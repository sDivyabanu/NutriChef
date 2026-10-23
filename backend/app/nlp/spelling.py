"""Typo correction for queries.

A word is only corrected when it is *unknown*: not in the recipe-corpus vocabulary (freq >= MIN_KNOWN_FREQ),
the ingredient lexicon, the constraint vocabulary or the Tamil/Tanglish function words. Candidates come from
domain terms first (ingredients, diets, cuisines, meal types) so "panner" -> "paneer", not "planner".
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from rapidfuzz import process
from rapidfuzz.distance import DamerauLevenshtein

MIN_KNOWN_FREQ = 3
MIN_TARGET_FREQ = 25


@dataclass
class Correction:
    original: str
    corrected: str
    distance: int


def max_edits(word: str) -> int:
    n = len(word)
    if n <= 3:
        return 0
    if n <= 5:
        return 1
    return 2


class SpellCorrector:
    def __init__(self, corpus_counts: Counter, domain_terms: set[str], protected: set[str]):
        self.counts = corpus_counts
        self.domain = {t for t in domain_terms if t.isalpha() and len(t) > 2}
        self.protected = protected
        frequent = {w for w, c in corpus_counts.items() if c >= MIN_TARGET_FREQ and w.isalpha() and len(w) > 3}
        self._domain_list = sorted(self.domain)
        self._general_list = sorted(frequent - self.domain)

    def known(self, word: str) -> bool:
        return (
            word in self.domain
            or word in self.protected
            or self.counts.get(word, 0) >= MIN_KNOWN_FREQ
            or not word.isalpha()
        )

    def correct_word(self, word: str) -> Correction | None:
        if self.known(word):
            return None
        k = max_edits(word)
        if k == 0:
            return None
        for pool in (self._domain_list, self._general_list):
            cands = process.extract(word, pool, scorer=DamerauLevenshtein.distance, score_cutoff=k, limit=8)
            if not cands:
                continue
            # fewest edits, then same first letter, then most frequent
            best = min(cands, key=lambda c: (c[1], c[0][0] != word[0], -self.counts.get(c[0], 0)))
            return Correction(word, best[0], int(best[1]))
        return None

    def correct(self, text: str) -> tuple[str, list[Correction]]:
        """Correct a normalised text word by word; returns (corrected_text, corrections)."""
        out: list[str] = []
        corrections: list[Correction] = []
        pos = 0
        for m in re.finditer(r"[a-z]+", text):
            out.append(text[pos : m.start()])
            fix = self.correct_word(m.group(0))
            if fix:
                corrections.append(fix)
                out.append(fix.corrected)
            else:
                out.append(m.group(0))
            pos = m.end()
        out.append(text[pos:])
        return "".join(out), corrections
