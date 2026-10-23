"""Conversational recipe assistant with explicit, structured state.

Each turn: reset? -> reference to a shown result? -> recipe question (answered from the database) ->
filter removal? -> parse + merge constraints into the state -> deterministic search -> templated, grounded reply.
No LLM memory is relied on; the state is a QueryUnderstanding the client sends back each turn.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from .engine import NLPEngine
from .modify import SUBS, _short
from .query import IngredientRef, ParsedQuery
from .ranker import GROUP_LABEL, Prefs, Ranker, SearchOutcome
from .text import normalize
from .vocab import RESET_PHRASES

ORDINALS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4, "fifth": 5, "5th": 5,
            "last": -1, "top": 1}
REF_RE = re.compile(r"\b(?:the\s+)?(?P<ord>first|second|third|fourth|fifth|last|1st|2nd|3rd|4th|5th|top)\s+(?:one|recipe|result|option|dish)?\b|"
                    r"(?:#|number|no\.?|recipe|option)\s*(?P<num>\d+)\b")
QUESTION_RE = re.compile(r"\b(how long|how much time|time|ingredients?|what do i need|need to buy|is (it|this|that)|does (it|this|that)|"
                         r"contain|calories|protein|nutrition|carbs|fat|servings?|serve|how many people|steps|how do i (make|cook)|"
                         r"instructions|method|spicy|allergens?|substitute|replace|instead of|vegan|vegetarian|gluten|dairy)\b")
REMOVE_FILTER_RE = re.compile(
    r"\b(remove|drop|forget|ignore|clear|no need for|doesn't need|does not need|don't need|any)\b\s*(?:the\s+)?(?P<what>time|time limit|cuisine|meal|meal type|"
    r"diet|calorie|calories|protein|nutrition|filters?|limit|restriction)s?\b|\bany time\b|\btime doesn'?t matter\b|\bany cuisine\b"
)
ALLOW_RE = re.compile(r"\b(?P<x>[a-z ]+?)\s+(?:is|are)\s+(?:fine|ok|okay|allowed)\b|\ballow\s+(?P<y>[a-z ]+)\b")
NEW_TOPIC_CUES = re.compile(r"^(only|also|and|but|with|without|under|less than|in under|make it|make them|what about|how about|"
                            r"actually|instead|no |not |nothing|just|preferably|something|ideally|maybe|vegetarian|vegan|quick|"
                            r"spicy|cheaper|healthier|less|more|any)\b")


@dataclass
class ChatTurn:
    reply: str
    state: dict
    action: str                       # search | answer | clarify | reset | generate
    results: SearchOutcome | None = None
    focus_recipe_id: int | None = None
    shown_ids: list[int] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def empty_state() -> dict:
    return {"pq": None, "shown_ids": [], "focus_recipe_id": None, "turns": 0}


class ChatAssistant:
    def __init__(self, engine: NLPEngine, ranker: Ranker):
        self.e = engine
        self.ranker = ranker

    # ------------------------------------------------------------------ state helpers
    @staticmethod
    def _describe(pq: ParsedQuery) -> str:
        bits = []
        bits += pq.diets
        bits += pq.qualities
        bits += [c.title() if c.islower() else c for c in pq.cuisines]
        bits += pq.meal_types
        bits.append("recipes")
        s = " ".join(bits)
        req = [r.display for r in pq.ingredients if r.role == "required"]
        have = [r.display for r in pq.ingredients if r.role == "available"]
        exc = [r.display for r in pq.ingredients if r.role == "excluded"] + [GROUP_LABEL.get(g, g) for g in pq.excluded_groups]
        if req:
            s += " with " + ", ".join(req)
        if have:
            s += " using " + ", ".join(have)
        if exc:
            s += " without " + ", ".join(dict.fromkeys(exc))
        if pq.max_time_min:
            s += f" under {pq.max_time_min} minutes"
        for n in pq.nutrition:
            s += f", {n.text}"
        if pq.similar_to:
            s += f", similar to {pq.similar_to}"
        return s.strip()

    def _merge(self, old: ParsedQuery | None, new: ParsedQuery, text: str) -> ParsedQuery:
        if old is None:
            return new
        refine = bool(NEW_TOPIC_CUES.match(normalize(text))) or not new.free_text or len(text.split()) <= 4
        has_new_dish = bool(new.free_text) and not refine
        if has_new_dish and (new.ingredients or new.similar_to or len(new.free_text.split()) >= 2):
            # looks like a new request: keep persistent safety constraints (exclusions, diets), replace the rest
            merged = copy.deepcopy(new)
            for r in old.ingredients:
                if r.role == "excluded" and not any(x.name == r.name for x in merged.ingredients):
                    merged.ingredients.append(r)
            merged.excluded_groups = list(dict.fromkeys(old.excluded_groups + new.excluded_groups))
            merged.diets = list(dict.fromkeys(old.diets + new.diets))
            merged.notes = new.notes + ["Kept your earlier exclusions/diet. Say 'start over' to clear them."] if (
                old.diets or old.excluded_groups or any(r.role == "excluded" for r in old.ingredients)) else new.notes
            return merged
        m = copy.deepcopy(old)
        m.original, m.corrected, m.notes, m.conflicts, m.clarification = new.original, new.corrected, list(new.notes), [], None
        m.corrections = new.corrections
        for r in new.ingredients:
            m.ingredients = [x for x in m.ingredients if x.name != r.name]   # newest role wins ("actually no paneer")
            m.ingredients.append(r)
        if re.search(r"\bonly\b", normalize(text)) and new.ingredients:
            # "only paneer recipes": the named ingredients become requirements, earlier soft ones stay soft
            for r in m.ingredients:
                if any(r.name == x.name for x in new.ingredients) and r.role != "excluded":
                    r.role = "required"
        m.excluded_groups = list(dict.fromkeys(m.excluded_groups + new.excluded_groups))
        m.diets = list(dict.fromkeys(m.diets + new.diets))
        if "non-vegetarian" in new.diets:
            m.diets = [d for d in m.diets if d not in ("vegetarian", "vegan", "eggetarian")]
        if new.cuisines:
            m.cuisines = new.cuisines
        if new.meal_types:
            m.meal_types = new.meal_types
        if new.max_time_min is not None:
            m.max_time_min = new.max_time_min
        for n in new.nutrition:
            m.nutrition = [x for x in m.nutrition if x.nutrient != n.nutrient] + [n]
        m.qualities = list(dict.fromkeys(m.qualities + new.qualities))
        if "mild" in new.qualities and "spicy" in m.qualities:
            m.qualities.remove("spicy")
        if new.similar_to:
            m.similar_to = new.similar_to
        if new.servings:
            m.servings = new.servings
        extra = [w for w in new.free_text.split() if w not in m.free_text.split()]
        m.free_text = " ".join([*m.free_text.split(), *extra]).strip()
        m.intent = old.intent if new.intent in ("search", "question") else new.intent
        return m

    def _remove_filters(self, pq: ParsedQuery, text: str) -> tuple[ParsedQuery, list[str]]:
        t = normalize(text)
        changed = []
        m = REMOVE_FILTER_RE.search(t)
        if m:
            what = (m.group("what") or t)
            if "time" in what or "any time" in t or "time doesn" in t:
                pq.max_time_min = None
                changed.append("time limit")
            if "cuisine" in what:
                pq.cuisines = []
                changed.append("cuisine")
            if "meal" in what:
                pq.meal_types = []
                changed.append("meal type")
            if "diet" in what:
                pq.diets = []
                changed.append("diet")
            if re.search(r"calor|protein|nutrition", what):
                pq.nutrition = []
                changed.append("nutrition limits")
            if "filter" in what or "restriction" in what:
                pq.max_time_min, pq.cuisines, pq.meal_types, pq.nutrition, pq.qualities = None, [], [], [], []
                changed.append("all filters except exclusions and diet")
        # "forget the paneer", "eggs are fine"
        for rx in (re.compile(r"\b(?:forget|drop|remove|ignore)\s+(?:the\s+)?(?P<x>[a-z ]+?)(?:\s+(?:filter|requirement))?$"), ALLOW_RE):
            mm = rx.search(t)
            if mm:
                phrase = mm.group("x") if "x" in mm.groupdict() and mm.group("x") else mm.groupdict().get("y")
                if not phrase:
                    continue
                for men in self.e.fx.extractor.mentions(phrase, strict_ambiguous=False):
                    before = len(pq.ingredients)
                    pq.ingredients = [r for r in pq.ingredients if not self.e.lex.is_a(r.name, men.name) and r.name != men.name]
                    grp = {"egg": "egg", "dairy": "dairy", "nut": "nuts", "peanut": "peanut", "fish": "fish", "meat": "meat"}.get(men.name)
                    if grp and grp in pq.excluded_groups:
                        pq.excluded_groups.remove(grp)
                    if men.name == "egg" and "vegetarian" in pq.diets:
                        pq.diets = ["eggetarian" if d == "vegetarian" else d for d in pq.diets]
                    if len(pq.ingredients) != before or grp:
                        changed.append(men.display)
        return pq, changed

    # ------------------------------------------------------------------ answering questions about a recipe
    def _answer(self, rid: int, text: str) -> str | None:
        from .. import db

        rec = db.get_recipe(rid)
        f = self.e.feature(rid)
        if not rec or not f:
            return None
        t = normalize(text)
        title = rec["title"]
        if re.search(r"how long|time|how much time|quick", t):
            if rec.get("total_time_min"):
                return f"“{title}” takes {rec['total_time_min']} minutes (stated by the author)."
            if f.est_time_min is not None:
                return (f"“{title}” takes roughly {f.est_time_min} minutes — that's the sum of the times stated in its steps, "
                        "so add some prep time.")
            return f"“{title}” doesn't state any cooking times, so I can't estimate it."
        if re.search(r"calor|protein|nutrition|carb|\bfat\b|macro", t):
            nut = rec.get("nutrition") or {}
            known = {k: v for k, v in nut.items() if v is not None}
            if known:
                return f"Per serving for “{title}” (entered by the recipe author): " + ", ".join(f"{k.replace('_g', '')} {v:g}" for k, v in known.items()) + "."
            return f"There's no nutrition data for “{title}”, and I don't estimate calories or macros — it stays unknown."
        if re.search(r"serv|how many people", t):
            return f"“{title}” serves {rec['servings']:g}." if rec.get("servings") else f"“{title}” doesn't say how many it serves."
        m = re.search(r"(?:substitute|replace|instead of|swap)\s+(?:for\s+)?(?:the\s+)?(?P<x>[a-z ]+)", t)
        if m:
            for men in self.e.fx.extractor.mentions(m.group("x"), strict_ambiguous=False):
                e = self.e.lex.get(men.name)
                for anc in (e.ancestors if e else (men.name,)):
                    if anc in SUBS:
                        opts = SUBS[anc].get("default") or next((v for k, v in SUBS[anc].items() if isinstance(v, list)), [])
                        note = SUBS[anc].get("note")
                        return f"Instead of {men.display} you could use: {', '.join(_short(o) for o in opts)}." + (f" Note: {note}" if note else "") + \
                            " (Open the recipe and use “Modify this recipe” to apply it.)"
                return f"I don't have a curated substitute for {men.display}."
        for diet, key in (("vegan", "vegan"), ("vegetarian", "vegetarian"), ("gluten", "gluten_free"), ("dairy", "dairy_free"),
                          ("egg", "egg_free"), ("nut", "nut_free")):
            if re.search(rf"\b{diet}", t) and re.search(r"\b(is|are|does|contain|free|has|have)\b", t):
                ok = f.diet[key]
                label = {"gluten_free": "gluten-free", "dairy_free": "dairy-free", "egg_free": "egg-free", "nut_free": "nut-free"}.get(key, key)
                unsure = f" (but {len(f.unknown_lines)} ingredient line(s) couldn't be checked)" if f.unknown_lines else ""
                return (f"Based on its ingredient list, “{title}” is {'' if ok else 'not '}{label}{unsure}. "
                        "This is an NLP check of the ingredient text, not a guarantee.")
        m = re.search(r"(?:contain|has|have|use|uses|with)\s+(?:any\s+)?(?P<x>[a-z ]+)\??$", t)
        if m:
            mentions = self.e.fx.extractor.mentions(m.group("x"), strict_ambiguous=False)
            if mentions:
                parts = []
                for men in mentions:
                    hits = [n for n in f.ingredients if self.e.lex.is_a(n, men.name)]
                    parts.append(f"yes — {', '.join(hits)}" if hits else f"no {men.display} in the ingredient list")
                return f"“{title}”: " + "; ".join(parts) + "."
        if re.search(r"spic|hot", t):
            return f"“{title}” looks {f.spice_level} (estimated from its chili ingredients: {', '.join(f.spicy_ingredients) or 'none'})."
        if re.search(r"allergen", t):
            return f"Allergens found in the ingredient text of “{title}”: {', '.join(f.allergens) or 'none recognised'}. Not a guarantee of allergy safety."
        if re.search(r"ingredient|what do i need|buy|shopping", t):
            lines = rec["ingredients"]
            return f"Ingredients for “{title}”:\n" + "\n".join(f"• {l}" for l in lines[:25])
        if re.search(r"step|how do i|how to|instruction|method|make it|cook it", t):
            steps = [s for s in re.split(r"\n+", rec["instructions"] or "") if s.strip()]
            return f"How to make “{title}”:\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps[:8])) + (
                "\n(See the recipe page for the rest.)" if len(steps) > 8 else "")
        return None

    def _resolve_ref(self, text: str, shown: list[int]) -> int | None:
        m = REF_RE.search(normalize(text))
        if not m or not shown:
            return None
        if m.group("num"):
            k = int(m.group("num"))
        else:
            k = ORDINALS.get(m.group("ord"), 1)
        if k == -1:
            return shown[-1]
        return shown[k - 1] if 1 <= k <= len(shown) else None

    # ------------------------------------------------------------------ main
    def turn(self, text: str, state: dict, prefs: Prefs, pq_from_state) -> ChatTurn:
        state = state or empty_state()
        t = normalize(text)
        state["turns"] = state.get("turns", 0) + 1
        if any(p in t for p in RESET_PHRASES):
            return ChatTurn("Okay — I've cleared everything. What would you like to cook?", empty_state(), "reset")
        old: ParsedQuery | None = pq_from_state(state.get("pq"))
        shown = state.get("shown_ids") or []

        ref = self._resolve_ref(text, shown)
        focus = ref or state.get("focus_recipe_id")
        new = self.e.parser.parse(text)
        is_question = bool(QUESTION_RE.search(t)) and (ref is not None or (focus and re.search(r"\b(it|this|that|its|one)\b", t))
                                                       or (focus and new.intent == "question"))
        if is_question and focus:
            ans = self._answer(focus, text)
            if ans:
                state["focus_recipe_id"] = focus
                return ChatTurn(ans, state, "answer", focus_recipe_id=focus, shown_ids=shown)
        if ref is not None and not new.ingredients and not new.diets and not new.cuisines and new.max_time_min is None:
            state["focus_recipe_id"] = ref
            from .. import db

            rec = db.get_recipe(ref)
            return ChatTurn(f"“{rec['title']}” — ask me about its time, ingredients, steps, diet or substitutions, "
                            "or open it from the card below.", state, "answer", focus_recipe_id=ref, shown_ids=shown)

        if new.intent == "generate":
            return ChatTurn("I can write a new recipe for that with the local model — open the Generate page "
                            "(I've filled in your request).", state, "generate", suggestions=[text])

        changed: list[str] = []
        if old is not None:
            old, changed = self._remove_filters(copy.deepcopy(old), text)
        if changed and not (new.ingredients or new.diets or new.cuisines or new.meal_types or new.max_time_min or new.nutrition):
            merged = old
        else:
            merged = self._merge(old, new, text)
        if merged.clarification and old is None:
            return ChatTurn(merged.clarification, state, "clarify")
        if merged.conflicts:
            return ChatTurn("That conflicts with what you asked before: " + " ".join(merged.conflicts) +
                            " Which should I keep?", state, "clarify")
        outcome = self.ranker.search(merged, prefs, k=6)
        state["pq"] = merged
        state["shown_ids"] = [h.recipe_id for h in outcome.hits]
        state["focus_recipe_id"] = None
        desc = self._describe(merged)
        prefix = f"Removed the {', '.join(changed)}. " if changed else ""
        if merged.corrections:
            prefix += "(I read " + ", ".join(f"“{a}” as “{b}”" for a, b in merged.corrections) + ".) "
        if outcome.total == 0:
            if outcome.relaxations:
                opts = "; ".join(f"{r['label'].lower()} ({r['results']} recipes)" for r in outcome.relaxations[:3])
                reply = f"{prefix}I couldn't find {desc}. I kept your exclusions and diet — you could {opts}."
            else:
                reply = f"{prefix}I couldn't find {desc}. Try describing it differently or say “start over”."
        else:
            top = ", ".join(f"{i + 1}. {h.title}" for i, h in enumerate(outcome.hits[:3]))
            reply = f"{prefix}Here are {desc} — {outcome.total} match{'es' if outcome.total != 1 else ''}. Top picks: {top}."
            if any(n.startswith("Nutrition limits") for n in outcome.notes):
                reply += " (Nutrition limits couldn't be verified — these recipes have no nutrition data.)"
            reply += " Ask about any of them (e.g. “how long does the second one take?”) or refine further."
        return ChatTurn(reply, state, "search", results=outcome, shown_ids=state["shown_ids"])
