"""Unit tests for the NLP components (no server needed)."""
import pytest

from app.nlp.features import FeatureExtractor
from app.nlp.ingredients import IngredientExtractor
from app.nlp.lexicon import get_lexicon
from app.nlp.modify import RecipeModifier, scale_line
from app.nlp.query import QueryParser

LEX = get_lexicon()
X = IngredientExtractor(LEX)
P = QueryParser(None, LEX)
FX = FeatureExtractor(LEX)


def roles(text):
    return {(r.name, r.role) for r in P.parse(text).ingredients}


def test_spec_example_quantities():
    q = P.parse("I have 2 tomatoes, half an onion, 100g paneer and some capsicum.")
    got = {r.name: (r.quantity, r.unit, r.role) for r in q.ingredients}
    assert got["tomato"] == (2, None, "available")
    assert got["onion"] == (0.5, None, "available")
    assert got["paneer"] == (100, "g", "available")
    assert got["bell pepper"][2] == "available" and got["bell pepper"][0] is None


@pytest.mark.parametrize("line,name,qty,unit", [
    ("1 1/2 cups basmati rice", "basmati rice", 1.5, "cup"),
    ("¼ cup extra-virgin olive oil", "olive oil", 0.25, "cup"),
    ("a pinch of hing", "asafoetida", 1, "pinch"),
    ("2–3 green chillies, slit", "chili pepper", 2.5, None),
])
def test_recipe_line_parsing(line, name, qty, unit):
    ing = X.parse_line(line).ingredients[0]
    assert (ing["name"], ing["quantity"], ing["unit"]) == (name, qty, unit)


def test_optional_and_equipment_lines():
    assert X.parse_line("Lemon wedges (for serving)").optional
    assert not X.parse_line("2 Tbsp. olive oil, plus more for drizzling").optional
    assert X.parse_line("A 9-inch springform pan").kind == "equipment"


def test_negation_and_lists():
    assert roles("no peanuts or cashews please") == {("peanut", "excluded"), ("cashew", "excluded")}
    r = roles("spicy soup with lentils, no onion and no garlic")
    assert ("lentil", "required") in r and ("onion", "excluded") in r and ("garlic", "excluded") in r
    assert ("egg", "unavailable") in roles("I don't have eggs, chocolate cake")


def test_tamil_english():
    q = P.parse("Kathirikai vechu enna cook pannalam?")
    assert q.language == "ta-en" and ("eggplant", "available") in {(r.name, r.role) for r in q.ingredients}
    assert ("onion", "excluded") in roles("onion illama tomato rice")


def test_constraints():
    q = P.parse("Suggest a spicy vegetarian dinner under 30 minutes.")
    assert q.diets == ["vegetarian"] and q.meal_types == ["dinner"] and q.max_time_min == 30 and "spicy" in q.qualities
    q = P.parse("Find a high-protein breakfast under 350 calories.")
    assert [(n.nutrient, n.op, n.value) for n in q.nutrition] == [("calories", "<=", 350)]
    q = P.parse("Give me South Indian recipes without peanuts.")
    assert q.cuisines == ["south indian"] and "peanut" in q.excluded_groups
    assert P.parse("Find something similar to fried rice but with more vegetables.").similar_to == "fried rice"


def test_free_text_drops_exclusions():
    q = P.parse("chocolate dessert without peanuts")
    assert "peanut" not in q.free_text


def test_diet_inference():
    f = FX.compute({"id": 0, "title": "Test", "ingredients": ["1 cup chicken broth", "1 cup rice"], "instructions": ""})
    assert not f.diet["vegetarian"]
    f = FX.compute({"id": 0, "title": "Test", "ingredients": ["200 g paneer", "1 onion"], "instructions": ""})
    assert f.diet["vegetarian"] and not f.diet["vegan"] and "dairy" in f.allergens


def test_satisfies_hierarchy():
    assert LEX.satisfies({"cherry tomato"}, "tomato")
    assert LEX.satisfies({"rice"}, "basmati rice")
    assert not LEX.satisfies({"cheese"}, "paneer")


def test_modify_vegan_and_scale():
    M = RecipeModifier(LEX, P, FX)
    rec = {"title": "Paneer Masala", "servings": 4, "ingredients": ["250 g paneer", "2 tbsp butter", "1 onion"],
           "instructions": "Fry the onion in butter. Add paneer."}
    r = M.modify(rec, "make this vegan")
    assert all(v["passed"] for v in r.validation)
    r = M.modify(rec, "make it for 2 people")
    assert r.ingredients[0].startswith("125 g") and r.servings == 2
    assert scale_line("1 1/2 cups rice", 2)[0] == "3 cups rice"
