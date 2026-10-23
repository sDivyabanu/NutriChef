"""API integration tests (builds the real engine from local caches; no network)."""
import jwt
import pytest
from fastapi.testclient import TestClient

from app import services
from app.config import settings
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert services._ready.wait(300), "engine did not load"
        assert services.engine is not None
        yield c


def auth_cookie(uid="00000000-0000-0000-0000-00000000abcd"):
    return {"token": jwt.encode({"id": uid, "email": "t@test"}, settings.jwt_secret or "x", algorithm="HS256")}


def test_health(client):
    r = client.get("/api/nlp/health").json()
    assert r["components"]["nlp_engine"] == "ok" and r["recipes"] > 10000


def test_search_respects_exclusions(client):
    r = client.post("/api/nlp/search", json={"query": "chocolate dessert without nuts", "k": 10}).json()
    assert r["results"]
    for h in r["results"]:
        assert "tree_nut" not in h["recipe"]["derived"]["allergens"] and "peanut" not in h["recipe"]["derived"]["allergens"]


def test_search_vegetarian_and_time(client):
    r = client.post("/api/nlp/search", json={"query": "spicy vegetarian dinner under 30 minutes", "k": 10}).json()
    for h in r["results"]:
        d = h["recipe"]["derived"]
        assert d["diet"]["vegetarian"] and d["estimated_time_min"] <= 30


def test_pantry_mode_explanations(client):
    r = client.post("/api/nlp/search", json={"query": "I have tomatoes, rice and onions", "k": 5}).json()
    assert r["understanding"]["intent"] == "find_by_ingredients"
    assert all(h["pantry_match_pct"] is not None and h["used_ingredients"] for h in r["results"])


def test_nutrition_unknown_is_flagged(client):
    r = client.post("/api/nlp/search", json={"query": "breakfast under 350 calories", "k": 3}).json()
    assert any("not verified" in c["detail"] for h in r["results"] for c in h["checks"])


def test_chat_keeps_context(client):
    s = None
    for msg in ["Find a high-protein vegetarian dinner.", "Only paneer recipes.", "Under 20 minutes."]:
        r = client.post("/api/nlp/chat", json={"message": msg, "state": s}).json()
        s = r["state"]
    u = s["understanding"]
    assert u["diets"] == ["vegetarian"] and u["meal_types"] == ["dinner"] and u["max_time_min"] == 20
    assert {"name": "paneer", "role": "required"}.items() <= next(i for i in u["ingredients"] if i["name"] == "paneer").items()


def test_recipe_crud_and_index(client):
    c = auth_cookie()
    r = client.post("/api/recipes", cookies=c, json={"title": "Zzqx Test Kathirikai Fry", "ingredients": ["2 brinjals", "1 tsp chili powder"], "instructions": "Fry."})
    assert r.status_code == 201
    rid = r.json()["id"]
    hits = client.post("/api/nlp/search", json={"query": "zzqx kathirikai fry", "k": 5}).json()["results"]
    assert any(h["recipe"]["id"] == rid for h in hits), "new recipe should be searchable immediately"
    assert client.put(f"/api/recipes/{rid}", cookies=c, json={"title": "Zzqx Test 2"}).json()["version"] == 2
    assert client.put("/api/recipes/1", cookies=c, json={"title": "x"}).status_code == 403
    assert client.delete(f"/api/recipes/{rid}", cookies=c).status_code == 204
    assert client.get(f"/api/recipes/{rid}").status_code == 404


def test_modify_and_generate_fallback(client):
    r = client.post("/api/nlp/modify", json={"recipe_id": 603, "instruction": "make this vegan"}).json()
    assert r["understood"] and all(v["passed"] for v in r["validation"])
    job = client.post("/api/nlp/generate", json={"request": "vegan dal for 3 people", "use_llm": False}).json()
    import time
    for _ in range(60):
        j = client.get(f"/api/nlp/jobs/{job['id']}").json()
        if j["status"] in ("done", "error"):
            break
        time.sleep(1)
    assert j["status"] == "done" and j["result"]["method"] == "retrieve-and-adapt"
