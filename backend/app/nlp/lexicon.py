"""Curated ingredient lexicon: canonical names, synonyms (regional + Tamil), is-a hierarchy, diet/allergen facts."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .text import normalize, tokenize

log = logging.getLogger(__name__)

DATA = Path(__file__).parent / "data" / "ingredients.txt"
ANIMAL_CATEGORIES = {"meat": "meat", "poultry": "poultry", "fish": "seafood", "shellfish": "seafood"}
ALLERGEN_GROUPS = ("dairy", "egg", "peanut", "tree_nut", "soy", "gluten", "fish", "shellfish", "sesame", "mustard", "celery")
MAX_PHRASE = 6
# Group nodes that are too broad to stand in for a specific ingredient.
BROAD_GROUPS = frozenset(
    "vegetable fruit herb spice dairy cheese nut meat poultry seafood fish shellfish legume alcohol broth berry "
    "leafy greens squash bread juice sugar flour wine spirit cream milk sweetener chocolate".split()
)


@dataclass
class Entry:
    name: str
    category: str
    parent: str | None
    tags: set[str]
    synonyms: list[str]
    ancestors: tuple[str, ...] = ()           # self first, then parent chain
    descendants: set[str] = field(default_factory=set)
    allergens: set[str] = field(default_factory=set)
    maybe_allergens: set[str] = field(default_factory=set)
    animal: str | None = None                 # meat | poultry | seafood | None
    vegetarian: bool = True
    vegan: bool = True
    staple: bool = False
    spicy: bool = False


def pluralize(word: str) -> list[str]:
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return [word + "es"]
    if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        return [word[:-1] + "ies"]
    if word.endswith("leaf"):
        return [word[:-4] + "leaves"]
    if word.endswith("o"):
        return [word + "es", word + "s"]
    if word.endswith("i") and word.startswith("chil"):
        return [word + "es", word + "s"]
    return [word + "s"]


class Lexicon:
    def __init__(self, path: Path = DATA):
        self.entries: dict[str, Entry] = {}
        self.surface: dict[tuple[str, ...], str] = {}
        self._load(path)
        self._derive()

    # ------------------------------------------------------------------ loading
    def _load(self, path: Path) -> None:
        explicit: dict[tuple[str, ...], str] = {}
        generated: dict[tuple[str, ...], str] = {}
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 5:
                raise ValueError(f"{path.name}:{lineno}: expected 5 fields, got {len(parts)}")
            name, category, parent, tags, syns = parts
            if name in self.entries:
                raise ValueError(f"{path.name}:{lineno}: duplicate entry {name!r}")
            synonyms = [s.strip() for s in syns.split(",") if s.strip()]
            self.entries[name] = Entry(name, category, parent or None, set(tags.split()), synonyms)
            for form in [name, *synonyms]:
                toks = tuple(t.text for t in tokenize(normalize(form)) if t.text not in "-'")
                if not toks:
                    continue
                if toks in explicit and explicit[toks] != name:
                    log.debug("surface %r maps to both %s and %s; keeping first", toks, explicit[toks], name)
                    continue
                explicit[toks] = name
                for plural in pluralize(toks[-1]):
                    generated.setdefault(toks[:-1] + (plural,), name)
        for toks, name in generated.items():
            explicit.setdefault(toks, name)  # explicit forms always win over generated plurals
        self.surface = explicit
        missing = {e.parent for e in self.entries.values() if e.parent and e.parent not in self.entries}
        if missing:
            raise ValueError(f"unknown parent(s): {sorted(missing)}")

    def _derive(self) -> None:
        for e in self.entries.values():
            chain, cur, seen = [], e, set()
            while cur and cur.name not in seen:
                seen.add(cur.name)
                chain.append(cur.name)
                cur = self.entries.get(cur.parent) if cur.parent else None
            e.ancestors = tuple(chain)
        for e in self.entries.values():
            for anc in e.ancestors:
                self.entries[anc].descendants.add(e.name)
        for e in self.entries.values():
            chain = [self.entries[a] for a in e.ancestors]
            for a in chain:
                e.allergens |= {t.split(":", 1)[1] for t in a.tags if t.startswith("allergen:")}
                e.maybe_allergens |= {t.split(":", 1)[1] for t in a.tags if t.startswith("maybe:")}
                if a.category in ANIMAL_CATEGORIES and e.animal is None:
                    e.animal = ANIMAL_CATEGORIES[a.category]
                if a.category == "dairy":
                    e.allergens.add("dairy")
                if a.category == "egg":
                    e.allergens.add("egg")
                if "spicy" in a.tags:
                    e.spicy = True
            e.maybe_allergens -= e.allergens
            e.vegetarian = e.animal is None and "nonveg" not in e.tags
            e.vegan = e.vegetarian and not ({"dairy", "egg"} & e.allergens) and "nonvegan" not in e.tags
            e.staple = "staple" in e.tags

    # ------------------------------------------------------------------ queries
    def __contains__(self, name: str) -> bool:
        return name in self.entries

    def get(self, name: str) -> Entry | None:
        return self.entries.get(name)

    def lookup(self, phrase: str) -> str | None:
        toks = tuple(t.text for t in tokenize(normalize(phrase)) if t.text not in "-'")
        return self.surface.get(toks)

    def match(self, words: list[str]) -> list[tuple[int, int, str]]:
        """Greedy longest-match over a word sequence -> [(start, end, canonical)] (end exclusive)."""
        out, i, n = [], 0, len(words)
        while i < n:
            hit = None
            for length in range(min(MAX_PHRASE, n - i), 0, -1):
                name = self.surface.get(tuple(words[i : i + length]))
                if name:
                    hit = (i, i + length, name)
                    break
            if hit:
                out.append(hit)
                i = hit[1]
            else:
                i += 1
        return out

    def is_a(self, name: str, other: str) -> bool:
        e = self.entries.get(name)
        return bool(e and other in e.ancestors)

    def satisfies(self, have: set[str], need: str, allow_broad: bool = False) -> bool:
        """Does what the user has cover a recipe requirement?

        - exact or more specific form: have cherry tomato -> need tomato
        - a specific parent covers its varieties: have rice -> need basmati rice, have onion -> need red onion
        - broad groups never do: have cheese -/-> need paneer, have sugar -/-> need brown sugar
        - allow_broad: a specific item covers a generic requirement (have paneer -> recipe needs "cheese");
          used when listing missing ingredients, not when deciding a recipe "uses" what you have
        """
        if need in have:
            return True
        e = self.entries.get(need)
        if not e:
            return False
        if have & e.descendants and (allow_broad or need not in BROAD_GROUPS):
            return True
        return any(anc in have and anc not in BROAD_GROUPS for anc in e.ancestors[1:])

    def all_surface_forms(self) -> list[str]:
        return [" ".join(t) for t in self.surface]


@lru_cache(maxsize=1)
def get_lexicon() -> Lexicon:
    return Lexicon()
