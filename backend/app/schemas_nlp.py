"""Typed contracts for the NLP endpoints."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .schemas import DerivedInfo, ParsedIngredient

Role = Literal["available", "required", "preferred", "excluded", "unavailable"]


class IngredientConstraint(BaseModel):
    name: str
    display: str
    role: Role
    quantity: float | None = None
    unit: str | None = None
    quantity_text: str | None = None


class NutritionFilter(BaseModel):
    nutrient: Literal["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]
    op: Literal["<=", ">="]
    value: float = Field(..., ge=0)
    text: str = ""


class QueryUnderstanding(BaseModel):
    """Structured interpretation of a query. Clients may edit it and send it back (e.g. to remove a filter)."""

    model_config = ConfigDict(extra="ignore")
    original: str = ""
    corrected: str = ""
    corrections: list[tuple[str, str]] = []
    language: str = "en"
    intent: str = "search"
    ingredients: list[IngredientConstraint] = []
    excluded_groups: list[str] = []
    diets: list[str] = []
    cuisines: list[str] = []
    meal_types: list[str] = []
    max_time_min: int | None = Field(None, ge=1, le=10000)
    nutrition: list[NutritionFilter] = []
    qualities: list[str] = []
    servings: int | None = None
    similar_to: str | None = None
    free_text: str = ""
    notes: list[str] = []
    conflicts: list[str] = []
    clarification: str | None = None


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str | None = Field(None, max_length=500)
    understanding: QueryUnderstanding | None = None
    k: int = Field(12, ge=1, le=50)
    offset: int = Field(0, ge=0, le=1000)
    mode: Literal["hybrid", "tfidf", "embedding", "keyword"] = "hybrid"
    apply_profile: bool = True


class ConstraintCheck(BaseModel):
    constraint: str
    status: Literal["pass", "estimated", "unknown"]
    detail: str


class RecipeCard(BaseModel):
    id: int
    title: str
    source: str
    ingredient_count: int
    ingredients_preview: list[str]
    derived: DerivedInfo
    has_nutrition: bool


class SearchHit(BaseModel):
    recipe: RecipeCard
    score: float
    score_breakdown: dict[str, float]
    used_ingredients: list[str]
    missing_ingredients: list[str]
    pantry_match_pct: int | None = Field(
        None, description="Share of the recipe's essential ingredients (excluding staples and optional items) you have."
    )
    explanation: list[str]
    warnings: list[str]
    checks: list[ConstraintCheck]


class Relaxation(BaseModel):
    key: str
    label: str
    results: int


class SearchResponse(BaseModel):
    understanding: QueryUnderstanding
    results: list[SearchHit]
    total: int
    excluded_counts: dict[str, int]
    notes: list[str]
    relaxations: list[Relaxation]
    suggestions: list[str]
    add_ingredient_suggestions: list[str]
    mode: str
    timing_ms: dict[str, float]


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class ExtractResponse(BaseModel):
    corrected: str
    corrections: list[tuple[str, str]]
    language: str
    ingredients: list[IngredientConstraint]
    excluded_groups: list[str]
    parsed_lines: list[ParsedIngredient] = []
