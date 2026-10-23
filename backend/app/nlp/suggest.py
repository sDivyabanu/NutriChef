"""Search autocomplete: completes the word being typed from ingredients/constraint vocabulary and recipe titles."""
from __future__ import annotations

from rapidfuzz import fuzz, process

from .text import normalize
from .vocab import CUISINE_PHRASES, DIET_PHRASES, MEAL_PHRASES, QUALITY_PHRASES

_EXTRA = sorted({*DIET_PHRASES, *CUISINE_PHRASES, *MEAL_PHRASES, *QUALITY_PHRASES,
                 "under 30 minutes", "under 20 minutes", "without", "what can i cook with", "i have"})


def autocomplete(engine, q: str, limit: int = 8) -> list[str]:
    text = normalize(q)
    head, _, last = text.rpartition(" ")
    prefix = (head + " ") if head else ""
    out: list[str] = []
    if len(last) >= 2:
        vocab = sorted(set(engine.lex.entries) | set(_EXTRA))
        starts = [w for w in vocab if w.startswith(last)]
        starts.sort(key=lambda w: (len(w), w))
        if not starts and len(last) >= 4:  # typo-tolerant fallback
            starts = [m[0] for m in process.extract(last, vocab, scorer=fuzz.ratio, limit=4, score_cutoff=75)]
        out += [prefix + w for w in starts[:limit]]
    if len(text) >= 3:
        words = text.split()
        titles = []
        for t in engine.titles:
            tn = normalize(t)
            if all(w in tn for w in words):
                titles.append(t)
                if len(titles) >= limit:
                    break
        out += titles
    seen, uniq = set(), []
    for s in out:
        if s.lower() not in seen and s.lower() != text:
            seen.add(s.lower())
            uniq.append(s)
    return uniq[:limit]
