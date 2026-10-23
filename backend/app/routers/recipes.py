"""Recipe CRUD. Dataset recipes are read-only; users own the recipes they create or save."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .. import db, services
from ..auth import current_user_id, require_user
from ..convert import prefs_for_search, recipe_card
from ..nlp.similarity import compare, find_duplicates, similar_recipes
from ..schemas import Recipe, RecipeIn, RecipePage, RecipeUpdate
from ..schemas_nlp import RecipeCard
from ..services import enrich_recipe

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


def _load(recipe_id: int) -> dict:
    rec = db.get_recipe(recipe_id)
    if not rec:
        raise HTTPException(404, "Recipe not found")
    return rec


def _check_owner(rec: dict, user_id: str) -> None:
    if rec["source"] == "epicurious-13k":
        raise HTTPException(403, "Dataset recipes are read-only. Save a copy to edit it.")
    if rec["owner_id"] and rec["owner_id"] != user_id:
        raise HTTPException(403, "You can only change your own recipes")


@router.get("", response_model=RecipePage)
def list_recipes(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=100),
    q: str | None = Query(None, max_length=200, description="case-insensitive title filter (plain keyword search)"),
    mine: bool = False,
):
    owner = None
    if mine:
        owner = current_user_id(request)
        if not owner:
            raise HTTPException(401, "Login required")
    items, total = db.list_recipes(offset=offset, limit=limit, q=q, owner_id=owner)
    return RecipePage(items=[Recipe(**r) for r in items], total=total, offset=offset, limit=limit)


@router.get("/{recipe_id}", response_model=Recipe)
def get_recipe(recipe_id: int):
    return Recipe(**enrich_recipe(_load(recipe_id)))


@router.post("", response_model=Recipe, status_code=201)
def create_recipe(body: RecipeIn, user_id: str = Depends(require_user)):
    data = body.model_dump()
    generated = data.pop("generated", False)
    if body.nutrition is not None:
        data["nutrition_source"] = "user-entered"
    rid = db.create_recipe(data, source="generated" if generated else "user", owner_id=user_id)
    return Recipe(**enrich_recipe(_load(rid)))


@router.put("/{recipe_id}", response_model=Recipe)
def update_recipe(recipe_id: int, body: RecipeUpdate, user_id: str = Depends(require_user)):
    rec = _load(recipe_id)
    _check_owner(rec, user_id)
    data = body.model_dump(exclude_unset=True)
    if "nutrition" in data:
        data["nutrition_source"] = "user-entered" if data["nutrition"] else None
    db.update_recipe(recipe_id, data, changed_by=user_id)
    return Recipe(**enrich_recipe(_load(recipe_id)))


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, user_id: str = Depends(require_user)):
    rec = _load(recipe_id)
    _check_owner(rec, user_id)
    db.delete_recipe(recipe_id, changed_by=user_id)


# ---------------------------------------------------------------- recipe intelligence
class SimilarRecipe(BaseModel):
    recipe: RecipeCard
    score: float
    ingredient_overlap: float
    shared: list[str]
    reason: str


@router.get("/{recipe_id}/similar", response_model=list[SimilarRecipe])
def similar(recipe_id: int, request: Request, k: int = Query(6, ge=1, le=20)):
    _load(recipe_id)
    eng = services.get_engine()
    prefs = prefs_for_search(current_user_id(request), True)
    keep = None
    if prefs.apply_profile:
        from ..nlp.query import ParsedQuery

        keep = eng.active.copy()
        for _, m in services.ranker._hard_constraints(ParsedQuery("", "", ""), prefs, []):
            keep &= m
    out = []
    for s in similar_recipes(eng, recipe_id, k=k, keep_mask=keep):
        card = recipe_card(s["recipe_id"])
        if card:
            out.append(SimilarRecipe(recipe=card, score=s["score"], ingredient_overlap=s["ingredient_overlap"],
                                     shared=s["shared"], reason=s["reason"]))
    return out


@router.get("/{recipe_id}/compare/{other_id}")
def compare_recipes(recipe_id: int, other_id: int):
    a, b = _load(recipe_id), _load(other_id)
    data = compare(services.get_engine(), recipe_id, other_id)
    return {"first": {"id": a["id"], "title": a["title"]}, "second": {"id": b["id"], "title": b["title"]}, **data}


class DuplicateCheckIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    ingredients: list[str] = Field(..., min_length=1, max_length=100)
    exclude_id: int | None = None


@router.post("/check-duplicates")
def check_duplicates(body: DuplicateCheckIn):
    eng = services.get_engine()
    f = eng.fx.compute({"id": -1, "title": body.title, "ingredients": body.ingredients, "instructions": ""})
    from ..nlp.retrieval import embedding_doc

    doc = embedding_doc({"title": body.title, "ingredients": body.ingredients}, f.ingredients)
    return {"duplicates": find_duplicates(eng, body.title, f.essential, doc, exclude_id=body.exclude_id)}
