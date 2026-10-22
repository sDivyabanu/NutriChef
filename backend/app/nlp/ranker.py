"""Hybrid ranking: hard constraints first, then a weighted, explainable score.

Hard constraints (never traded off against similarity): excluded ingredients/groups, diets, allergies,
required ingredients, meal type, cuisine evidence, time limits.
Soft signals: semantic + lexical relevance, pantry coverage, missing ingredients, preferences, qualities.
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, field

import numpy as np

from .engine import NLPEngine
from .features import CUISINE_PARENT
from .lexicon import BROAD_GROUPS
from .query import ParsedQuery
from .text import normalize

MEAL_STRICT = {"breakfast": {"breakfast"}, "dessert": {"dessert"}, "drink": {"drink"}, "soup": {"soup"},
               "salad": {"salad"}, "snack": {"appetizer", "snack"}, "appetizer": {"appetizer"}, "side": {"side"}}
MAIN_MEALS = {"dinner", "lunch"}
NOT_A_MEAL = {"dessert", "drink", "component", "bread"}
CUISINE_CHILDREN = {"indian": ["south indian", "north indian"], "asian": ["chinese", "thai", "japanese", "korean", "vietnamese"],
                    "mediterranean": ["italian", "greek", "middle eastern", "spanish", "north african"]}
JAIN_EXCLUDE = ["onion", "garlic", "potato", "carrot", "beet", "radish", "turnip", "sweet potato", "ginger", "leek",
                "shallot", "spring onion", "mushroom"]
CUISINE_EVIDENCE = 2.0
MAX_DETAILED = 600   # candidates scored in detail (all candidates pass the hard filters first)
MAX_DETAILED_NO_TEXT = 6000
# Descriptive phrases for the embedding model when a query has only qualities ("something filling").
QUALITY_HINTS = {"filling": "hearty filling main dish", "healthy": "healthy fresh vegetable dish",
                 "light": "light fresh salad", "quick": "quick easy weeknight dish", "easy": "simple easy dish",
                 "high-protein": "high protein dish", "low-calorie": "light low calorie dish",
                 "comforting": "comforting stew", "budget": "simple inexpensive dish", "high-fibre": "beans lentils whole grains"}


@dataclass
class Weights:
    semantic: float = 1.0
    lexical: float = 0.7
    used: float = 1.4
    recipe_cov: float = 0.8
    missing: float = 0.5
    preferred: float = 0.5
    unavailable: float = 0.8
    cuisine: float = 0.5
    meal: float = 0.25
    quality: float = 0.3
    similar: float = 1.0
    personal: float = 0.25


@dataclass
class Prefs:
    vegetarian_includes_eggs: bool = False
    diet: str | None = None
    allergies: list[str] = field(default_factory=list)
    disliked_ingredients: list[str] = field(default_factory=list)
    liked_ingredients: list[str] = field(default_factory=list)
    liked_cuisines: list[str] = field(default_factory=list)
    staples: list[str] = field(default_factory=list)
    favorite_ids: list[int] = field(default_factory=list)
    apply_profile: bool = True


@dataclass
class Hit:
    recipe_id: int
    title: str
    score: float
    breakdown: dict
    used: list[str]
    missing: list[str]
    pantry_match_pct: int | None
    explanation: list[str]
    warnings: list[str]
    checks: list[dict]


@dataclass
class SearchOutcome:
    hits: list[Hit]
    total: int
    excluded: dict[str, int]
    notes: list[str]
    relaxations: list[dict]
    add_ingredient_suggestions: list[str]
    mode: str
    timing_ms: dict


def _mask(engine: NLPEngine, key: str) -> np.ndarray:
    m = np.zeros(len(engine.ids), dtype=bool)
    idx = engine.index.get(key)
    if idx:
        m[list(idx)] = True
    return m


GROUP_KEYS = {
    "meat": ["animal:meat", "animal:poultry", "animal:seafood", "animal:other"],
    "seafood": ["animal:seafood"], "fish": ["allergen:fish"], "shellfish": ["allergen:shellfish"],
    "dairy": ["allergen:dairy"], "egg": ["allergen:egg"], "nuts": ["allergen:tree_nut", "allergen:peanut"],
    "tree_nut": ["allergen:tree_nut"], "peanut": ["allergen:peanut"], "gluten": ["allergen:gluten"],
    "soy": ["allergen:soy"], "sesame": ["allergen:sesame"], "mustard": ["allergen:mustard"], "alcohol": ["alcohol"],
    "onion_garlic": ["onion", "garlic"],
    "animal": ["animal:meat", "animal:poultry", "animal:seafood", "animal:other", "allergen:dairy", "allergen:egg", "honey"],
}
GROUP_LABEL = {"meat": "meat, poultry or seafood", "nuts": "nuts or peanuts", "onion_garlic": "onion or garlic",
               "animal": "animal products", "tree_nut": "tree nuts", "egg": "eggs"}
ALLERGEN_GROUPS = {"dairy", "egg", "nuts", "tree_nut", "peanut", "gluten", "soy", "sesame", "fish", "shellfish", "mustard"}


class Ranker:
    def __init__(self, engine: NLPEngine, weights: Weights | None = None):
        self.e = engine
        self.w = weights or Weights()

    # ================================================================== public
    def search(self, pq: ParsedQuery, prefs: Prefs | None = None, k: int = 20, offset: int = 0,
               mode: str = "hybrid") -> SearchOutcome:
        t0 = time.perf_counter()
        prefs = prefs or Prefs(apply_profile=False)
        e = self.e
        with e.lock:
            if mode != "hybrid":
                return self._baseline(pq, k, offset, mode, t0)
            n = len(e.ids)
            mask = e.active.copy()
            excluded: Counter = Counter()
            notes: list[str] = list(pq.notes)
            unknown_nutrition = False

            def apply(m: np.ndarray, reason: str) -> None:
                nonlocal mask
                removed = int((mask & ~m).sum())
                if removed:
                    excluded[reason] += removed
                mask &= m

            constraints = self._hard_constraints(pq, prefs, notes)
            for label, keep in constraints:
                apply(keep, label)

            avail = pq.names("available")
            required = pq.names("required")
            preferred = pq.names("preferred")
            unavailable = pq.names("unavailable")
            pantry_mode = bool(avail)
            staples = {name for name, en in e.lex.entries.items() if en.staple} | set(prefs.staples)
            if pantry_mode:
                cand = np.zeros(n, dtype=bool)
                for a in avail:
                    cand |= self._covers_mask(a)
                apply(cand, "uses none of your ingredients")

            # ---------------- relevance signals
            t_ret = time.perf_counter()
            text = pq.free_text or " ".join(avail + required + preferred)
            sem_text = text or " ".join(QUALITY_HINTS.get(q, q) for q in pq.qualities)
            sem = e.embedding_scores(sem_text) if sem_text else np.zeros(n, dtype=np.float32)
            lex = e.tfidf_scores(text) if text else np.zeros(n, dtype=np.float32)
            sim = np.zeros(n, dtype=np.float32)
            if pq.similar_to:
                sim = e.embedding_scores(pq.similar_to) if e.embed else e.tfidf_scores(pq.similar_to)
            retrieval_ms = (time.perf_counter() - t_ret) * 1000

            cands = np.flatnonzero(mask)
            total = len(cands)
            hits: list[Hit] = []
            if total:
                sem_n = self._norm(sem, cands)
                lex_n = self._norm(lex, cands)
                sim_n = self._norm(sim, cands)
                prelim = self.w.semantic * sem_n + self.w.lexical * lex_n + self.w.similar * sim_n
                if pantry_mode:
                    used_cnt = np.zeros(n, dtype=np.float32)
                    for a in avail:
                        used_cnt += self._covers_mask(a)
                    prelim = prelim + self.w.used * used_cnt / len(avail) - 0.05 * e.n_essential
                text_signal = bool(prelim[cands].max() > 0) if len(cands) else False
                if len(cands) > (MAX_DETAILED if text_signal else MAX_DETAILED_NO_TEXT):
                    cands = cands[np.argsort(-prelim[cands], kind="stable")[:MAX_DETAILED]]
                scores = np.zeros(n, dtype=np.float32)
                details: dict[int, dict] = {}
                avail_set = set(avail) | staples
                asked_types = set(pq.meal_types)
                for i in cands:
                    f = e.features[i]
                    b = {"semantic": float(self.w.semantic * sem_n[i]), "lexical": float(self.w.lexical * lex_n[i])}
                    used, missing = [], []
                    if pantry_mode:
                        used = [a for a in avail if self._recipe_uses(f, a)]
                        missing = [r for r in f.essential if not e.lex.satisfies(avail_set, r, allow_broad=True)]
                        ess = max(1, len(f.essential))
                        b["used"] = self.w.used * len(used) / len(avail)
                        b["recipe_coverage"] = self.w.recipe_cov * (ess - len(missing)) / ess
                        b["missing"] = -self.w.missing * min(len(missing), 10) / 10
                    if preferred:
                        got = 0.0
                        for p in preferred:
                            if p in ("vegetable", "leafy greens"):
                                got += min(1.0, f.vegetable_count / 4)
                            elif self._recipe_uses(f, p):
                                got += 1.0
                        b["preferred"] = self.w.preferred * got / len(preferred)
                    if unavailable:
                        need = [u for u in unavailable if self._recipe_needs(f, u)]
                        if need:
                            b["unavailable"] = -self.w.unavailable * len(need)
                    if pq.cuisines:
                        best = max(self._cuisine_score(f, c) for c in pq.cuisines)
                        b["cuisine"] = self.w.cuisine * min(best / 6.0, 1.0)
                    if pq.meal_types:
                        b["meal"] = self.w.meal * self._meal_fit(f, pq.meal_types)
                    elif set(f.meal_types) & {"component", "drink"} and "main" not in f.meal_types:
                        b["meal"] = -self.w.meal  # sauces/drinks only when asked for
                    if pq.qualities:
                        b["qualities"] = self.w.quality * sum(self._quality(f, ql) for ql in pq.qualities)
                    if pq.similar_to:
                        b["similar"] = self.w.similar * float(sim_n[i])
                    if prefs.apply_profile:
                        p = self._personal(f, prefs)
                        if p:
                            b["personal"] = p
                    # small prior: prefer recipes whose ingredient lines we could fully read
                    b["parse_quality"] = -0.05 * min(len(f.unknown_lines), 3)
                    scores[i] = sum(b.values())
                    details[i] = {"b": b, "used": used, "missing": missing}

                order = sorted(cands, key=lambda i: (-scores[i], len(details[i]["missing"]), e.ids[i]))
                seen_titles: set[str] = set()
                ranked = []
                for i in order:
                    key = normalize(e.titles[i])
                    if key in seen_titles:
                        continue
                    seen_titles.add(key)
                    ranked.append(i)
                for i in ranked[offset : offset + k]:
                    d = details[i]
                    hit, unk = self._explain(i, pq, prefs, d, pantry_mode, float(scores[i]))
                    unknown_nutrition |= unk
                    hits.append(hit)
            if pq.nutrition and unknown_nutrition:
                notes.append(
                    "Nutrition limits could only be checked for recipes that have nutrition data. The source dataset "
                    "has no nutrition information, so those recipes are shown as 'not verified' — nothing is assumed."
                )
            relax = self._relaxations(pq, prefs) if total == 0 else []
            add_sugg = self._ingredient_suggestions(hits, pq) if pantry_mode and hits else []
            timing = {"retrieval_ms": round(retrieval_ms, 1), "total_ms": round((time.perf_counter() - t0) * 1000, 1)}
            return SearchOutcome(hits, total, dict(excluded), notes, relax, add_sugg, "hybrid", timing)

    # ================================================================== constraints
    def _hard_constraints(self, pq: ParsedQuery, prefs: Prefs, notes: list[str]) -> list[tuple[str, np.ndarray]]:
        e = self.e
        n = len(e.ids)
        out: list[tuple[str, np.ndarray]] = []
        strict = bool(re.search(r"allerg|intoleran|celiac|coeliac|anaphyla", pq.corrected))
        for ref in pq.ingredients:
            if ref.role == "excluded":
                out.append((f"contains {ref.display}", ~_mask(e, ref.name)))
        groups = list(pq.excluded_groups)
        if prefs.apply_profile:
            for a in prefs.allergies:
                g = a.lower().strip()
                g = {"nut": "nuts", "peanuts": "peanut", "eggs": "egg", "milk": "dairy", "lactose": "dairy",
                     "wheat": "gluten", "soya": "soy", "prawn": "shellfish", "shrimp": "shellfish"}.get(g, g)
                if g in GROUP_KEYS:
                    if g not in groups:
                        groups.append(g)
                    strict = True
                else:
                    name = e.lex.lookup(g)
                    if name:
                        out.append((f"contains {g} (your allergy)", ~_mask(e, name)))
        for g in groups:
            keys = GROUP_KEYS.get(g, [])
            bad = np.zeros(n, dtype=bool)
            for key in keys:
                bad |= _mask(e, key)
            out.append((f"contains {GROUP_LABEL.get(g, g)}", ~bad))
            if strict and g in ALLERGEN_GROUPS:
                maybe = np.zeros(n, dtype=bool)
                for key in keys:
                    if key.startswith("allergen:"):
                        maybe |= _mask(e, "maybe:" + key.split(":", 1)[1])
                out.append((f"may contain {GROUP_LABEL.get(g, g)}", ~maybe))
        diets = list(pq.diets)
        if prefs.apply_profile and prefs.diet:
            d = prefs.diet.lower().replace(" ", "-")
            d = {"non-vegetarian": None, "nonveg": None}.get(d, d)
            if d and d not in diets and not ("vegetarian" in d and "non-vegetarian" in diets):
                diets.append(d)
        for d in diets:
            if d == "vegetarian":
                key = "eggetarian" if prefs.vegetarian_includes_eggs else "vegetarian"
                out.append(("not vegetarian" + ("" if prefs.vegetarian_includes_eggs else " (NutriChef's vegetarian excludes eggs)"),
                            e.diet_arr[key]))
            elif d in ("vegan", "eggetarian", "pescatarian"):
                out.append((f"not {d}", e.diet_arr[d]))
            elif d in ("gluten-free", "dairy-free", "nut-free", "egg-free"):
                key = d.replace("-", "_")
                out.append((f"not {d}", e.diet_arr[key]))
                if strict:
                    grp = {"gluten_free": "gluten", "dairy_free": "dairy", "nut_free": "nuts", "egg_free": "egg"}[key]
                    maybe = np.zeros(n, dtype=bool)
                    for k2 in GROUP_KEYS[grp]:
                        maybe |= _mask(e, "maybe:" + k2.split(":", 1)[1])
                    out.append((f"may contain {GROUP_LABEL.get(grp, grp)}", ~maybe))
            elif d == "non-vegetarian":
                anim = _mask(e, "animal:meat") | _mask(e, "animal:poultry") | _mask(e, "animal:seafood")
                out.append(("no meat, poultry or seafood", anim))
            elif d == "jain":
                bad = np.zeros(n, dtype=bool)
                for name in JAIN_EXCLUDE:
                    bad |= _mask(e, name)
                out.append(("not Jain (onion, garlic or root vegetables)", ~bad & e.diet_arr["vegetarian"]))
        for name in pq.names("required"):
            ref = next(r for r in pq.ingredients if r.name == name and r.role == "required")
            out.append((f"doesn't use {ref.display}", self._covers_mask(name)))
        for mt in pq.meal_types:
            if mt in MEAL_STRICT:
                allowed = MEAL_STRICT[mt]
                out.append((f"not a {mt} recipe", np.array([bool(s & allowed) for s in e.meal_sets])))
            elif mt in MAIN_MEALS:
                out.append((f"not a {mt} dish (dessert, drink, sauce or bread)",
                            np.array([not (s & NOT_A_MEAL) and not (s == {"breakfast"}) for s in e.meal_sets])))
        if pq.cuisines:
            ok = np.zeros(n, dtype=bool)
            for i, f in enumerate(e.features):
                ok[i] = any(self._cuisine_score(f, c) >= CUISINE_EVIDENCE for c in pq.cuisines)
            out.append((f"no {'/'.join(pq.cuisines)} cuisine evidence", ok))
        if pq.max_time_min is not None:
            t = e.time_arr
            unknown = np.isnan(t)
            out.append(("no cooking time stated", ~unknown))
            out.append((f"takes longer than {pq.max_time_min} min", np.nan_to_num(t, nan=1e9) <= pq.max_time_min))
        for nc in pq.nutrition:
            keep = np.ones(n, dtype=bool)
            for i, nut in enumerate(e.nutrition):
                v = (nut or {}).get(nc.nutrient)
                if v is not None:
                    keep[i] = v <= nc.value if nc.op == "<=" else v >= nc.value
            out.append((f"fails {nc.text}", keep))
        return out

    # ================================================================== helpers
    def _covers_mask(self, name: str) -> np.ndarray:
        """Recipes that contain `name` or something `name` can stand in for (have rice -> basmati rice)."""
        e = self.e
        m = _mask(e, name)
        entry = e.lex.get(name)
        if entry:
            for anc in entry.ancestors[1:]:
                if anc in BROAD_GROUPS:
                    break
                # recipes needing exactly the parent ("tomato") are covered by a child ("cherry tomato")
                for i in e.index.get(anc, ()):
                    if anc in e.features[i].ingredients:
                        m[i] = True
        return m

    def _recipe_uses(self, f, name: str) -> bool:
        lex = self.e.lex
        return any(lex.satisfies({name}, r) or lex.is_a(r, name) for r in f.ingredients)

    def _recipe_needs(self, f, name: str) -> bool:
        lex = self.e.lex
        return any(lex.is_a(r, name) for r in f.essential)

    @staticmethod
    def _norm(arr: np.ndarray, cands: np.ndarray) -> np.ndarray:
        mx = float(arr[cands].max()) if len(cands) else 0.0
        return arr / mx if mx > 1e-9 else np.zeros_like(arr)

    @staticmethod
    def _cuisine_score(f, c: str) -> float:
        scores = f.cuisine_scores or {}
        best = scores.get(c, 0.0)
        for child in CUISINE_CHILDREN.get(c, []):
            best = max(best, scores.get(child, 0.0))
        if c == "indian":
            best = max(best, scores.get("south indian", 0.0))
        return best

    @staticmethod
    def _meal_fit(f, meals: list[str]) -> float:
        s = set(f.meal_types)
        fit = 0.0
        for mt in meals:
            if mt in MAIN_MEALS:
                fit = max(fit, 1.0 if "main" in s else 0.6 if s & {"soup", "salad"} else 0.0)
            else:
                fit = max(fit, 1.0 if s & MEAL_STRICT.get(mt, {mt}) else 0.0)
        return fit

    def _quality(self, f, q: str) -> float:
        title = f.title_norm
        names = set(f.ingredients)
        if q == "spicy":
            return {"hot": 1.0, "medium": 0.6, "mild": 0.0}[f.spice_level]
        if q == "mild":
            return {"hot": -0.7, "medium": 0.2, "mild": 1.0}[f.spice_level]
        if q == "quick":
            t = f.est_time_min
            return 0.0 if t is None else 1.0 if t <= 30 else 0.5 if t <= 45 else -0.3
        if q == "easy":
            return {"easy": 1.0, "medium": 0.3, "hard": -0.5}[f.difficulty]
        if q == "high-protein":
            return 1.0 if f.protein_ingredients else 0.0
        if q == "high-fibre":
            return min(1.0, 0.6 * bool(f.fibre_ingredients) + 0.15 * f.vegetable_count)
        if q in ("low-oil", "low-fat"):
            return -1.0 if f.oil_heavy else -0.4 if f.fried else 0.6 if f.extras.get("oil_tbsp_equiv", 0) <= 2 else 0.2
        if q in ("low-calorie", "light"):
            return (-1.0 if f.oil_heavy or "dessert" in f.meal_types else 0.0) + (0.6 if set(f.meal_types) & {"salad", "soup"} else 0.0) + min(0.4, 0.1 * f.vegetable_count)
        if q == "healthy":
            return min(1.0, 0.15 * f.vegetable_count + 0.3 * bool(f.fibre_ingredients)) - (0.8 if f.fried or f.oil_heavy else 0.0) - (0.5 if "dessert" in f.meal_types else 0.0)
        if q == "filling":
            if set(f.meal_types) & {"dessert", "drink", "component"}:
                return -0.5
            starchy = any(self.e.lex.get(n) and self.e.lex.get(n).category in ("grain", "legume", "pasta", "bread") for n in names)
            return 0.5 * bool(f.protein_ingredients) + 0.5 * starchy
        if q == "comforting":
            return 1.0 if re.search(r"\b(stew|soup|curry|pasta|casserole|mac|pie|braise|chili|risotto|dal|khichdi|porridge)\b", title) else 0.0
        if q == "creamy":
            return 1.0 if names & {"cream", "coconut milk", "yogurt", "sour cream", "cream cheese", "creme fraiche"} or "creamy" in title else 0.0
        if q == "crispy":
            return 1.0 if f.fried or re.search(r"\b(crisp|crispy|crunchy)\b", title) else 0.0
        if q == "one-pot":
            return 1.0 if re.search(r"\b(one[- ]pot|one[- ]pan|sheet[- ]pan|skillet)\b", title) else 0.0
        if q == "sweet":
            return 1.0 if "dessert" in f.meal_types else 0.0
        if q == "tangy":
            return 1.0 if names & {"tamarind", "lemon", "lemon juice", "lime", "lime juice", "vinegar"} else 0.0
        if q == "budget":
            return 1.0 if len(f.essential) <= 8 else 0.0
        if q == "low-carb":
            carby = any(self.e.lex.get(n) and self.e.lex.get(n).category in ("grain", "pasta", "bread", "sweetener", "flour") for n in f.essential)
            return 0.0 if carby else 1.0
        if q == "low-sugar":
            return 0.0 if "dessert" in f.meal_types or any(self.e.lex.is_a(n, "sugar") for n in f.essential) else 1.0
        return 0.0

    def _personal(self, f, prefs: Prefs) -> float:
        s = 0.0
        if prefs.liked_cuisines and f.cuisine and (f.cuisine in prefs.liked_cuisines or CUISINE_PARENT.get(f.cuisine) in prefs.liked_cuisines):
            s += self.w.personal
        if prefs.liked_ingredients:
            liked = [x for x in prefs.liked_ingredients if self._recipe_uses(f, x)]
            s += self.w.personal * min(1.0, len(liked) / 2)
        if prefs.disliked_ingredients:
            if any(self._recipe_needs(f, x) for x in prefs.disliked_ingredients):
                s -= 2 * self.w.personal
        return s

    # ================================================================== explanations
    def _explain(self, i: int, pq: ParsedQuery, prefs: Prefs, d: dict, pantry: bool, score: float) -> tuple[Hit, bool]:
        e = self.e
        f = e.features[i]
        exp: list[str] = []
        warn: list[str] = []
        checks: list[dict] = []
        used, missing = d["used"], d["missing"]
        pct = None
        if pantry:
            avail = pq.names("available")
            ess = len(f.essential)
            pct = round(100 * (ess - len(missing)) / ess) if ess else 100
            line = f"Uses {len(used)} of your {len(avail)} ingredient{'s' if len(avail) != 1 else ''}"
            line += f" and needs {len(missing)} more" if missing else " and needs nothing else (staples like salt, pepper, oil and water assumed)"
            exp.append(line + ".")
        for ref in pq.ingredients:
            if ref.role == "required":
                exp.append(f"Contains {ref.display}.")
            elif ref.role == "excluded":
                checks.append({"constraint": f"no {ref.display}", "status": "pass", "detail": "not found in the ingredient list"})
        for g in pq.excluded_groups:
            checks.append({"constraint": f"no {GROUP_LABEL.get(g, g)}", "status": "pass", "detail": "checked against the ingredient list"})
        for diet in pq.diets:
            label = diet
            detail = "every ingredient line was checked"
            if diet == "vegetarian" and not prefs.vegetarian_includes_eggs:
                detail += " (no meat, fish or eggs)"
            checks.append({"constraint": label, "status": "pass", "detail": detail})
        if pq.cuisines:
            c = f.cuisine or "unlabelled"
            checks.append({"constraint": "/".join(pq.cuisines), "status": "estimated",
                           "detail": f"cuisine inferred from title/ingredients (best guess: {c})"})
        if pq.meal_types:
            checks.append({"constraint": "/".join(pq.meal_types), "status": "estimated",
                           "detail": f"dish type inferred from the title: {', '.join(f.meal_types)}"})
        if pq.max_time_min is not None:
            checks.append({"constraint": f"≤ {pq.max_time_min} min", "status": "estimated",
                           "detail": f"about {f.est_time_min} min — sum of times stated in the steps (prep not included)"})
        unknown_nutrition = False
        nut = e.nutrition[i] or {}
        for nc in pq.nutrition:
            v = nut.get(nc.nutrient)
            if v is None:
                unknown_nutrition = True
                checks.append({"constraint": nc.text, "status": "unknown", "detail": "no nutrition data for this recipe — not verified"})
            else:
                checks.append({"constraint": nc.text, "status": "pass", "detail": f"{v:g} per serving (user-entered)"})
        for ql in pq.qualities:
            v = self._quality(f, ql)
            if v > 0:
                exp.append(f"Looks {ql} ({self._quality_reason(f, ql)}).")
            elif ql in ("high-protein", "low-calorie", "low-fat", "low-oil", "high-fibre", "healthy"):
                warn.append(f"Couldn't confirm '{ql}' from the ingredient list.")
        if pq.similar_to and d["b"].get("similar", 0) > 0.6:
            exp.append(f"Similar to {pq.similar_to}.")
        if d["b"].get("personal", 0) > 0:
            exp.append("Matches your saved preferences.")
        if d["b"].get("unavailable", 0) < 0:
            warn.append("Needs an ingredient you said you don't have.")
        if f.unknown_lines:
            warn.append(f"{len(f.unknown_lines)} ingredient line(s) could not be classified — check them for allergens.")
        if f.maybe_allergens:
            warn.append(f"May contain: {', '.join(f.maybe_allergens)} (depends on brand/variety).")
        if not exp:
            exp.append("Relevant to your search terms.")
        b = {k: round(v, 3) for k, v in d["b"].items() if abs(v) > 1e-6}
        return Hit(e.ids[i], e.titles[i], round(score, 4), b, used, missing, pct, exp, warn, checks), unknown_nutrition

    @staticmethod
    def _quality_reason(f, q: str) -> str:
        return {
            "spicy": f"spice level {f.spice_level}: {', '.join(f.spicy_ingredients[:3]) or 'title'}",
            "mild": "few or no chili ingredients",
            "quick": f"about {f.est_time_min} min stated",
            "easy": f"{len(f.essential)} main ingredients, {f.n_steps} steps",
            "high-protein": f"contains {', '.join(f.protein_ingredients[:3])} — not a measured value",
            "high-fibre": ", ".join(f.fibre_ingredients[:3]) or f"{f.vegetable_count} vegetables",
            "filling": "has a protein or starch base",
            "low-oil": "little oil or butter listed", "low-fat": "little oil or butter listed",
        }.get(q, "estimated from ingredients and steps")

    # ================================================================== empty results
    def _relaxations(self, pq: ParsedQuery, prefs: Prefs) -> list[dict]:
        """Count how many recipes each *single* relaxation would return. Exclusions and diets are never relaxed."""
        import copy

        options = []
        if pq.max_time_min is not None:
            q2 = copy.deepcopy(pq)
            q2.max_time_min = None
            options.append(("remove_time", f"Remove the {pq.max_time_min}-minute limit", q2))
        if pq.cuisines:
            q2 = copy.deepcopy(pq)
            q2.cuisines = []
            options.append(("remove_cuisine", f"Any cuisine instead of {', '.join(pq.cuisines)}", q2))
        if pq.meal_types:
            q2 = copy.deepcopy(pq)
            q2.meal_types = []
            options.append(("remove_meal", f"Any dish type instead of {', '.join(pq.meal_types)}", q2))
        req = [r for r in pq.ingredients if r.role == "required"]
        for r in req:
            q2 = copy.deepcopy(pq)
            for x in q2.ingredients:
                if x.name == r.name and x.role == "required":
                    x.role = "preferred"
            options.append((f"optional:{r.name}", f"Make {r.display} optional", q2))
        out = []
        for key, label, q2 in options:
            mask_ok = self.e.active.copy()
            for _, keep in self._hard_constraints(q2, prefs, []):
                mask_ok &= keep
            if q2.names("available"):
                cand = np.zeros(len(self.e.ids), dtype=bool)
                for a in q2.names("available"):
                    cand |= self._covers_mask(a)
                mask_ok &= cand
            cnt = int(mask_ok.sum())
            if cnt:
                out.append({"key": key, "label": label, "results": cnt})
        return sorted(out, key=lambda x: -x["results"])

    def _ingredient_suggestions(self, hits: list[Hit], pq: ParsedQuery) -> list[str]:
        c = Counter(m for h in hits for m in h.missing)
        have = set(pq.names("available"))
        return [m for m, _ in c.most_common(8) if m not in have][:5]

    # ================================================================== baselines (for evaluation)
    def _baseline(self, pq: ParsedQuery, k: int, offset: int, mode: str, t0: float) -> SearchOutcome:
        e = self.e
        if mode == "keyword":
            terms = [w for w in re.findall(r"[a-z]+", pq.normalized) if w not in _BASELINE_STOP]
            ids = e.keyword.search(terms, k=offset + k)
            pos = [e.pos_of[r] for r in ids]
        else:
            text = pq.normalized
            s = e.tfidf_scores(text) if mode == "tfidf" else e.embedding_scores(text)
            s = np.where(e.active, s, -1)
            pos = list(np.argsort(-s)[: offset + k])
        hits = [Hit(e.ids[i], e.titles[i], 0.0, {}, [], [], None, [], [], []) for i in pos[offset:]]
        return SearchOutcome(hits, len(hits), {}, [], [], [], mode, {"total_ms": round((time.perf_counter() - t0) * 1000, 1)})


_BASELINE_STOP = set("""i have a an the and or of for to in on with what can cook make prepare suggest find give me some
something recipe recipes dish dishes i'm im want need under minutes minute without no please using my any that is are""".split())


def hit_to_dict(h: Hit) -> dict:
    return asdict(h)
