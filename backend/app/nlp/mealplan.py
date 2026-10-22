"""Natural-language meal planning built on the hybrid ranker (same constraints, preferences and explanations)."""
from __future__ import annotations

import copy
import re
from collections import Counter

from .engine import NLPEngine
from .query import ParsedQuery
from .ranker import Prefs, Ranker
from .text import normalize

DAY_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "a": 1}
DAYS_RE = re.compile(r"\b(?P<n>\d+|one|two|three|four|five|six|seven)[- ]?days?\b|\b(?P<week>week|weekly|7-day)\b|\b(?P<wd>weekdays|work ?week)\b")


COUNT_RE = re.compile(r"\b(?P<n>\d+|one|two|three|four|five|six|seven)\s+(?:[a-z-]+\s+){0,4}?(?:dinners|lunches|breakfasts|meals|dishes)\b")


def plan_days(text: str) -> int:
    t = normalize(text)
    c = COUNT_RE.search(t)
    if c and not DAYS_RE.search(t):
        n = c.group("n")
        return max(1, min(7, int(n) if n.isdigit() else DAY_WORDS.get(n, 3)))
    m = DAYS_RE.search(t)
    if not m:
        return 3
    if m.group("week"):
        return 7
    if m.group("wd"):
        return 5
    n = m.group("n")
    return max(1, min(7, int(n) if n.isdigit() else DAY_WORDS.get(n, 3)))


def build_plan(engine: NLPEngine, ranker: Ranker, text: str, prefs: Prefs) -> dict:
    pq = engine.parser.parse(text)
    days = plan_days(text)
    meals = [m for m in pq.meal_types if m in ("breakfast", "lunch", "dinner")] or ["dinner"]
    used_ids: set[int] = set()
    cuisine_count: Counter = Counter()
    main_count: Counter = Counter()
    dish_count: Counter = Counter()
    plan = []
    for d in range(days):
        day = {"day": d + 1, "meals": []}
        for meal in meals:
            q = copy.deepcopy(pq)
            q.meal_types = [meal]
            q.intent = "search"
            if not q.free_text.strip():
                q.free_text = meal
            out = ranker.search(q, prefs, k=40)
            pick, why = None, ""
            for h in out.hits:
                if h.recipe_id in used_ids:
                    continue
                f = engine.feature(h.recipe_id)
                main = next((n for n in f.essential if engine.lex.get(n) and engine.lex.get(n).category in
                             ("meat", "poultry", "fish", "shellfish", "plant_protein", "legume", "dairy")), None)
                # variety: avoid repeating a cuisine or main protein too often
                if f.cuisine and cuisine_count[f.cuisine] >= max(2, days // 2):
                    continue
                if main and main_count[main] >= 2:
                    continue
                dish = normalize(h.title).split()[-1] if h.title else ""
                if dish and dish_count[dish] >= 1 and dish not in ("salad", "rice", "bowl"):
                    continue
                pick, why = h, "; ".join(h.explanation[:1])
                cuisine_count[f.cuisine] += 1 if f.cuisine else 0
                if main:
                    main_count[main] += 1
                dish_count[dish] += 1
                break
            if pick is None and out.hits:
                pick = next((h for h in out.hits if h.recipe_id not in used_ids), None)
                why = "repeated cuisine/protein (not enough variety in matching recipes)"
            if pick:
                used_ids.add(pick.recipe_id)
                day["meals"].append({"meal": meal, "recipe_id": pick.recipe_id, "title": pick.title, "why": why,
                                     "checks": pick.checks, "warnings": pick.warnings})
            else:
                day["meals"].append({"meal": meal, "recipe_id": None, "title": None, "why": "no recipe satisfies all constraints",
                                     "checks": [], "warnings": []})
        plan.append(day)
    have = set(pq.names("available"))
    shopping: Counter = Counter()
    for day in plan:
        for m in day["meals"]:
            if m["recipe_id"]:
                for n in engine.feature(m["recipe_id"]).essential:
                    if not engine.lex.satisfies(have, n, allow_broad=True):
                        shopping[n] += 1
    by_cat: dict[str, list[dict]] = {}
    for n, cnt in sorted(shopping.items()):
        cat = engine.lex.get(n).category if engine.lex.get(n) else "other"
        by_cat.setdefault(cat, []).append({"name": n, "recipes": cnt})
    return {"days": days, "meals_per_day": meals, "plan": plan, "shopping_list": by_cat,
            "constraints": {"diets": pq.diets, "excluded": [r.display for r in pq.ingredients if r.role == "excluded"] + pq.excluded_groups,
                            "max_time_min": pq.max_time_min, "cuisines": pq.cuisines, "qualities": pq.qualities},
            "note": "Quantities aren't summed because many recipes don't state servings; nutrition totals aren't shown because the dataset has no nutrition data."}
