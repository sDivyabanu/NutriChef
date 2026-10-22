"""Natural-language recipe modification with curated substitutions, scaling and validation.

Deterministic and explainable: every change is listed with a reason; requested diets are re-checked on the
result; anything that could not be changed is reported instead of silently ignored.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from .features import FeatureExtractor
from .ingredients import IngredientExtractor
from .lexicon import Lexicon
from .query import QueryParser
from .text import normalize

SUBS = json.loads((Path(__file__).parent / "data" / "substitutions.json").read_text(encoding="utf-8"))
SUBS.pop("_comment", None)

_NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ten": 10, "twelve": 12}
SCALE_RE = re.compile(r"\b(?:for|serves?|feed|feeds)\s+(?P<n>\d+|one|two|three|four|five|six|seven|eight|ten|twelve)\b(?:\s+(?:people|persons?|servings?|of us|adults|guests|portions))?")
FACTOR_RE = re.compile(r"\b(?P<w>double|triple|halve|half)\b")
LESS_SPICE_RE = re.compile(r"\b(less|reduce|lower|tone down|cut down|decrease|not so|not too|milder|mild|no)\b.*\b(spic\w*|heat|hot|chil\w*)|\bmilder\b|\bless spicy\b|\bnot spicy\b")
MORE_SPICE_RE = re.compile(r"\b(more|increase|extra|add)\b.*\b(spic\w*|heat|kick)|\b(spicier|hotter)\b|\bmake it (hot|spicy)\b")
QUICK_RE = re.compile(r"\b(quicker|faster|less time|speed(?: it)? up|shorter|quick version|in less time|save time)\b")
LIGHT_RE = re.compile(r"\b(lighter|healthier|less oil|low[- ]?fat|less fat|low[- ]?cal\w*|less butter)\b")
REPLACE_RES = [
    re.compile(r"\b(?:replace|swap|switch|change)\s+(?:the\s+)?(?P<a>[a-z' -]+?)\s+(?:with|for|to|by)\s+(?P<b>[a-z' -]+)"),
    re.compile(r"\bsubstitute\s+(?:the\s+)?(?P<a>[a-z' -]+?)\s+with\s+(?P<b>[a-z' -]+)"),
    re.compile(r"\bsubstitute\s+(?P<b>[a-z' -]+?)\s+for\s+(?:the\s+)?(?P<a>[a-z' -]+)"),
    re.compile(r"\buse\s+(?P<b>[a-z' -]+?)\s+instead of\s+(?:the\s+)?(?P<a>[a-z' -]+)"),
    re.compile(r"\b(?P<b>[a-z' -]+?)\s+instead of\s+(?:the\s+)?(?P<a>[a-z' -]+)"),
]
ALT_RE = re.compile(r"\b(?:alternative|substitute|replacement|swap|option)s?\b.*\b(?:without|for|to)\s+(?:the\s+)?(?P<x>[a-z' -]+)|\bwhat can i use instead of\s+(?P<y>[a-z' -]+)")
REMOVE_RE = re.compile(r"\b(?:remove|without|skip|leave out|omit|drop|take out|get rid of|no)\s+(?:the\s+)?(?P<x>[a-z' ,-]+?)(?=$|[.!?]| from| in| please| and make| but)")
JAIN_EXCLUDE = ["onion", "garlic", "potato", "carrot", "beet", "radish", "turnip", "sweet potato", "ginger", "leek", "shallot", "spring onion", "mushroom"]


@dataclass
class Op:
    kind: str
    args: dict
    text: str


@dataclass
class LineChange:
    before: str | None
    after: str | None
    status: str           # unchanged | changed | removed | added
    note: str | None = None
    alternatives: list[str] = field(default_factory=list)


@dataclass
class ModifyResult:
    understood: list[str]
    ops: list[Op]
    title: str
    ingredients: list[str]
    instructions: str
    servings: float | None
    line_changes: list[LineChange]
    step_changes: list[dict]
    validation: list[dict]
    suggestions: list[str]
    warnings: list[str]
    clarification: str | None = None


def fmt_qty(x: float) -> str:
    if abs(x - round(x)) < 0.05:
        return str(int(round(x)))
    whole = int(x)
    frac = Fraction(x - whole).limit_denominator(8)
    if frac.numerator == 0:
        return str(whole)
    if frac.denominator > 8 or frac == 1:
        return f"{x:.1f}"
    return f"{whole} {frac}" if whole else f"{frac}"


_LEAD_QTY = re.compile(
    r"^(?P<lead>\s*)(?P<a>\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?|[½¼¾⅓⅔⅛]|\d+[½¼¾⅓⅔])(?:\s*(?P<sep>-|–|to)\s*(?P<b>\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?))?"
)
_UNI = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}


def _val(s: str) -> float:
    s = s.strip()
    if s[-1] in _UNI and len(s) > 1:
        return float(s[:-1]) + _UNI[s[-1]]
    if s in _UNI:
        return _UNI[s]
    if " " in s:
        w, f = s.split()
        return float(w) + float(Fraction(f))
    return float(Fraction(s))


def scale_line(line: str, factor: float) -> tuple[str, bool]:
    m = _LEAD_QTY.match(line)
    if not m:
        return line, False
    a = fmt_qty(_val(m.group("a")) * factor)
    out = m.group("lead") + a
    if m.group("b"):
        out += f"{m.group('sep')}{fmt_qty(_val(m.group('b')) * factor)}"
    return out + line[m.end():], True


def _short(sub: str) -> str:
    return re.split(r"\s*\(", sub)[0].strip()


class RecipeModifier:
    def __init__(self, lex: Lexicon, parser: QueryParser, fx: FeatureExtractor):
        self.lex = lex
        self.parser = parser
        self.fx = fx
        self.ix: IngredientExtractor = fx.extractor

    # ------------------------------------------------------------------ understanding
    def _names(self, text: str) -> list[tuple[str, str]]:
        return [(m.name, m.display) for m in self.ix.mentions(text, strict_ambiguous=False)]

    def understand(self, instruction: str) -> list[Op]:
        t = normalize(instruction)
        ops: list[Op] = []
        consumed: list[tuple[int, int]] = []
        for rx in REPLACE_RES:
            for m in rx.finditer(t):
                if any(s <= m.start() < e for s, e in consumed):
                    continue
                a = self._names(m.group("a"))
                if a:
                    b_text = m.group("b").strip()
                    b_text = re.split(r"\s+(?:and|but|please|in|so)\s+", b_text)[0].strip()
                    for name, disp in a:
                        ops.append(Op("replace", {"name": name, "display": disp, "with": b_text}, m.group(0)))
                    consumed.append((m.start(), m.end()))
        m = ALT_RE.search(t)
        if m:
            x = m.group("x") or m.group("y") or ""
            for name, disp in self._names(x):
                if not any(o.args.get("name") == name for o in ops):
                    ops.append(Op("alternative", {"name": name, "display": disp}, m.group(0)))
            consumed.append((m.start(), m.end()))
        pq = self.parser.parse(instruction)
        for d in pq.diets:
            if d != "non-vegetarian":
                ops.append(Op("diet", {"diet": d}, d))
        for g in pq.excluded_groups:
            gmap = {"dairy": "dairy-free", "gluten": "gluten-free", "nuts": "nut-free", "egg": "egg-free", "meat": "vegetarian",
                    "alcohol": "alcohol-free"}
            if g in gmap and not any(o.kind == "diet" and o.args["diet"] == gmap[g] for o in ops):
                ops.append(Op("diet", {"diet": gmap[g]}, f"no {g}"))
        for m in REMOVE_RE.finditer(t):
            if any(s <= m.start() < e for s, e in consumed):
                continue
            for name, disp in self._names(m.group("x")):
                if name in ("dairy", "egg", "nut", "meat", "alcohol") and any(o.kind == "diet" for o in ops):
                    continue
                if not any(o.args.get("name") == name for o in ops):
                    ops.append(Op("remove", {"name": name, "display": disp}, m.group(0)))
        m = SCALE_RE.search(t)
        if m:
            n = m.group("n")
            ops.append(Op("scale", {"servings": int(n) if n.isdigit() else _NUMWORDS[n]}, m.group(0)))
        else:
            m = FACTOR_RE.search(t)
            if m:
                ops.append(Op("scale", {"factor": {"double": 2, "triple": 3, "halve": 0.5, "half": 0.5}[m.group("w")]}, m.group(0)))
        if LESS_SPICE_RE.search(t):
            ops.append(Op("spice", {"direction": "down"}, "less spicy"))
        elif MORE_SPICE_RE.search(t):
            ops.append(Op("spice", {"direction": "up"}, "spicier"))
        if QUICK_RE.search(t):
            ops.append(Op("quicker", {}, "quicker"))
        if LIGHT_RE.search(t):
            ops.append(Op("lighter", {}, "lighter"))
        return ops

    # ------------------------------------------------------------------ helpers
    def _violates(self, name: str, diet: str) -> bool:
        e = self.lex.get(name)
        if not e:
            return False
        return {
            "vegan": not e.vegan,
            "vegetarian": not e.vegetarian or "egg" in e.allergens,
            "eggetarian": not e.vegetarian,
            "pescatarian": e.animal in ("meat", "poultry"),
            "dairy-free": "dairy" in e.allergens,
            "gluten-free": "gluten" in e.allergens,
            "nut-free": bool({"tree_nut", "peanut"} & e.allergens),
            "egg-free": "egg" in e.allergens,
            "soy-free": "soy" in e.allergens,
            "jain": any(self.lex.is_a(name, j) for j in JAIN_EXCLUDE) or not e.vegetarian,
            "alcohol-free": self.lex.is_a(name, "alcohol"),
        }.get(diet, False)

    def _subs_for(self, name: str, goal: str) -> tuple[list[str], str | None]:
        e = self.lex.get(name)
        for anc in (e.ancestors if e else (name,)):
            entry = SUBS.get(anc)
            if entry:
                goals = [goal] + (["egg-free"] if goal == "vegetarian" else []) + (["vegan"] if goal == "dairy-free" else [])
                for g in goals:
                    if entry.get(g):
                        return list(entry[g]), entry.get("note")
                if goal == "default" and entry.get("default"):
                    return list(entry["default"]), entry.get("note")
        return [], None

    @staticmethod
    def _replace_text(text: str, words: list[str], new: str) -> tuple[str, bool]:
        changed = False
        for w in sorted({w for w in words if w}, key=len, reverse=True):
            pattern = re.compile(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", re.IGNORECASE)
            if pattern.search(text):
                text = pattern.sub(new, text)
                changed = True
        return text, changed

    def _surface_words(self, name: str, display: str | None) -> list[str]:
        e = self.lex.get(name)
        words = {name, display or ""}
        if e:
            words.update(s for s in e.synonyms if len(s) > 2)
            words.update(p for s in [name] for p in (s + "s", s + "es"))
        return [w for w in words if w]

    # ------------------------------------------------------------------ apply
    def modify(self, recipe: dict, instruction: str, original_servings: float | None = None) -> ModifyResult:
        ops = self.understand(instruction)
        lines = list(recipe["ingredients"])
        steps = [s for s in re.split(r"\n+", recipe.get("instructions") or "") if s.strip()]
        orig_steps = list(steps)
        title = recipe["title"]
        notes: dict[int, str] = {}
        alts: dict[int, list[str]] = {}
        removed: set[int] = set()
        warnings: list[str] = []
        suggestions: list[str] = []
        understood: list[str] = []
        servings = recipe.get("servings") or original_servings
        clarification = None
        parsed = [self.ix.parse_line(l) for l in lines]

        def substitute(idx: int, name: str, display: str | None, new: str, reason: str, others: list[str] | None = None,
                       note: str | None = None, retitle: bool = True):
            nonlocal title
            short = _short(new)
            words = self._surface_words(name, display)
            new_line, ok = self._replace_text(lines[idx], words, short)
            if not ok:
                lead = _LEAD_QTY.match(lines[idx])
                new_line = (lead.group(0).strip() + " " if lead else "") + short
            lines[idx] = new_line
            notes[idx] = reason + (f" — {note}" if note else "")
            if others:
                alts[idx] = others
            for si, s in enumerate(steps):
                steps[si], _ = self._replace_text(s, words, short)
            if retitle:
                title, _ = self._replace_text(title, words, short.title() if title.istitle() else short)

        if not ops:
            return ModifyResult([], [], title, lines, recipe.get("instructions") or "", servings, [LineChange(l, l, "unchanged") for l in lines], [], [], [],
                                ["I couldn't find a modification in that request."],
                                "Try e.g. 'make this vegan', 'replace paneer with tofu', 'less spicy', 'remove mushrooms' or 'make it for 2 people'.")

        for op in ops:
            if op.kind == "replace":
                hit = False
                for i, pl in enumerate(parsed):
                    for ing in pl.ingredients:
                        if ing["name"] and self.lex.is_a(ing["name"], op.args["name"]) and i not in removed:
                            substitute(i, ing["name"], ing.get("display"), op.args["with"], f"replaced {ing.get('display') or ing['name']} with {op.args['with']} (your request)")
                            hit = True
                understood.append(f"Replace {op.args['display']} with {op.args['with']}")
                if not hit:
                    warnings.append(f"This recipe doesn't list {op.args['display']}, so nothing was replaced.")
                else:
                    _, note = self._subs_for(op.args["name"], "default")
                    if note:
                        suggestions.append(note)
            elif op.kind == "alternative":
                options, note = self._subs_for(op.args["name"], "default")
                understood.append(f"Suggest an alternative to {op.args['display']}")
                hit = False
                for i, pl in enumerate(parsed):
                    for ing in pl.ingredients:
                        if ing["name"] and self.lex.is_a(ing["name"], op.args["name"]) and i not in removed:
                            if options:
                                substitute(i, ing["name"], ing.get("display"), options[0], f"alternative to {ing['name']}", options[1:], note)
                            else:
                                removed.add(i)
                                notes[i] = f"removed {ing['name']} (no curated substitute)"
                            hit = True
                if not hit:
                    warnings.append(f"This recipe doesn't list {op.args['display']}.")
            elif op.kind == "remove":
                understood.append(f"Remove {op.args['display']}")
                hit = False
                for i, pl in enumerate(parsed):
                    names = [ing["name"] for ing in pl.ingredients if ing["name"]]
                    if any(self.lex.is_a(n, op.args["name"]) for n in names) and i not in removed:
                        hit = True
                        others = [n for n in names if not self.lex.is_a(n, op.args["name"])]
                        if not others:
                            removed.add(i)
                            options, _ = self._subs_for(op.args["name"], "default")
                            notes[i] = f"removed (your request)"
                            if options:
                                alts[i] = options
                        else:
                            words = self._surface_words(op.args["name"], op.args["display"])
                            new_line, _ = self._replace_text(lines[i], words, "")
                            lines[i] = re.sub(r"\s*(,|\band\b|\bor\b)\s*(?=$|,)", "", re.sub(r"\s{2,}", " ", new_line)).strip(" ,")
                            notes[i] = "removed from this line (your request)"
                words = self._surface_words(op.args["name"], op.args["display"])
                for si, s in enumerate(steps):
                    new, ok = self._replace_text(s, words, "")
                    if ok:
                        new = re.sub(r"\s+(,|\.)", r"\1", re.sub(r"\b(and|or|with)\s+(and|or|,|\.)", r"\2", re.sub(r"\s{2,}", " ", new)))
                        new = re.sub(r",\s*,", ",", re.sub(r"\b(add|with|and)\s*,", r"\1", new)).strip()
                        new = re.sub(r"\b(in|add|with|the|stir|and)\s+and\s+", r"\1 ", new, flags=re.I)
                        new = re.sub(r"\s+and\s*(?=[.,;]|$)", "", new)
                        steps[si] = new
                if not hit:
                    warnings.append(f"This recipe doesn't list {op.args['display']}.")
            elif op.kind == "diet":
                diet = op.args["diet"]
                understood.append(f"Make it {diet}")
                if f"({diet} version)" not in title:
                    title = f"{title} ({diet} version)"
                for i, pl in enumerate(parsed):
                    if i in removed:
                        continue
                    for ing in pl.ingredients:
                        n = ing["name"]
                        if not n or not self._violates(n, diet):
                            continue
                        options, note = self._subs_for(n, diet)
                        if options:
                            substitute(i, n, ing.get("display"), options[0], f"{n} is not {diet} → {_short(options[0])}", options[1:], note,
                                       retitle=False)
                        elif pl.optional:
                            removed.add(i)
                            notes[i] = f"removed optional {n} (not {diet})"
                        else:
                            warnings.append(f"No curated {diet} substitute for {n} — replace or remove it yourself.")
                        break
            elif op.kind == "scale":
                factor = op.args.get("factor")
                if factor is None:
                    if not servings:
                        clarification = (f"This recipe doesn't say how many it serves. How many servings does the original make? "
                                         f"(Needed to scale to {op.args['servings']}.)")
                        understood.append(f"Scale to {op.args['servings']} servings (needs original servings)")
                        continue
                    factor = op.args["servings"] / float(servings)
                    understood.append(f"Scale from {servings:g} to {op.args['servings']} servings (×{factor:.2g})")
                    servings = op.args["servings"]
                else:
                    understood.append(f"Scale quantities ×{factor:g}")
                    servings = servings * factor if servings else None
                unscaled = []
                for i in range(len(lines)):
                    if i in removed:
                        continue
                    lines[i], ok = scale_line(lines[i], factor)
                    if ok:
                        notes[i] = (notes.get(i, "") + f"; scaled ×{factor:.2g}").strip("; ")
                    elif not parsed[i].optional and parsed[i].kind == "ingredient":
                        unscaled.append(lines[i])
                if unscaled:
                    warnings.append(f"{len(unscaled)} line(s) have no number to scale (e.g. '{unscaled[0]}') — adjust by taste.")
                suggestions.append("Cooking times and pan sizes may need adjusting when scaling.")
            elif op.kind == "spice":
                down = op.args["direction"] == "down"
                understood.append("Reduce the heat" if down else "Make it spicier")
                touched = False
                for i, pl in enumerate(parsed):
                    if i in removed:
                        continue
                    if any(ing["name"] and self.lex.get(ing["name"]) and self.lex.get(ing["name"]).spicy for ing in pl.ingredients):
                        f = 0.5 if down else 1.5
                        new, ok = scale_line(lines[i], f)
                        lines[i] = new if ok else lines[i] + (" (use about half)" if down else " (use about 1.5×)")
                        notes[i] = "less heat" if down else "more heat"
                        touched = True
                if down:
                    suggestions.append("Remove chili seeds and membranes, and add a spoon of yogurt or coconut milk at the end to soften the heat.")
                if not touched:
                    if down:
                        warnings.append("No chili ingredients found — this recipe is probably already mild.")
                    else:
                        lines.append("1/2 tsp red chili flakes or 1 green chili, chopped (added for heat)")
                        notes[len(lines) - 1] = "added for heat"
            elif op.kind == "quicker":
                understood.append("Make it quicker")
                text = " ".join(steps).lower()
                for i, pl in enumerate(parsed):
                    if any(ing["name"] and self.lex.is_a(ing["name"], "legume") for ing in pl.ingredients) and re.search(r"\bdried\b|\bsoak", lines[i].lower() + text):
                        lines[i] = re.sub(r"\bdried\b", "canned (drained)", lines[i], flags=re.I)
                        notes[i] = "use canned legumes to skip soaking and boiling"
                if re.search(r"overnight|marinate", text):
                    suggestions.append("Shorten the marinade to 30 minutes (flavour will be lighter).")
                if re.search(r"simmer[^.]*\b(hour|[4-9]\d minutes)", text) or re.search(r"\bbraise", text):
                    suggestions.append("Use a pressure cooker: most braises and dals cook in about a third of the time.")
                if re.search(r"\broast|bake", text):
                    suggestions.append("Cut ingredients smaller so they roast or bake faster.")
                suggestions.append("Prep all ingredients before you start cooking.")
            elif op.kind == "lighter":
                understood.append("Make it lighter")
                for i, pl in enumerate(parsed):
                    if i in removed:
                        continue
                    for ing in pl.ingredients:
                        n = ing["name"]
                        if not n:
                            continue
                        e = self.lex.get(n)
                        if e and (e.category == "oil" or n in ("butter", "ghee")):
                            new, ok = scale_line(lines[i], 0.5)
                            if ok:
                                lines[i] = new
                                notes[i] = "half the fat"
                        elif self.lex.is_a(n, "cream") and n not in ("ice cream",):
                            options, note = self._subs_for(n, "lighter")
                            if options:
                                substitute(i, n, ing.get("display"), options[0], "lighter than cream", options[1:], note)
                if re.search(r"deep[- ]fr", " ".join(steps).lower()):
                    suggestions.append("Bake or air-fry instead of deep-frying.")

        # ---------------- assemble result, re-validate
        final_lines = [l for i, l in enumerate(lines) if i not in removed]
        changes: list[LineChange] = []
        for i, orig in enumerate(recipe["ingredients"]):
            if i in removed:
                changes.append(LineChange(orig, None, "removed", notes.get(i), alts.get(i, [])))
            elif lines[i] != orig:
                changes.append(LineChange(orig, lines[i], "changed", notes.get(i), alts.get(i, [])))
            else:
                changes.append(LineChange(orig, orig, "unchanged"))
        for i in range(len(recipe["ingredients"]), len(lines)):
            changes.append(LineChange(None, lines[i], "added", notes.get(i)))
        step_changes = [{"before": a, "after": b, "changed": a != b} for a, b in zip(orig_steps, steps)]

        validation = []
        f = self.fx.compute({"id": -1, "title": title, "ingredients": final_lines or [""], "instructions": "\n".join(steps)})
        for op in ops:
            if op.kind == "diet":
                diet = op.args["diet"]
                bad = sorted({n for n in f.ingredients if self._violates(n, diet)})
                validation.append({"check": diet, "passed": not bad, "detail": "all ingredient lines pass" if not bad else f"still contains: {', '.join(bad)}"})
            elif op.kind in ("remove", "replace", "alternative") and op.args.get("name"):
                still = [n for n in f.ingredients if self.lex.is_a(n, op.args["name"])]
                validation.append({"check": f"no {op.args['display']}", "passed": not still, "detail": "removed everywhere" if not still else f"still listed: {', '.join(still)}"})
        if f.unknown_lines:
            warnings.append("Some ingredient lines could not be checked automatically — review them.")

        return ModifyResult(understood, ops, title, final_lines, "\n".join(steps), servings, changes, step_changes, validation,
                            list(dict.fromkeys(suggestions)), warnings, clarification)
