"""Recipe-to-recipe similarity, comparison and duplicate detection."""
from __future__ import annotations

import numpy as np

from .engine import NLPEngine
from .text import normalize


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def similar_recipes(engine: NLPEngine, rid: int, k: int = 6, keep_mask: np.ndarray | None = None) -> list[dict]:
    i = engine.pos_of.get(rid)
    if i is None:
        return []
    f = engine.features[i]
    base = set(f.essential)
    emb = np.zeros(len(engine.ids), dtype=np.float32)
    if engine.embed is not None and engine.embed.vector(rid) is not None:
        emb = engine.embedding_scores_vec(engine.embed.vector(rid))
    # candidates: semantic neighbours + recipes sharing essential ingredients
    cand = set(np.argsort(-emb)[:300].tolist()) if emb.any() else set()
    for name in list(base)[:12]:
        cand |= set(list(engine.index.get(f"essential:{name}", set()))[:400])
    title = normalize(engine.titles[i])
    scored = []
    for j in cand:
        if j == i or not engine.active[j] or (keep_mask is not None and not keep_mask[j]):
            continue
        if normalize(engine.titles[j]) == title:
            continue
        other = set(engine.features[j].essential)
        jac = jaccard(base, other)
        score = 0.6 * float(emb[j]) + 0.4 * jac
        scored.append((score, j, jac, sorted(base & other)))
    scored.sort(key=lambda x: -x[0])
    out = []
    for score, j, jac, shared in scored[:k]:
        reason = f"Shares {len(shared)} ingredient{'s' if len(shared) != 1 else ''}" + (f": {', '.join(shared[:4])}" if shared else "")
        out.append({"recipe_id": engine.ids[j], "title": engine.titles[j], "score": round(score, 3),
                    "ingredient_overlap": round(jac, 3), "shared": shared, "reason": reason})
    return out


def compare(engine: NLPEngine, a: int, b: int) -> dict:
    fa, fb = engine.feature(a), engine.feature(b)
    if not fa or not fb:
        return {}
    sa, sb = set(fa.essential), set(fb.essential)
    sem = None
    if engine.embed is not None and engine.embed.vector(a) is not None and engine.embed.vector(b) is not None:
        sem = round(float(engine.embed.vector(a) @ engine.embed.vector(b)), 3)
    return {
        "shared_ingredients": sorted(sa & sb), "only_in_first": sorted(sa - sb), "only_in_second": sorted(sb - sa),
        "ingredient_overlap": round(jaccard(sa, sb), 3), "semantic_similarity": sem,
        "rows": [
            {"field": "Estimated time (min)", "first": fa.est_time_min, "second": fb.est_time_min},
            {"field": "Difficulty (estimated)", "first": fa.difficulty, "second": fb.difficulty},
            {"field": "Spice level (estimated)", "first": fa.spice_level, "second": fb.spice_level},
            {"field": "Main ingredients", "first": len(fa.essential), "second": len(fb.essential)},
            {"field": "Vegetarian", "first": fa.diet["vegetarian"], "second": fb.diet["vegetarian"]},
            {"field": "Vegan", "first": fa.diet["vegan"], "second": fb.diet["vegan"]},
            {"field": "Allergens", "first": ", ".join(fa.allergens) or "none found", "second": ", ".join(fb.allergens) or "none found"},
            {"field": "Cuisine (inferred)", "first": fa.cuisine, "second": fb.cuisine},
        ],
    }


def find_duplicates(engine: NLPEngine, title: str, essential: list[str], text_for_embedding: str,
                    exclude_id: int | None = None, k: int = 5) -> list[dict]:
    """Near-duplicates: same normalised title, or high ingredient overlap plus high semantic similarity."""
    tnorm = normalize(title)
    base = set(essential)
    emb = engine.embedding_scores(text_for_embedding) if engine.embed else np.zeros(len(engine.ids), dtype=np.float32)
    cand = set(np.argsort(-emb)[:50].tolist()) if emb.any() else set()
    cand |= {j for j, t in enumerate(engine.titles) if normalize(t) == tnorm}
    out = []
    for j in cand:
        if not engine.active[j] or engine.ids[j] == exclude_id:
            continue
        same_title = normalize(engine.titles[j]) == tnorm
        jac = jaccard(base, set(engine.features[j].essential))
        sem = float(emb[j]) if emb.any() else 0.0
        if same_title and jac >= 0.5 or (jac >= 0.7 and sem >= 0.85) or jac >= 0.9:
            out.append({"recipe_id": engine.ids[j], "title": engine.titles[j], "same_title": same_title,
                        "ingredient_overlap": round(jac, 3), "semantic_similarity": round(sem, 3)})
    out.sort(key=lambda d: (-d["ingredient_overlap"], -d["semantic_similarity"]))
    return out[:k]
