"""Per-user data in the NLP service: preferences, interactions, recommendations, feedback, saved searches."""
from __future__ import annotations

import time
from typing import Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .. import db, services
from ..auth import current_user_id, require_user
from ..convert import load_prefs, prefs_for_search, recipe_card, save_prefs
from ..nlp.query import ParsedQuery
from ..schemas_nlp import RecipeCard

router = APIRouter(prefix="/api", tags=["personalisation"])


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    diet: Literal["vegetarian", "vegan", "eggetarian", "pescatarian", "non-vegetarian", "jain"] | None = None
    vegetarian_includes_eggs: bool = False
    allergies: list[str] = Field(default_factory=list, max_length=20)
    disliked_ingredients: list[str] = Field(default_factory=list, max_length=50)
    liked_ingredients: list[str] = Field(default_factory=list, max_length=50)
    liked_cuisines: list[str] = Field(default_factory=list, max_length=20)
    staples: list[str] = Field(default_factory=list, max_length=50)
    apply_profile: bool = True


class PreferencesOut(Preferences):
    unrecognised: list[str] = []


@router.get("/me/preferences", response_model=PreferencesOut)
def get_preferences(user_id: str = Depends(require_user)):
    return PreferencesOut(**{k: v for k, v in load_prefs(user_id).items() if k in Preferences.model_fields})


@router.put("/me/preferences", response_model=PreferencesOut)
def put_preferences(body: Preferences, user_id: str = Depends(require_user)):
    lex = services.get_engine().lex
    data = body.model_dump()
    unknown = []
    for key in ("disliked_ingredients", "liked_ingredients", "staples"):
        cleaned = []
        for item in data[key]:
            item = item.strip()[:60]
            if not item:
                continue
            if not lex.lookup(item):
                unknown.append(item)
            cleaned.append(item)
        data[key] = cleaned
    data["allergies"] = [a.strip().lower()[:40] for a in data["allergies"] if a.strip()]
    save_prefs(user_id, data)
    return PreferencesOut(**data, unrecognised=unknown)


class InteractionIn(BaseModel):
    recipe_id: int
    kind: Literal["view", "rating", "favorite", "unfavorite"]
    value: float | None = Field(None, ge=1, le=5)


@router.post("/interactions", status_code=204)
def add_interaction(body: InteractionIn, user_id: str = Depends(require_user)):
    if not db.get_recipe(body.recipe_id):
        raise HTTPException(404, "Recipe not found")
    with db.tx() as conn:
        if body.kind == "unfavorite":
            conn.execute("DELETE FROM interactions WHERE user_id = ? AND recipe_id = ? AND kind = 'favorite'", (user_id, body.recipe_id))
        elif body.kind in ("rating", "favorite"):
            conn.execute("DELETE FROM interactions WHERE user_id = ? AND recipe_id = ? AND kind = ?", (user_id, body.recipe_id, body.kind))
            conn.execute("INSERT INTO interactions(user_id, recipe_id, kind, value, created_at) VALUES (?, ?, ?, ?, ?)",
                         (user_id, body.recipe_id, body.kind, body.value, time.time()))
        else:
            conn.execute("INSERT INTO interactions(user_id, recipe_id, kind, value, created_at) VALUES (?, ?, 'view', NULL, ?)",
                         (user_id, body.recipe_id, time.time()))


class MyRecipeState(BaseModel):
    favorite: bool
    rating: float | None


@router.get("/interactions/{recipe_id}", response_model=MyRecipeState)
def my_state(recipe_id: int, user_id: str = Depends(require_user)):
    conn = db.get_conn()
    fav = conn.execute("SELECT 1 FROM interactions WHERE user_id = ? AND recipe_id = ? AND kind = 'favorite'", (user_id, recipe_id)).fetchone()
    rating = conn.execute("SELECT value FROM interactions WHERE user_id = ? AND recipe_id = ? AND kind = 'rating'", (user_id, recipe_id)).fetchone()
    return MyRecipeState(favorite=bool(fav), rating=rating[0] if rating else None)


class Recommendation(BaseModel):
    recipe: RecipeCard
    reason: str


@router.get("/me/recently-viewed", response_model=list[RecipeCard])
def recently_viewed(user_id: str = Depends(require_user)):
    rows = db.get_conn().execute(
        "SELECT recipe_id, MAX(created_at) t FROM interactions WHERE user_id = ? AND kind = 'view' GROUP BY recipe_id ORDER BY t DESC LIMIT 8",
        (user_id,)).fetchall()
    return [c for c in (recipe_card(r[0]) for r in rows) if c]


