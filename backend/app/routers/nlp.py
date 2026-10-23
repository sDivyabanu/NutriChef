"""NLP endpoints: query understanding, search, ingredient extraction, autocomplete."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .. import services
from ..auth import current_user_id
from ..convert import hits_to_schema, parsed_from_understanding, prefs_for_search, understanding_from_parsed
from ..schemas import ParsedIngredient
from ..schemas_nlp import ExtractRequest, ExtractResponse, IngredientConstraint, QueryUnderstanding, SearchRequest, SearchResponse

router = APIRouter(prefix="/api/nlp", tags=["nlp"])
log = logging.getLogger("nutrichef.search")


def _engine():
    try:
        eng = services.get_engine()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    if eng is None:
        raise HTTPException(503, f"NLP engine unavailable: {services.components.get('nlp_engine')}")
    return eng


@router.post("/understand", response_model=QueryUnderstanding)
def understand(body: ExtractRequest):
    """Parse a query into intent, ingredients (with roles) and constraints without searching."""
    eng = _engine()
    return understanding_from_parsed(eng.parser.parse(body.text))


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, request: Request):
    eng = _engine()
    if body.understanding is not None:
        pq = parsed_from_understanding(body.understanding)
    elif body.query and body.query.strip():
        pq = eng.parser.parse(body.query)
    else:
        raise HTTPException(422, "Provide a query or an understanding object")
    user_id = current_user_id(request)
    prefs = prefs_for_search(user_id, body.apply_profile)
    understanding = understanding_from_parsed(pq)
    suggestions = []
    if pq.corrections:
        suggestions.append("Searched for: " + pq.corrected)
    if pq.conflicts:
        # Conflicting explicit constraints are reported, never silently resolved.
        return SearchResponse(understanding=understanding, results=[], total=0, excluded_counts={},
                              notes=[*pq.notes, *pq.conflicts], relaxations=[], suggestions=suggestions,
                              add_ingredient_suggestions=[], mode=body.mode, timing_ms={})
    outcome = services.ranker.search(pq, prefs, k=body.k, offset=body.offset, mode=body.mode)
    notes = list(outcome.notes)
    if prefs.apply_profile and (prefs.allergies or prefs.diet):
        bits = []
        if prefs.diet:
            bits.append(f"diet: {prefs.diet}")
        if prefs.allergies:
            bits.append(f"allergies: {', '.join(prefs.allergies)}")
        notes.append("Your profile was applied (" + "; ".join(bits) + "). Turn it off with 'apply profile' to search without it.")
    log.info("search intent=%s total=%d ms=%s q=%r", pq.intent, outcome.total, outcome.timing_ms.get("total_ms"), (body.query or "")[:80])
    return SearchResponse(
        understanding=understanding, results=hits_to_schema(outcome.hits), total=outcome.total,
        excluded_counts=outcome.excluded, notes=notes, relaxations=outcome.relaxations, suggestions=suggestions,
        add_ingredient_suggestions=outcome.add_ingredient_suggestions, mode=outcome.mode, timing_ms=outcome.timing_ms,
    )


@router.post("/extract-ingredients", response_model=ExtractResponse)
def extract_ingredients(body: ExtractRequest):
    """Ingredient extraction with quantities/units, normalisation, typo correction and negation."""
    eng = _engine()
    pq = eng.parser.parse(body.text)
    lines = []
    if "\n" in body.text:
        for line in body.text.splitlines():
            if line.strip():
                lines.extend(ParsedIngredient(**p) for p in eng.fx.extractor.parse_line(line).ingredients)
    return ExtractResponse(
        corrected=pq.corrected, corrections=pq.corrections, language=pq.language,
        ingredients=[IngredientConstraint(name=r.name, display=r.display, role=r.role, quantity=r.quantity,
                                          unit=r.unit, quantity_text=r.quantity_text) for r in pq.ingredients],
        excluded_groups=pq.excluded_groups, parsed_lines=lines,
    )


@router.get("/suggest", response_model=list[str])
def suggest(q: str = Query(..., min_length=1, max_length=100), limit: int = Query(8, ge=1, le=20)):
    """Autocomplete: ingredient names, recipe titles and query templates (typo-tolerant prefix match)."""
    eng = _engine()
    from ..nlp.suggest import autocomplete

    return autocomplete(eng, q, limit)


class ParseRecipeIn(BaseModel):
    text: str = Field(..., min_length=10, max_length=20000)


class ParseRecipeOut(BaseModel):
    title: str | None
    ingredients: list[str]
    instructions: list[str]
    total_time_min: int | None
    time_source: str | None
    servings: int | None
    notes: list[str]
    parsed_ingredients: list[ParsedIngredient]
    cuisine_guess: str | None
    meal_type_guess: list[str]
    diet: dict[str, bool]
    allergens: list[str]
    confidence: dict[str, float]
    warnings: list[str]


@router.post("/parse-recipe", response_model=ParseRecipeOut)
def parse_recipe(body: ParseRecipeIn):
    """Extract title, ingredients (with quantities), steps, time, servings from pasted text — for review, not auto-saved."""
    eng = _engine()
    from ..nlp.recipe_parser import RecipeTextParser

    pr = RecipeTextParser(eng.fx).parse(body.text)
    f = eng.fx.compute({"id": -1, "title": pr.title or "", "ingredients": pr.ingredients or [""],
                        "instructions": "\n".join(pr.instructions)})
    return ParseRecipeOut(
        title=pr.title, ingredients=pr.ingredients, instructions=pr.instructions, total_time_min=pr.total_time_min,
        time_source=pr.time_source, servings=pr.servings, notes=pr.notes,
        parsed_ingredients=[ParsedIngredient(**p) for p in f.parsed], cuisine_guess=f.cuisine,
        meal_type_guess=f.meal_types, diet=f.diet, allergens=f.allergens, confidence=pr.confidence, warnings=pr.warnings,
    )


class InlineRecipe(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    ingredients: list[str] = Field(..., min_length=1, max_length=100)
    instructions: str = Field("", max_length=20000)
    servings: float | None = Field(None, gt=0, le=100)


class ModifyIn(BaseModel):
    instruction: str = Field(..., min_length=2, max_length=500)
    recipe_id: int | None = None
    recipe: InlineRecipe | None = None
    original_servings: float | None = Field(None, gt=0, le=100)


class LineChangeOut(BaseModel):
    before: str | None
    after: str | None
    status: str
    note: str | None = None
    alternatives: list[str] = []


class ModifyOut(BaseModel):
    understood: list[str]
    title: str
    ingredients: list[str]
    instructions: str
    servings: float | None
    line_changes: list[LineChangeOut]
    step_changes: list[dict]
    validation: list[dict]
    suggestions: list[str]
    warnings: list[str]
    clarification: str | None
    method: str = "rule-based substitutions (curated knowledge base)"


@router.post("/modify", response_model=ModifyOut)
def modify(body: ModifyIn):
    """Modify a recipe from a natural-language instruction. Returns a proposal; nothing is saved."""
    eng = _engine()
    from .. import db
    from ..nlp.modify import RecipeModifier

    if body.recipe_id is not None:
        rec = db.get_recipe(body.recipe_id)
        if not rec:
            raise HTTPException(404, "Recipe not found")
    elif body.recipe is not None:
        rec = body.recipe.model_dump()
    else:
        raise HTTPException(422, "Provide recipe_id or recipe")
    r = RecipeModifier(eng.lex, eng.parser, eng.fx).modify(rec, body.instruction, body.original_servings)
    return ModifyOut(understood=r.understood, title=r.title, ingredients=r.ingredients, instructions=r.instructions,
                     servings=r.servings, line_changes=[LineChangeOut(**vars(c)) for c in r.line_changes],
                     step_changes=r.step_changes, validation=r.validation, suggestions=r.suggestions,
                     warnings=r.warnings, clarification=r.clarification)


class MealPlanIn(BaseModel):
    request: str = Field(..., min_length=3, max_length=500)
    apply_profile: bool = True


@router.post("/meal-plan")
def meal_plan(body: MealPlanIn, request: Request):
    """Plan N days of meals from a natural-language request, reusing search constraints, preferences and variety rules."""
    eng = _engine()
    from ..nlp.mealplan import build_plan

    prefs = prefs_for_search(current_user_id(request), body.apply_profile)
    return build_plan(eng, services.ranker, body.request, prefs)
