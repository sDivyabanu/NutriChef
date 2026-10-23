"""Ingredient extraction: recipe ingredient lines and free-text mentions -> structured ingredients.

Quantities and units are parsed, not stripped: the original text is always preserved in `raw`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .lexicon import Lexicon, get_lexicon
from .text import Token, normalize, tokenize

WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "dozen": 12, "half": 0.5, "quarter": 0.25, "couple": 2,
    "oru": 1, "rendu": 2, "irandu": 2, "moonu": 3, "naalu": 4, "anju": 5,
}
VAGUE = {"some", "few", "little", "bit", "handful", "several", "bunch", "lots", "plenty", "leftover"}

UNITS = {
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g", "gr": "g",
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg",
    "mg": "mg", "ml": "ml", "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml",
    "l": "l", "liter": "l", "liters": "l", "litre": "l", "litres": "l", "ltr": "l",
    "cup": "cup", "cups": "cup", "c": "cup",
    "tbsp": "tbsp", "tbs": "tbsp", "tbsps": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp", "tbl": "tbsp", "t": "tbsp",
    "tsp": "tsp", "tsps": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
    "oz": "oz", "ounce": "oz", "ounces": "oz", "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "pint": "pint", "pints": "pint", "quart": "quart", "quarts": "quart", "qt": "quart", "gallon": "gallon",
    "pinch": "pinch", "pinches": "pinch", "dash": "dash", "dashes": "dash",
    "clove": "clove", "cloves": "clove", "can": "can", "cans": "can", "tin": "can", "tins": "can",
    "package": "package", "packages": "package", "pkg": "package", "packet": "package", "packets": "package",
    "stick": "stick", "sticks": "stick", "slice": "slice", "slices": "slice", "bunch": "bunch", "bunches": "bunch",
    "sprig": "sprig", "sprigs": "sprig", "handful": "handful", "handfuls": "handful", "piece": "piece",
    "pieces": "piece", "head": "head", "heads": "head", "stalk": "stalk", "stalks": "stalk", "rib": "rib",
    "ribs": "rib", "jar": "jar", "jars": "jar", "bottle": "bottle", "bottles": "bottle", "inch": "inch",
    "inches": "inch", "cm": "cm", "drop": "drop", "drops": "drop", "fillet": "fillet", "fillets": "fillet",
    "pod": "pod", "pods": "pod", "leaf": "leaf", "leaves": "leaf", "bag": "bag", "bags": "bag", "box": "box",
    "envelope": "envelope", "container": "container", "scoop": "scoop", "glass": "glass", "bowl": "bowl",
}
# Units that are also ingredient words when no number precedes them ("cloves", "leaves", "fillets").
AMBIGUOUS_UNITS = {"clove", "cloves", "leaf", "leaves", "fillet", "fillets", "stick", "sticks", "head", "c", "t", "l"}
SIZE_WORDS = {"small", "medium", "large", "big", "extra", "jumbo", "heaping", "heaped", "level", "scant", "generous", "rounded"}
PREP_WORDS = {
    "chopped", "minced", "diced", "sliced", "grated", "shredded", "crushed", "peeled", "seeded", "halved",
    "quartered", "julienned", "cubed", "mashed", "melted", "softened", "beaten", "whisked", "toasted", "roasted",
    "cooked", "boiled", "drained", "rinsed", "trimmed", "torn", "cored", "pitted", "zested", "juiced", "divided",
    "thawed", "frozen", "soaked", "sifted", "packed", "crumbled", "finely", "coarsely", "thinly", "roughly",
    "freshly", "lightly", "ground", "smashed", "deveined", "shelled", "blanched", "steamed", "fried",
}
OPTIONAL_RE = re.compile(
    r"\b(optional|for (garnish|garnishing|serving|dusting|drizzling|brushing|decorating|decoration|greasing|the pan|pan|"
    r"sprinkling|topping)|to serve|to garnish|garnish|as needed|if desired|accompaniment)\b"
)


EQUIPMENT_RE = re.compile(
    r"^(special )?equipment\b|\b(thermometer|springform|skillet|skewers?|parchment|cheesecloth|slicer|spatula|mixer|"
    r"food processor|blender|kitchen (string|twine|torch)|twine|ramekins?|molds?|moulds?|baking (sheet|dish|pan)s?|"
    r"(cake|tart|pie|loaf|bundt|muffin|roasting|sheet|saute|frying) pans?|wok|dutch oven|slow cooker|pressure cooker|"
    r"pastry bag|piping bag|cookie cutters?|mandoline|grill pan|ice cream maker|cocktail shaker|jigger|strainer|sieve|"
    r"measuring cup|cast[- ]iron|baking pans?|glasses|spice mill|mortar|pestle|grill|torch|aluminum foil|plastic wrap)\b"
)
NOTE_RE = re.compile(r"^\*|available at|specialty (foods|shops|stores)|supermarkets|recipe follows|see recipe|you will also need|also need")


@dataclass
class Mention:
    """An ingredient found in text, with its span (token indices) and any quantity attached."""

    name: str
    display: str
    start: int
    end: int
    char_start: int
    char_end: int
    quantity: float | None = None
    quantity_text: str | None = None
    unit: str | None = None
    matched_by: str = "exact"
    confidence: float = 1.0


@dataclass
class ParsedLine:
    raw: str
    ingredients: list[dict] = field(default_factory=list)   # ParsedIngredient-compatible dicts
    alternatives: list[list[str]] = field(default_factory=list)
    optional: bool = False
    unknown: bool = False
    kind: str = "ingredient"   # ingredient | equipment | note


def _num(tok: str) -> float | None:
    if re.fullmatch(r"\d+", tok):
        return float(tok)
    if re.fullmatch(r"\d+\.\d+", tok):
        return float(tok)
    m = re.fullmatch(r"(\d+)/(\d+)", tok)
    if m and int(m.group(2)):
        return int(m.group(1)) / int(m.group(2))
    return None


def parse_quantity(tokens: list[Token], i: int) -> tuple[float | None, str | None, str | None, int]:
    """Parse a quantity (+unit) starting at token i. Returns (value, unit, text, next_index)."""
    start, value, j = i, None, i
    n = len(tokens)

    def word(k: int) -> str:
        return tokens[k].text if k < n else ""

    # "half an onion", "a quarter cup", "one and a half"
    if (word(j) in WORD_NUMBERS and word(j) not in ("a", "an")) or (
        word(j) in ("a", "an") and word(j + 1) in ("half", "quarter", "dozen", "couple")
    ):
        if word(j) in ("a", "an"):
            j += 1
        value = WORD_NUMBERS[word(j)]
        j += 1
        if word(j) in ("a", "an", "of") and value in (0.5, 0.25, 12, 2):
            j += 1
        if word(j) == "and" and word(j + 1) in ("a", "an") and word(j + 2) == "half":
            value += 0.5
            j += 3
    elif word(j) in ("pinch", "dash", "handful", "sprinkle"):
        value = 1.0
    elif word(j) in ("a", "an") and word(j + 1).rstrip(".") in UNITS and word(j + 1) not in AMBIGUOUS_UNITS:
        value = 1.0
        j += 1
    elif _num(word(j)) is not None:
        value = _num(word(j))
        j += 1
        # mixed fraction "1 1/2"
        if j < n and "/" in word(j) and _num(word(j)) is not None:
            value += _num(word(j))
            j += 1
        # range "2-3", "2 to 3", "2 or 3"
        if word(j) in ("-", "to", "or") and j + 1 < n and _num(word(j + 1)) is not None:
            hi = _num(word(j + 1))
            j += 2
            if j < n and "/" in word(j) and _num(word(j)) is not None:
                hi += _num(word(j))
                j += 1
            value = (value + hi) / 2
    elif word(j) in VAGUE or (word(j) in ("a", "an") and word(j + 1) in VAGUE):
        if word(j) in ("a", "an"):
            j += 1
        j += 1
        if word(j) == "of":
            j += 1
        return None, None, " ".join(t.text for t in tokens[start:j]), j
    else:
        return None, None, None, i

    # optional parenthetical size "(14-oz)" directly after the number
    k = j
    while word(k) in SIZE_WORDS:
        k += 1
    unit = None
    w = word(k).rstrip(".")
    if w in UNITS:
        unit = UNITS[w]
        k += 1
        if word(k) == ".":
            k += 1
        if word(k) == "of":
            k += 1
        j = k
    text = " ".join(t.text for t in tokens[start:j] if t.text != ".")
    return value, unit, text, j


class IngredientExtractor:
    def __init__(self, lexicon: Lexicon | None = None):
        self.lex = lexicon or get_lexicon()

    # ------------------------------------------------------------------ free text
    def mentions(self, text: str, tokens: list[Token] | None = None, strict_ambiguous: bool = True) -> list[Mention]:
        """Find ingredient mentions in (already spelling-corrected) normalised text, with quantities."""
        norm = normalize(text) if tokens is None else text
        tokens = tokens if tokens is not None else tokenize(norm)
        out: list[Mention] = []
        # Phrases never cross hard punctuation ("tomato, rice" is two items); hyphens/apostrophes are fine.
        segment: list[int] = []
        segments: list[list[int]] = []
        for k, t in enumerate(tokens):
            if t.is_word:
                segment.append(k)
            elif t.text in "-'":
                continue
            else:
                if segment:
                    segments.append(segment)
                segment = []
        if segment:
            segments.append(segment)
        for idx in segments:
            wseq = [tokens[k].text for k in idx]
            for s, e, name in self.lex.match(wseq):
                ts, te = idx[s], idx[e - 1] + 1
                entry = self.lex.get(name)
                if strict_ambiguous and entry and "qamb" in entry.tags and not wseq[e - 1].endswith("s"):
                    # ambiguous words ("date", "orange", "sage") only count with a quantity before them
                    prev = tokens[ts - 1].text if ts > 0 else ""
                    if not (_num(prev) is not None or prev in WORD_NUMBERS):
                        continue
                m = Mention(name=name, display=norm[tokens[ts].start : tokens[te - 1].end], start=ts, end=te,
                            char_start=tokens[ts].start, char_end=tokens[te - 1].end)
                self._attach_quantity(tokens, m, out[-1].end if out else 0)
                out.append(m)
        out.sort(key=lambda m: m.start)
        return out

    def _attach_quantity(self, tokens: list[Token], m: Mention, floor: int) -> None:
        """Look left of the mention (not past the previous mention) for "2", "100 g", "half an"."""
        lo = max(floor, m.start - 6)
        for k in range(lo, m.start):
            value, unit, text, nxt = parse_quantity(tokens, k)
            if text is None:
                continue
            between = [t.text for t in tokens[nxt : m.start]]
            if all(w in SIZE_WORDS or w in PREP_WORDS or w in ("of", "fresh", "-", "(", ")") for w in between):
                m.quantity, m.unit, m.quantity_text = value, unit, text
                after = tokens[m.end].text if m.end < len(tokens) else ""
                if unit is None and after in UNITS and after not in ("c", "t", "l", "g"):
                    m.unit = UNITS[after]
                return

    # ------------------------------------------------------------------ recipe lines
    def parse_line(self, raw: str) -> ParsedLine:
        norm = normalize(raw)
        opt = OPTIONAL_RE.search(norm)
        # "2 tbsp oil, plus more for drizzling": only the extra amount is optional
        extra = re.search(r"\b(plus|and|with) (more|extra|additional)\b", norm)
        optional = bool(opt) and not (extra and extra.start() < opt.start())
        # parentheticals are size/notes ("(14-oz)", "(about 2 cups)", "(such as Gala)") -> not ingredients
        main = re.sub(r"\([^)]*\)", " ", norm)
        main_tokens = tokenize(main)
        # text after "such as"/"preferably" names a variety, not another ingredient
        cut = len(main_tokens)
        for k, t in enumerate(main_tokens):
            if t.text == "such" and k + 1 < len(main_tokens) and main_tokens[k + 1].text == "as":
                cut = k
                break
        tokens = main_tokens[:cut]
        qty, unit, qtext, nxt = parse_quantity(tokens, 0)
        mentions = self.mentions(main, tokens, strict_ambiguous=False)
        # drop equipment/serving phrases accidentally matched after "for" ("for the pan")
        parsed = ParsedLine(raw=raw, optional=optional)
        if not mentions and (EQUIPMENT_RE.search(norm) or NOTE_RE.search(norm)):
            parsed.kind = "equipment" if EQUIPMENT_RE.search(norm) else "note"
            return parsed
        if not mentions:
            parsed.unknown = True
            words = [t.text for t in tokens[nxt:] if t.is_word and t.text not in PREP_WORDS and t.text not in SIZE_WORDS]
            parsed.ingredients.append(
                dict(raw=raw, name=None, display=" ".join(words[:4]) or None, quantity=qty, quantity_text=qtext,
                     unit=unit, optional=optional, confidence=0.0, matched_by=None)
            )
            return parsed
        # alternatives: mentions separated only by "or" / "and/or"
        groups: list[list[Mention]] = [[mentions[0]]]
        for prev, cur in zip(mentions, mentions[1:]):
            between = {t.text for t in tokens[prev.end : cur.start]}
            if "or" in between and not between - {"or", "and", "/", ",", "-"} - PREP_WORDS - SIZE_WORDS:
                groups[-1].append(cur)
            else:
                groups.append([cur])
        prep_words = [t.text for t in tokens if t.text in PREP_WORDS]
        for gi, group in enumerate(groups):
            for mi, m in enumerate(group):
                e = self.lex.get(m.name)
                first = gi == 0 and mi == 0
                parsed.ingredients.append(
                    dict(
                        raw=raw, name=m.name, display=m.display,
                        quantity=m.quantity if m.quantity is not None else (qty if first else None),
                        quantity_text=m.quantity_text or (qtext if first else None),
                        unit=m.unit or (unit if first else None),
                        preparation=", ".join(dict.fromkeys(prep_words)) or None,
                        optional=optional, category=e.category if e else None,
                        is_staple=bool(e and e.staple), confidence=m.confidence, matched_by=m.matched_by,
                    )
                )
            if len(group) > 1:
                parsed.alternatives.append([m.name for m in group])
        return parsed