@router.get("/me/recommendations", response_model=list[Recommendation])
def recommendations(request: Request, k: int = 8):
    """Explainable, content-based: neighbours of what you favourited/rated highly + your liked cuisines/ingredients.
    Hard exclusions (allergies, diet) from your preferences are always applied first."""
    eng = services.get_engine()
    user_id = current_user_id(request)
    if not user_id:
        raise HTTPException(401, "Login required")
    prefs = prefs_for_search(user_id, True)
    conn = db.get_conn()
    liked = [r[0] for r in conn.execute(
        "SELECT recipe_id FROM interactions WHERE user_id = ? AND (kind = 'favorite' OR (kind = 'rating' AND value >= 4))", (user_id,))]
    seen = {r[0] for r in conn.execute("SELECT recipe_id FROM interactions WHERE user_id = ?", (user_id,))}
    pq = ParsedQuery(original="", normalized="", corrected="")
    keep = eng.active.copy()
    for _, m in services.ranker._hard_constraints(pq, prefs, []):
        keep &= m
    score = np.zeros(len(eng.ids), dtype=np.float32)
    reason: dict[int, str] = {}
    vecs = [eng.embed.vector(r) for r in liked if eng.embed is not None and eng.embed.vector(r) is not None]
    if vecs:
        profile = np.mean(vecs, axis=0)
        profile /= np.linalg.norm(profile) or 1.0
        score += eng.embedding_scores_vec(profile)
        anchor = eng.titles[eng.pos_of[liked[-1]]] if liked[-1] in eng.pos_of else "your favourites"
        for i in np.argsort(-score)[:200]:
            reason[int(i)] = f"Similar to recipes you liked (e.g. {anchor})"
    for c in prefs.liked_cuisines:
        for i, f in enumerate(eng.features):
            if f.cuisine and (f.cuisine == c or services.ranker._cuisine_score(f, c) >= 3):
                score[i] += 0.3
                reason.setdefault(i, f"Matches your liked cuisine: {c}")
    for ing in prefs.liked_ingredients:
        for i in eng.index.get(ing, ()):
            score[i] += 0.2
            reason.setdefault(i, f"Uses {ing}, which you like")
    if not score.any():
        return []
    for rid in seen:
        if rid in eng.pos_of:
            keep[eng.pos_of[rid]] = False
    score = np.where(keep, score, -1e9)
    out = []
    for i in np.argsort(-score)[: k * 2]:
        if score[i] <= 0 or len(out) >= k:
            break
        card = recipe_card(eng.ids[i])
        if card:
            out.append(Recommendation(recipe=card, reason=reason.get(int(i), "Popular with your preferences")))
    return out


class FeedbackIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    recipe_id: int
    helpful: bool


@router.post("/nlp/feedback", status_code=204)
def feedback(body: FeedbackIn, request: Request):
    with db.tx() as conn:
        conn.execute("INSERT INTO search_feedback(user_id, query, recipe_id, helpful, created_at) VALUES (?, ?, ?, ?, ?)",
                     (current_user_id(request), body.query, body.recipe_id, int(body.helpful), time.time()))


class SavedSearchIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class SavedSearch(BaseModel):
    id: int
    query: str
    created_at: float


@router.get("/me/saved-searches", response_model=list[SavedSearch])
def list_saved(user_id: str = Depends(require_user)):
    rows = db.get_conn().execute("SELECT id, query, created_at FROM saved_searches WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    return [SavedSearch(id=r[0], query=r[1], created_at=r[2]) for r in rows]


@router.post("/me/saved-searches", response_model=SavedSearch, status_code=201)
def add_saved(body: SavedSearchIn, user_id: str = Depends(require_user)):
    now = time.time()
    with db.tx() as conn:
        cur = conn.execute("INSERT INTO saved_searches(user_id, query, created_at) VALUES (?, ?, ?)", (user_id, body.query.strip(), now))
    return SavedSearch(id=cur.lastrowid, query=body.query.strip(), created_at=now)


@router.delete("/me/saved-searches/{sid}", status_code=204)
def del_saved(sid: int, user_id: str = Depends(require_user)):
    with db.tx() as conn:
        conn.execute("DELETE FROM saved_searches WHERE id = ? AND user_id = ?", (sid, user_id))
