"""Typed request/response contracts for the NutriChef API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------- recipes


class Nutrition(BaseModel):
    """Per-serving values. Every field is optional: unknown is None, never 0."""

    model_config = ConfigDict(extra="forbid")
    calories: float | None = Field(None, ge=0, le=10000)
    protein_g: float | None = Field(None, ge=0, le=1000)
    carbs_g: float | None = Field(None, ge=0, le=2000)
    fat_g: float | None = Field(None, ge=0, le=1000)
    fiber_g: float | None = Field(None, ge=0, le=500)


class RecipeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=1, max_length=200)
    ingredients: list[str] = Field(..., min_length=1, max_length=100)
    instructions: str = Field("", max_length=20000)
    cuisine: str | None = Field(None, max_length=60)
    meal_type: str | None = Field(None, max_length=60)
    total_time_min: int | None = Field(None, ge=1, le=7 * 24 * 60)
    servings: float | None = Field(None, gt=0, le=100)
    nutrition: Nutrition | None = None
    diet_tags: list[str] = Field(default_factory=list, max_length=20)
    generated: bool = Field(False, description="True when the recipe came from the local generator (kept as a label)")

    @field_validator("ingredients")
    @classmethod
    def _strip_lines(cls, v: list[str]) -> list[str]:
        lines = [s.strip()[:300] for s in v if s and s.strip()]
        if not lines:
            raise ValueError("at least one ingredient line is required")
        return lines


class RecipeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(None, min_length=1, max_length=200)
    ingredients: list[str] | None = Field(None, min_length=1, max_length=100)
    instructions: str | None = Field(None, max_length=20000)
    cuisine: str | None = None
    meal_type: str | None = None
    total_time_min: int | None = Field(None, ge=1, le=7 * 24 * 60)
    servings: float | None = Field(None, gt=0, le=100)
    nutrition: Nutrition | None = None
    diet_tags: list[str] | None = None


class ParsedIngredient(BaseModel):
    raw: str
    name: str | None                 # canonical ingredient name (None if not recognised)
    display: str | None = None       # name as phrased by the user / recipe
    quantity: float | None = None
    quantity_text: str | None = None
    unit: str | None = None
    preparation: str | None = None
    optional: bool = False
    category: str | None = None
    is_staple: bool = False          # salt, water, oil… (not counted as "missing")
    confidence: float = 1.0
    matched_by: str | None = None    # exact | synonym | lemma | fuzzy | tamil | substring


class DerivedInfo(BaseModel):
    """Values inferred by NutriChef's NLP — always labelled as derived, never as source data."""

    diet: dict[str, bool]                    # vegetarian / vegan / ... from explicit ingredient checks
    diet_uncertain: list[str] = []           # ingredients that could not be classified
    allergens: list[str] = []                # allergen groups detected in ingredient lines
    cuisine_guess: str | None = None
    meal_type_guess: list[str] = []
    estimated_time_min: int | None = None    # sum of durations stated in the instructions
    time_basis: str | None = None
    difficulty: str | None = None
    spice_level: str | None = None


class Recipe(BaseModel):
    id: int
    source: str
    title: str
    ingredients: list[str]
    instructions: str
    cuisine: str | None = None
    meal_type: str | None = None
    total_time_min: int | None = None
    servings: float | None = None
    nutrition: Nutrition | None = None
    nutrition_source: str | None = None
    diet_tags: list[str] = []
    owner_id: str | None = None
    created_at: float
    updated_at: float
    version: int = 1
    parsed_ingredients: list[ParsedIngredient] | None = None
    derived: DerivedInfo | None = None


class RecipePage(BaseModel):
    items: list[Recipe]
    total: int
    offset: int
    limit: int


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    recipes: int
    components: dict[str, str]
    offline: bool
