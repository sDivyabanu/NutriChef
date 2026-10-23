"""Natural-language query understanding: intent, ingredients with roles, and structured constraints.

Rule-based and fully deterministic so that hard constraints (exclusions, diets) are never guessed by a model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .ingredients import SIZE_WORDS, UNITS, VAGUE, WORD_NUMBERS, IngredientExtractor, Mention
from .lexicon import Lexicon, get_lexicon
from .spelling import SpellCorrector
from .text import STOPWORDS, Token, normalize, tokenize
from .vocab import (
    AVAILABLE_CUES, AVAILABLE_PHRASES, CUISINE_PHRASES, DIET_PHRASES, EXCLUDE_CUES, EXCLUDE_PHRASES, GROUP_WORDS,
    LIST_SEPARATORS, MEAL_PHRASES, PREFER_CUES, QUALITY_PHRASES, REQUIRE_CUES, TAMIL_POST_AVAILABLE,
    TAMIL_INGREDIENT_WORDS, TAMIL_MARKERS, TAMIL_POST_EXCLUDE, TANGLISH_WORDS, UNAVAILABLE_PHRASES,
)

ROLES = ("available", "required", "preferred", "excluded", "unavailable")
# Qualities that also describe the dish text (kept for lexical/semantic retrieval). Others ("filling", "healthy",
# "quick", "low-oil"…) are scored from recipe features only, so they can't match words like "pie filling".
DESCRIPTIVE_QUALITIES = ("spicy", "creamy", "crispy", "tangy", "sweet", "comforting")

_NUMWORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
             "forty": 40, "forty-five": 45, "fortyfive": 45, "sixty": 60, "ninety": 90, "half": 0.5}
_NUM = r"(?:\d+(?:\.\d+)?|half an?|an?|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty(?:-five)?|sixty|ninety)"
_LE = r"under|below|less than|lesser than|within|in|max(?:imum)?|no more than|not more than|at most|up to|upto|<=?|ready in|done in|just|only|about|around|approx(?:imately)?|max of|inside"
_GE = r"over|above|more than|at least|atleast|min(?:imum)?|>=?|minimum of|no less than"

TIME_RE = re.compile(
    rf"(?:(?P<op>{_LE}|{_GE})\s+)?(?P<num>{_NUM})\s*(?:-|\s)?\s*(?P<unit>minutes?|mins?|min\b|hours?|hrs?|hr\b)(?:\s+(?P<post>or less|or under|max|tops|or more))?"
)
NUTRIENTS = {
    "calorie": "calories", "calories": "calories", "kcal": "calories", "kcals": "calories", "cal": "calories",
    "cals": "calories", "protein": "protein_g", "proteins": "protein_g", "carb": "carbs_g", "carbs": "carbs_g",
    "carbohydrate": "carbs_g", "carbohydrates": "carbs_g", "fat": "fat_g", "fats": "fat_g", "fibre": "fiber_g",
    "fiber": "fiber_g",
}
_NUT_WORD = r"(?P<nut>k?cals?|kcals?|calories?|proteins?|carbs?|carbohydrates?|fats?|fib(?:re|er))"
NUTRI_RE = re.compile(
    rf"(?:(?P<op>{_LE}|{_GE})\s+)?(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>g|gm|gms|grams?|kcal)?\s*(?:of\s+)?{_NUT_WORD}\b"
    rf"(?:\s+(?P<post>or less|or fewer|or under|max|or more|plus|minimum|min|\+))?"
)
NUTRI_RE_REV = re.compile(
    rf"\b{_NUT_WORD}\s+(?:of\s+|content\s+)?(?P<op>{_LE}|{_GE})\s+(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>g|gm|grams?|kcal)?"
)
SERVINGS_RE = re.compile(
    r"\b(?:for|feeds?|serves?|serving)\s+(?P<n>\d+|one|two|three|four|five|six|eight|ten|twelve)"
    r"(?:\s+(?:people|persons?|servings?|of us|adults|guests|members|kids|portions))?\b(?!\s*(?:min|hour|hr))"
)
SIMILAR_RE = re.compile(
    r"\b(?:similar to|(?:something|anything|dish(?:es)?|recipes?|meals?|food)\s+like|alternatives? to|"
    r"reminds? me of|in the style of|a version of|variation of|twist on|other than)\s+(?:a\s+|an\s+|the\s+)?"
    r"(?P<dish>[a-z][a-z' -]*?)(?=\s+(?:but|with|without|that|under|which|for|using|and|in|except)\b|[,.;!?]|$)"
)
INTENT_PATTERNS = [
    ("generate", re.compile(r"\b(create|generate|invent|come up with|make up|write me|design|compose|new recipe|"
                            r"original recipe|custom recipe|unique recipe|recipe idea of my own)\b")),
    ("meal_plan", re.compile(r"\b(meal plan|plan (?:my |a |the |out )?(?:meals|week|dinners|lunches|breakfasts|menu|day)|"
                             r"weekly (?:menu|plan)|for the (?:whole )?week|\d+[- ]day (?:meal )?plan|menu for)\b")),
    ("modify", re.compile(r"\b(make (?:it|this|that|the recipe)|replace|substitute|swap|instead of|remove \w+ from|"
                          r"reduce the|increase the|scale (?:it|this)|double (?:it|the)|halve|less spicy|more spicy|"
                          r"tone down|(?:this|that|the) recipe for \d+|for (?:\d+|two|four) people instead)\b")),
    ("question", re.compile(r"^(how (?:long|many|much|do i|to)|what(?:'s| is| are) (?:in|the)|is (?:it|this|that)|"
                            r"does (?:it|this)|can i|which one|tell me (?:about|more))\b")),
    ("greeting", re.compile(r"^(hi|hello|hey|thanks|thank you|vanakkam|ok|okay|cool|great)\W*$")),
]
FIND_BY_INGREDIENTS_RE = re.compile(
    r"\b(what can i (?:cook|make|prepare)|what (?:should|could) i (?:cook|make)|i have|i've got|ive got|"
    r"in my (?:fridge|pantry)|using up|enna (?:cook|samaikka|seyya|panna|pannalam)|cook pannalam|enkitta)\b"
)


@dataclass
class IngredientRef:
    name: str
    display: str
    role: str
    quantity: float | None = None
    unit: str | None = None
    quantity_text: str | None = None


@dataclass
class NutritionConstraint:
    nutrient: str
    op: str          # "<=" | ">="
    value: float
    text: str


@dataclass
class ParsedQuery:
    original: str
    normalized: str
    corrected: str
    corrections: list[tuple[str, str]] = field(default_factory=list)
    language: str = "en"
    intent: str = "search"
    ingredients: list[IngredientRef] = field(default_factory=list)
    excluded_groups: list[str] = field(default_factory=list)
    diets: list[str] = field(default_factory=list)
    cuisines: list[str] = field(default_factory=list)
    meal_types: list[str] = field(default_factory=list)
    max_time_min: int | None = None
    nutrition: list[NutritionConstraint] = field(default_factory=list)
    qualities: list[str] = field(default_factory=list)
    servings: int | None = None
    similar_to: str | None = None
    free_text: str = ""
    notes: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    clarification: str | None = None

    def names(self, role: str) -> list[str]:
        return [i.name for i in self.ingredients if i.role == role]


def _to_number(s: str) -> float:
    s = s.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return float(s)
    if s.startswith("half"):
        return 0.5
    return float(_NUMWORDS.get(s, 1))


def _find_phrases(words: list[str], table: dict[str, str], used: set[int]) -> list[tuple[int, int, str]]:
    """Greedy longest match of multiword phrases from `table` over word tokens not yet used."""
    keys = {tuple(k.replace("-", " - ").split()): v for k, v in table.items()}
    maxlen = max(len(k) for k in keys)
    out, i = [], 0
    while i < len(words):
        hit = None
        for n in range(min(maxlen, len(words) - i), 0, -1):
            span = range(i, i + n)
            if any(k in used for k in span):
                continue
            if tuple(words[i : i + n]) in keys:
                hit = (i, i + n, keys[tuple(words[i : i + n])])
                break
        if hit:
            out.append(hit)
            i = hit[1]
        else:
            i += 1
    return out


class QueryParser:
    def __init__(self, speller: SpellCorrector | None = None, lexicon: Lexicon | None = None):
        self.lex = lexicon or get_lexicon()
        self.extractor = IngredientExtractor(self.lex)
        self.speller = speller

    # ------------------------------------------------------------------ main entry
    def parse(self, text: str) -> ParsedQuery:
        norm = normalize(text)[:1000]
        corrected, corrections = (norm, [])
        if self.speller:
            corrected, corr = self.speller.correct(norm)
            corrections = [(c.original, c.corrected) for c in corr]
        q = ParsedQuery(original=text, normalized=norm, corrected=corrected, corrections=corrections)
        tokens = tokenize(corrected)
        words = [t.text for t in tokens]
        used: set[int] = set()

        tamil_hits = {w for w in words if w in TAMIL_MARKERS} | {w for w in words if re.match(r"[஀-௿]", w)}
        tamil_hits |= {w for w in words if w in TAMIL_INGREDIENT_WORDS}
        if tamil_hits:
            q.language = "ta-en"

        self._extract_regex_constraints(q, corrected, tokens, used)
        self._extract_phrase_constraints(q, tokens, used)
        mentions = self._extract_mentions(q, corrected, tokens, used)
        self._assign_roles(q, tokens, mentions, used)
        self._detect_intent(q, corrected, tokens, mentions)
        self._free_text(q, tokens, used, mentions)
        self._check_conflicts_and_ambiguity(q, tokens, mentions)
        return q

    # ------------------------------------------------------------------ constraints
    def _mark(self, tokens: list[Token], start: int, end: int, used: set[int]) -> None:
        for k, t in enumerate(tokens):
            if t.start >= start and t.end <= end:
                used.add(k)

    def _extract_regex_constraints(self, q: ParsedQuery, text: str, tokens: list[Token], used: set[int]) -> None:
        for m in NUTRI_RE.finditer(text):
            nut = NUTRIENTS.get(m.group("nut").rstrip("s") if m.group("nut") not in NUTRIENTS else m.group("nut"))
            nut = nut or NUTRIENTS.get(m.group("nut"))
            if not nut:
                continue
            op_word = (m.group("op") or "") + " " + (m.group("post") or "")
            q.nutrition.append(NutritionConstraint(nut, self._op(op_word, nut), float(m.group("num")), m.group(0).strip()))
            self._mark(tokens, m.start(), m.end(), used)
        for m in NUTRI_RE_REV.finditer(text):
            nut = NUTRIENTS.get(m.group("nut")) or NUTRIENTS.get(m.group("nut").rstrip("s"))
            if not nut or any(c.nutrient == nut and c.value == float(m.group("num")) for c in q.nutrition):
                continue
            q.nutrition.append(NutritionConstraint(nut, self._op(m.group("op"), nut), float(m.group("num")), m.group(0).strip()))
            self._mark(tokens, m.start(), m.end(), used)
        for m in TIME_RE.finditer(text):
            if any(t.start >= m.start() and t.end <= m.end() and k in used for k, t in enumerate(tokens)):
                continue
            minutes = _to_number(m.group("num")) * (60 if m.group("unit").startswith("h") else 1)
            op_word = (m.group("op") or "") + " " + (m.group("post") or "")
            if re.search(_GE, op_word) and not re.search(r"\b(" + _LE + r")\b", op_word):
                q.notes.append(f"Minimum cooking times are not used as a filter (\"{m.group(0).strip()}\").")
            else:
                q.max_time_min = int(round(minutes)) if q.max_time_min is None else min(q.max_time_min, int(round(minutes)))
            self._mark(tokens, m.start(), m.end(), used)
        m = SERVINGS_RE.search(text)
        if m:
            q.servings = int(_to_number(m.group("n")))
            self._mark(tokens, m.start(), m.end(), used)
        m = SIMILAR_RE.search(text)
        if m and m.group("dish").strip() not in STOPWORDS:
            q.similar_to = m.group("dish").strip()
            self._mark(tokens, m.start(), m.end(), used)

    @staticmethod
    def _op(op_word: str, nutrient: str) -> str:
        op_word = (op_word or "").strip()
        if re.search(r"\b(no|not) (more|over|above)\b", op_word):
            return "<="
        if re.search(r"\b(no|not) (less|fewer|under|below)\b", op_word):
            return ">="
        if re.search(rf"\b(?:{_GE})\b|or more|plus|\+|minimum|min\b", op_word):
            return ">="
        if re.search(rf"\b(?:{_LE})\b|or less|or fewer|or under|max", op_word):
            return "<="
        return ">=" if nutrient in ("protein_g", "fiber_g") else "<="

    def _extract_phrase_constraints(self, q: ParsedQuery, tokens: list[Token], used: set[int]) -> None:
        words = [t.text for t in tokens]
        # lexicon phrases that contain constraint words must win ("light brown sugar", "sweet potato")
        protected = set()
        for s, e, _ in self.lex.match(words):
            if e - s > 1:
                protected.update(range(s, e))
        blocked = used | protected
        for s, e, diet in _find_phrases(words, DIET_PHRASES, blocked):
            if diet not in q.diets:
                q.diets.append(diet)
            used.update(range(s, e))
        for s, e, c in _find_phrases(words, CUISINE_PHRASES, used | protected):
            if c not in q.cuisines:
                q.cuisines.append(c)
            used.update(range(s, e))
        for s, e, mt in _find_phrases(words, MEAL_PHRASES, used | protected):
            if mt not in q.meal_types:
                q.meal_types.append(mt)
            used.update(range(s, e))
        for s, e, ql in _find_phrases(words, QUALITY_PHRASES, used | protected):
            if ql not in q.qualities:
                q.qualities.append(ql)
            used.update(range(s, e))
        if "spicy" in q.qualities and "mild" in q.qualities:
            q.qualities.remove("spicy")

    # ------------------------------------------------------------------ ingredients
    def _extract_mentions(self, q: ParsedQuery, text: str, tokens: list[Token], used: set[int]) -> list[Mention]:
        mentions = [m for m in self.extractor.mentions(text, tokens) if not any(k in used for k in range(m.start, m.end))]
        # non-lexicon groups ("gluten", "soy", "wheat") become pseudo-ingredients "group:<name>"
        words = [t.text for t in tokens]
        taken = {k for m in mentions for k in range(m.start, m.end)} | used
        for s, e, g in _find_phrases(words, {k: v for k, v in GROUP_WORDS.items() if v in
                                              ("gluten", "soy", "onion_garlic", "animal", "tree_nut")}, taken):
            mentions.append(Mention(name=f"group:{g}", display=" ".join(words[s:e]), start=s, end=e,
                                    char_start=tokens[s].start, char_end=tokens[e - 1].end))
        mentions.sort(key=lambda m: m.start)
        return mentions

    def _assign_roles(self, q: ParsedQuery, tokens: list[Token], mentions: list[Mention], used: set[int] | None = None) -> None:
        words = [t.text for t in tokens]
        text = " ".join(words)
        roles: list[str | None] = [None] * len(mentions)

        def window_role(lo: int, hi: int) -> str | None:
            win = [words[k] for k in range(lo, hi) if k not in (used or ())]
            joined = " " + " ".join(win) + " "
            if any(f" {p} " in joined for p in UNAVAILABLE_PHRASES):
                return "unavailable"
            if any(f" {p} " in joined for p in EXCLUDE_PHRASES) or (set(win) & EXCLUDE_CUES):
                return "excluded"
            if any(f" {p} " in joined for p in AVAILABLE_PHRASES) or (set(win) & AVAILABLE_CUES):
                return "available"
            if set(win) & {"only", "must", "need", "needs", "require", "required"}:
                return "required"
            if set(win) & REQUIRE_CUES:
                return "required"
            if set(win) & PREFER_CUES:
                return "preferred"
            return None

        prev_end = 0
        for i, m in enumerate(mentions):
            between = words[prev_end : m.start]
            chained = i > 0 and between and all(w in LIST_SEPARATORS for w in between)
            adjacent = i > 0 and not between
            # clause start: last hard boundary before the mention (but list commas don't break a chain)
            lo = prev_end
            for k in range(m.start - 1, prev_end - 1, -1):
                if words[k] in {".", ";", "!", "?", "but", "though", "however"}:
                    lo = k + 1
                    break
            if (chained or adjacent) and roles[i - 1] is not None:
                cue = window_role(lo, m.start) if not chained else None
                roles[i] = cue or roles[i - 1]
            else:
                roles[i] = window_role(lo, m.start)
                if roles[i] is None and lo == prev_end and i > 0 and roles[i - 1] in ("available",) and not (
                    set(between) & {"but", "without", "with"}
                ):
                    roles[i] = roles[i - 1]
            nxt_word = words[m.end] if m.end < len(words) else ""
            if (roles[i] in ("excluded", "unavailable") and chained and nxt_word and tokens[m.end].is_word
                    and nxt_word not in LIST_SEPARATORS and nxt_word not in STOPWORDS
                    and nxt_word not in TAMIL_POST_EXCLUDE and nxt_word not in {"please", "free"}):
                # "no eggs, chocolate cake": a mention followed by a dish noun starts a new phrase
                roles[i] = window_role(m.start, m.start) or None
            if m.start > 0 and words[m.start - 1] in ("more", "extra", "lots", "plenty"):
                roles[i] = "preferred"
            # suffix negation: "peanut-free", "onion free"
            after = words[m.end : m.end + 2]
            if after[:1] == ["free"] or after[:2] == ["-", "free"]:
                roles[i] = "excluded"
            prev_end = m.end

        # Tamil postpositional cues apply to the mention and the list chained before it
        for i, m in enumerate(mentions):
            nxt = words[m.end : m.end + 2]
            post = None
            if set(nxt) & TAMIL_POST_EXCLUDE:
                post = "excluded"
            elif set(nxt) & TAMIL_POST_AVAILABLE:
                post = "available"
            if not post:
                continue
            roles[i] = post
            j = i
            while j > 0 and all(w in LIST_SEPARATORS for w in words[mentions[j - 1].end : mentions[j].start]):
                j -= 1
                roles[j] = post

        # "X is fine / X is ok" re-allows something excluded earlier in the same message
        bare_list = self._is_bare_list(words, mentions, q)
        find_mode = bool(FIND_BY_INGREDIENTS_RE.search(text)) or bare_list
        for i, m in enumerate(mentions):
            role = roles[i]
            if role is None:
                role = "available" if find_mode else "preferred"
            if role == "required" and find_mode and not re.search(r"\bonly\b", text):
                role = "available"
            name = m.name
            if name.startswith("group:"):
                group = name.split(":", 1)[1]
                if role in ("excluded", "unavailable"):
                    if group not in q.excluded_groups:
                        q.excluded_groups.append(group)
                continue
            if role == "excluded":
                g = self._group_for_entry(name, words[m.start : m.end])
                if g and g not in q.excluded_groups:
                    q.excluded_groups.append(g)
            if any(r.name == name and r.role == role for r in q.ingredients):
                continue
            q.ingredients.append(IngredientRef(name=name, display=m.display, role=role, quantity=m.quantity,
                                               unit=m.unit, quantity_text=m.quantity_text))

    def _group_for_entry(self, name: str, surface: list[str]) -> str | None:
        """Excluding a group-like ingredient also excludes its allergen group (e.g. "no nuts" -> peanuts too)."""
        phrase = " ".join(surface)
        if phrase in ("meat", "meats", "non veg", "nonveg"):
            return "meat"
        return {"dairy": "dairy", "milk": None, "egg": "egg", "nut": "nuts", "peanut": "peanut", "sesame seed": "sesame",
                "fish": "fish", "shellfish": "shellfish", "seafood": "seafood", "soybean": "soy",
                "alcohol": "alcohol"}.get(name)

    def _is_bare_list(self, words: list[str], mentions: list[Mention], q: ParsedQuery) -> bool:
        if len(mentions) < 2:
            return False
        covered = {k for m in mentions for k in range(m.start, m.end)}
        rest = [w for k, w in enumerate(words) if k not in covered and w not in LIST_SEPARATORS and w not in STOPWORDS
                and w not in TANGLISH_WORDS and w not in {".", "?", "!", "-", "(", ")"} and not re.fullmatch(r"[\d./]+", w)
                and w not in UNITS and w not in SIZE_WORDS and w not in WORD_NUMBERS and w not in VAGUE]
        free = [w for k, w in enumerate(words) if k not in covered]
        if set(free) & (REQUIRE_CUES | EXCLUDE_CUES | PREFER_CUES):
            return False  # "something with X and Y" states requirements, not a pantry list
        has_sep = any(w in LIST_SEPARATORS for w in free)
        return not rest and (has_sep or len(mentions) >= 3)

    # ------------------------------------------------------------------ intent
    def _detect_intent(self, q: ParsedQuery, text: str, tokens: list[Token], mentions: list[Mention]) -> None:
        for intent, rx in INTENT_PATTERNS:
            if rx.search(text):
                q.intent = intent
                break
        else:
            if q.similar_to:
                q.intent = "similar"
            elif q.names("available") or FIND_BY_INGREDIENTS_RE.search(text):
                q.intent = "find_by_ingredients"
            else:
                q.intent = "search"
        if q.intent == "question" and (q.names("available") or q.names("required")) and not re.search(r"\b(it|this|that)\b", text):
            q.intent = "find_by_ingredients" if q.names("available") else "search"

    # ------------------------------------------------------------------ free text for retrieval
    def _free_text(self, q: ParsedQuery, tokens: list[Token], used: set[int], mentions: list[Mention]) -> None:
        excluded_tok = set()
        role_by_name = {}
        for r in q.ingredients:
            role_by_name.setdefault(r.name, r.role)
        for m in mentions:
            if m.name.startswith("group:") or role_by_name.get(m.name) in ("excluded", "unavailable"):
                excluded_tok.update(range(m.start, m.end))
        cue_words = (EXCLUDE_CUES | AVAILABLE_CUES | REQUIRE_CUES | PREFER_CUES | TAMIL_POST_EXCLUDE
                     | TAMIL_POST_AVAILABLE | TANGLISH_WORDS | {"free", "allergic", "minutes", "minute", "mins", "don't",
                                                                "dont", "can't", "cant", "please", "suggest"})
        canonical = {m.start: (m.end, m.name) for m in mentions if not m.name.startswith("group:")}
        keep = []
        skip_until = -1
        for k, t in enumerate(tokens):
            w = t.text
            if k < skip_until:
                continue
            if k in canonical and k not in excluded_tok:
                end, name = canonical[k]
                keep.extend(name.split())   # canonical form ("capsicum" -> "bell pepper") for retrieval
                skip_until = end
                continue
            if k in excluded_tok or not t.is_word or w in STOPWORDS or w in cue_words:
                continue
            if k in used and not any(w in d.split() for d in (*q.cuisines, *q.meal_types, *DESCRIPTIVE_QUALITIES, *q.diets)):
                continue
            keep.append(w)
        if q.similar_to:
            keep = q.similar_to.split() + keep
        q.free_text = " ".join(dict.fromkeys(keep))

    # ------------------------------------------------------------------ ambiguity / conflicts
    def _check_conflicts_and_ambiguity(self, q: ParsedQuery, tokens: list[Token], mentions: list[Mention]) -> None:
        words = [t.text for t in tokens]
        for m in mentions:
            if words[m.start : m.end] == ["pepper"]:
                q.notes.append("'pepper' was read as black pepper (the spice); say 'bell pepper' or 'capsicum' for the vegetable.")
            if words[m.start : m.end] in (["chili"], ["chilli"], ["chile"]) and len(mentions) == 1:
                q.notes.append("'chili' was read as the chili pepper ingredient, not the dish chili con carne.")
        positive = {r.name for r in q.ingredients if r.role in ("required", "available", "preferred")}
        for r in q.ingredients:
            if r.role == "excluded" and r.name in positive:
                q.conflicts.append(f"'{r.display}' is both requested and excluded.")
        required = [r for r in q.ingredients if r.role == "required"]
        for diet in q.diets:
            for r in required:
                e = self.lex.get(r.name)
                if not e:
                    continue
                if diet in ("vegetarian", "vegan", "eggetarian") and not e.vegetarian:
                    q.conflicts.append(f"'{r.display}' is not {diet}.")
                elif diet == "vegan" and not e.vegan:
                    q.conflicts.append(f"'{r.display}' is not vegan ({', '.join(sorted(e.allergens & {'dairy', 'egg'})) or 'animal product'}).")
        if "vegetarian" in q.diets and "non-vegetarian" in q.diets:
            q.conflicts.append("Both vegetarian and non-vegetarian were requested.")
        if q.max_time_min is not None and q.max_time_min < 5:
            q.notes.append(f"A {q.max_time_min}-minute limit is very short; few recipes state times that low.")
        has_content = (q.ingredients or q.diets or q.cuisines or q.meal_types or q.qualities or q.nutrition
                       or q.max_time_min or q.similar_to or len(q.free_text.split()) >= 1)
        if q.intent == "greeting":
            q.clarification = "Hi! Tell me what ingredients you have or what kind of dish you feel like."
        elif not has_content:
            q.clarification = ("Could you tell me a bit more? For example, ingredients you have, a cuisine, "
                               "a meal (breakfast, dinner…) or a time limit.")
