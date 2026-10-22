"""Conversions between internal NLP dataclasses and API schemas."""
from __future__ import annotations

import json
import time

from . import db, services
from .nlp.query import IngredientRef, NutritionConstraint, ParsedQuery
from .nlp.ranker import Prefs
from .schemas_nlp import (ConstraintCheck, IngredientConstraint, NutritionFilter, QueryUnderstanding, RecipeCard,
                          SearchHit)


def understanding_from_parsed(pq: ParsedQuery) -> QueryUnderstanding:
    return QueryUnderstanding(
        original=pq.original, corrected=pq.corrected, corrections=pq.corrections, language=pq.language,
        intent=pq.intent,
        ingredients=[IngredientConstraint(name=r.name, display=r.display, role=r.role, quantity=r.quantity,
                                          unit=r.unit, quantity_text=r.quantity_text) for r in pq.ingredients],
        excluded_groups=pq.excluded_groups, diets=pq.diets, cuisines=pq.cuisines, meal_types=pq.meal_types,
        max_time_min=pq.max_time_min,
        nutrition=[NutritionFilter(nutrient=n.nutrient, op=n.op, value=n.value, text=n.text) for n in pq.nutrition],
        qualities=pq.qualities, servings=pq.servings, similar_to=pq.similar_to, free_text=pq.free_text,
        notes=pq.notes, conflicts=pq.conflicts, clarification=pq.clarification,
    )


def parsed_from_understanding(u: QueryUnderstanding) -> ParsedQuery:
    lex = services.get_engine().lex
    ingredients = []
    for i in u.ingredients:
        name = i.name if (i.name in lex or i.name.startswith("group:")) else (lex.lookup(i.name) or lex.lookup(i.display))
        if name:
            ingredients.append(IngredientRef(name=name, display=i.display or name, role=i.role, quantity=i.quantity,
                                             unit=i.unit, quantity_text=i.quantity_text))
    nutrition = [NutritionConstraint(n.nutrient, n.op, n.value, n.text or f"{n.nutrient} {n.op} {n.value:g}") for n in u.nutrition]
    free = u.free_text
    if not free:
        free = " ".join([i.name for i in ingredients if i.role not in ("excluded", "unavailable")] + u.cuisines + u.meal_types + u.qualities)
    return ParsedQuery(
        original=u.original, normalized=u.corrected or u.original, corrected=u.corrected or u.original,
        corrections=list(u.corrections), language=u.language, intent=u.intent, ingredients=ingredients,
        excluded_groups=list(u.excluded_groups), diets=list(u.diets), cuisines=list(u.cuisines),
        meal_types=list(u.meal_types), max_time_min=u.max_time_min, nutrition=nutrition, qualities=list(u.qualities),
        servings=u.servings, similar_to=u.similar_to, free_text=free, notes=[], conflicts=list(u.conflicts),
        clarification=None,
    )


def recipe_card(rid: int, rec: dict | None = None) -> RecipeCard | None:
    eng = services.get_engine()
    rec = rec or db.get_recipe(rid)
    if not rec:
        return None
    f = eng.feature(rid) or eng.fx.compute(rec)
    return RecipeCard(
        id=rid, title=rec["title"], source=rec["source"], ingredient_count=len(rec["ingredients"]),
        ingredients_preview=[p["name"] for p in f.parsed if p.get("name")][:8],
        derived=services.derived_info(f), has_nutrition=bool(rec.get("nutrition")),
    )


def hits_to_schema(hits) -> list[SearchHit]:
    recs = db.get_recipes([h.recipe_id for h in hits])
    out = []
    for h in hits:
        card = recipe_card(h.recipe_id, recs.get(h.recipe_id))
        if card is None:
            continue
        out.append(SearchHit(recipe=card, score=h.score, score_breakdown=h.breakdown, used_ingredients=h.used,
                             missing_ingredients=h.missing, pantry_match_pct=h.pantry_match_pct,
                             explanation=h.explanation, warnings=h.warnings,
                             checks=[ConstraintCheck(**c) for c in h.checks]))
    return out


# ------------------------------------------------------------------ preferences
DEFAULT_PREFS = {
    "diet": None, "vegetarian_includes_eggs": False, "allergies": [], "disliked_ingredients": [],
    "liked_ingredients": [], "liked_cuisines": [], "staples": [], "apply_profile": True,
}


def load_prefs(user_id: str | None) -> dict:
    if not user_id:
        return dict(DEFAULT_PREFS)
    row = db.get_conn().execute("SELECT prefs FROM user_prefs WHERE user_id = ?", (user_id,)).fetchone()
    data = dict(DEFAULT_PREFS)
    if row:
        data.update(json.loads(row[0]))
    return data


def save_prefs(user_id: str, prefs: dict) -> None:
    with db.tx() as conn:
        conn.execute(
            "INSERT INTO user_prefs(user_id, prefs, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET prefs = excluded.prefs, updated_at = excluded.updated_at",
            (user_id, json.dumps(prefs), time.time()),
        )


def prefs_for_search(user_id: str | None, apply_profile: bool) -> Prefs:
    p = load_prefs(user_id)
    favs = []
    if user_id:
        favs = [r[0] for r in db.get_conn().execute(
            "SELECT DISTINCT recipe_id FROM interactions WHERE user_id = ? AND kind = 'favorite'", (user_id,))]
    return Prefs(
        vegetarian_includes_eggs=bool(p.get("vegetarian_includes_eggs")), diet=p.get("diet"),
        allergies=list(p.get("allergies") or []), disliked_ingredients=_canon(p.get("disliked_ingredients")),
        liked_ingredients=_canon(p.get("liked_ingredients")), liked_cuisines=[c.lower() for c in p.get("liked_cuisines") or []],
        staples=_canon(p.get("staples")), favorite_ids=favs,
        apply_profile=bool(apply_profile and user_id and p.get("apply_profile", True)),
    )


def _canon(items) -> list[str]:
    lex = services.get_engine().lex
    out = []
    for it in items or []:
        name = lex.lookup(str(it))
        if name:
            out.append(name)
    return out
