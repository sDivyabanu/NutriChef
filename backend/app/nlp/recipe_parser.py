"""Parse an unstructured, pasted recipe into structured fields for user review (never auto-saved).

Heuristic, explainable segmentation: section headers if present, otherwise a per-line classifier
(quantity/ingredient-lexicon lines -> ingredients, imperative/longer sentences -> steps).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .features import FeatureExtractor
from .ingredients import IngredientExtractor, parse_quantity
from .text import normalize, tokenize

ING_HEADER = re.compile(r"^\s*(ingredients?|you(?:'ll)? need|shopping list|for the [a-z ]+)\s*:?\s*$", re.I)
STEP_HEADER = re.compile(r"^\s*(method|instructions?|directions?|steps?|preparation|how to make( it)?|procedure)\s*:?\s*$", re.I)
NOTE_HEADER = re.compile(r"^\s*(notes?|tips?|serving suggestions?|storage)\s*:?\s*$", re.I)
TIME_LINE = re.compile(r"\b(prep(?:aration)?|cook(?:ing)?|total|active|bake|ready in)\s*(?:time)?\s*[:\-]?\s*(?P<v>[\d.]+\s*(?:-\s*[\d.]+)?)\s*(?P<u>min(?:ute)?s?|hrs?|hours?)\b", re.I)
SERVES_LINE = re.compile(r"\b(?:serves|servings?|yield|makes|portions?)\s*[:\-]?\s*(?P<n>\d+)", re.I)
BULLET = re.compile(r"^\s*(?:[-*•·▪◦]|\d+[.)]|step\s*\d+[:.)]?)\s*", re.I)
IMPERATIVE = re.compile(r"^(add|heat|cook|stir|mix|combine|place|put|bake|boil|simmer|fry|saute|sauté|chop|cut|slice|"
                        r"pour|whisk|blend|serve|preheat|bring|remove|transfer|season|garnish|let|cover|drain|roast|"
                        r"grill|toss|spread|fold|knead|marinate|soak|grind|temper|wash|rinse|peel|keep|allow|"
                        r"take|in a|once|when|after|meanwhile|then|finally|now|first|next|reduce|turn|switch|sprinkle)\b", re.I)


@dataclass
class ParsedRecipe:
    title: str | None
    ingredients: list[str]
    instructions: list[str]
    total_time_min: int | None
    time_source: str | None
    servings: int | None
    notes: list[str] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class RecipeTextParser:
    def __init__(self, fx: FeatureExtractor):
        self.fx = fx
        self.ix: IngredientExtractor = fx.extractor

    def _is_ingredient_line(self, line: str) -> float:
        norm = normalize(BULLET.sub("", line))
        toks = tokenize(norm)
        if not toks:
            return 0.0
        value, unit, qtext, _ = parse_quantity(toks, 0)
        mentions = self.ix.mentions(norm, toks, strict_ambiguous=False)
        words = [t for t in toks if t.is_word]
        score = 0.0
        if qtext is not None:
            score += 0.5
        if unit:
            score += 0.2
        if mentions:
            score += 0.4
        if len(words) <= 8:
            score += 0.2
        if IMPERATIVE.match(norm) or len(words) > 14 or norm.endswith("."):
            score -= 0.6
        return score

    def _looks_like_title(self, s: str) -> bool:
        norm = normalize(s)
        toks = tokenize(norm)
        if not toks or len(s) > 90 or BULLET.match(s) or IMPERATIVE.match(norm) or s.rstrip().endswith("."):
            return False
        return parse_quantity(toks, 0)[2] is None

    def parse(self, text: str) -> ParsedRecipe:
        raw_lines = [l.rstrip() for l in text.replace("\r", "").split("\n")]
        lines = [l for l in raw_lines if l.strip()]
        title = None
        time_total, time_source, servings = None, None, None
        notes: list[str] = []
        ingredients: list[str] = []
        steps: list[str] = []
        section = None
        times: dict[str, float] = {}

        for idx, line in enumerate(lines):
            s = line.strip()
            m = SERVES_LINE.search(s)
            if m and len(s) < 40 and servings is None:
                servings = int(m.group("n"))
                continue
            tm = list(TIME_LINE.finditer(s))
            if tm and len(s) < 80:
                for t in tm:
                    v = t.group("v").split("-")
                    val = sum(float(x) for x in v) / len(v)
                    val *= 60 if t.group("u").lower().startswith("h") else 1
                    times[t.group(1).lower()[:4]] = val
                continue
            if ING_HEADER.match(s):
                section = "ing"
                continue
            if STEP_HEADER.match(s):
                section = "steps"
                continue
            if NOTE_HEADER.match(s):
                section = "notes"
                continue
            if title is None and idx == 0 and self._looks_like_title(s):
                title = s.strip("#*: ")
                continue
            if section == "notes":
                notes.append(s)
            elif section == "ing":
                ingredients.append(BULLET.sub("", s).strip())
            elif section == "steps":
                steps.append(BULLET.sub("", s).strip())
            else:
                (ingredients if self._is_ingredient_line(s) >= 0.5 else steps).append(BULLET.sub("", s).strip())

        # a single long paragraph of instructions -> split into sentences
        if len(steps) == 1 and len(steps[0]) > 120:
            steps = [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", steps[0]) if x.strip()]
        if "tota" in times:
            time_total, time_source = int(round(times["tota"])), "stated (total time)"
        elif times:
            time_total, time_source = int(round(sum(times.values()))), "stated (prep + cook)"
        warnings = []
        if not ingredients:
            warnings.append("No ingredient lines were recognised — please add them manually.")
        if not steps:
            warnings.append("No instruction steps were recognised.")
        if title is None:
            warnings.append("No title found — please add one.")
        unknown = [l for l in ingredients if self.ix.parse_line(l).unknown]
        if unknown:
            warnings.append(f"{len(unknown)} ingredient line(s) contain ingredients NutriChef doesn't recognise.")
        conf = {
            "title": 0.9 if title else 0.0,
            "ingredients": 0.9 if any(ING_HEADER.match(l.strip()) for l in lines) else 0.6 if ingredients else 0.0,
            "instructions": 0.9 if any(STEP_HEADER.match(l.strip()) for l in lines) else 0.6 if steps else 0.0,
        }
        return ParsedRecipe(title, ingredients, steps, time_total, time_source, servings, notes, conf, warnings)
