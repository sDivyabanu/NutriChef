# NutriChef — local NLP recipe search, understanding and adaptation

NutriChef is a recipe platform (Next.js + PostgreSQL) with a **fully local** NLP service (FastAPI + Python). You can describe what you want in plain English or Tamil-English, for example *"I have tomatoes, rice and onions"* or *"South Indian recipes without peanuts"*. NutriChef extracts ingredients, exclusions, diets, cuisines, time limits and nutrition limits, enforces the hard constraints, and ranks real recipes with explanations.

**No external AI or inference APIs are used.** All NLP runs on your machine. After the one-time model download, the app works offline.

---

## 1. What is implemented

| Area | Implemented |
|---|---|
| Natural-language search | Intent detection, ingredient extraction with roles (have / must include / prefer / exclude / don't have), diets, cuisines, meal types, time limits, numeric nutrition limits, qualities (spicy, quick, filling, high-protein, low-oil…), "similar to …", servings, clarification and conflict detection |
| Ingredient extraction | Quantities (fractions, unicode ½, ranges, "half an", "a dozen"), units, preparation notes, optional lines, "X or Y" alternatives, equipment lines, typo correction, singular/plural, regional/British/Indian/Tamil synonyms, negation scope (including Tamil postpositions such as *"onion illama"*) |
| Retrieval | TF-IDF (1–2-grams), sentence embeddings (all-MiniLM-L6-v2, cached), original keyword baseline, and **hybrid ranking** with hard filters, pantry coverage, missing-ingredient penalties, preferences and explanations |
| Dietary / allergy filtering | Vegetarian (no eggs by default, matching the app's profile options), eggetarian, vegan, pescatarian, Jain, gluten-, dairy-, nut-, egg-free, plus allergen groups. Checks run on every ingredient line using a curated lexicon with an is-a hierarchy; "may contain" items are excluded when you say you're allergic |
| Nutrition | Numeric filters apply only to recipes with real nutrition data (user-entered). The source dataset has **none**, so those results are marked **"not verified"**. Nothing is estimated or invented |
| Recipe pages | Parsed ingredients, labelled estimates (time from steps, cuisine, difficulty, spice), allergens, similar recipes, comparison, favourites, ratings |
| Recipe CRUD | Create, edit, delete (soft delete with version history), "save a copy" of dataset recipes, ownership checks. New and edited recipes are indexed incrementally |
| Paste-a-recipe parsing | Extracts title, ingredients, quantities, steps, time and servings from unstructured text for review. Fills only empty fields |
| Recipe modification | "make this vegan", "replace paneer with tofu", "less spicy", "remove mushrooms", "make it for 2 people", "alternative without cream", "quicker", "lighter". Uses a curated substitution knowledge base, scaling, a step rewrite, diet re-validation and an original-vs-modified diff. Saves as new, or replaces your own recipe after confirmation |
| Recipe generation | Default: **retrieve-and-adapt** (best matching recipe + rule-based modification + constraint checks), clearly labelled. Optional: a local LLM via llama.cpp with JSON-schema-constrained output, Pydantic validation, constraint checks and one repair round |
| Conversational assistant | Structured state (not LLM memory). Keeps constraints across turns ("only paneer", "under 20 minutes"), removes filters ("remove the time limit", "eggs are fine"), answers questions about shown recipes from the database ("how long does the first one take?", "is it vegan?"), and resets |
| Personalisation | Preferences (diet, allergies, liked/disliked ingredients, cuisines, pantry staples), favourites, ratings, recently viewed, explainable content-based recommendations. Hard filters always apply first |
| Other | Autocomplete, search feedback, saved searches, meal planning with variety rules and a shopping list, duplicate detection on save, photo detection (optional; YOLOv8n/COCO, which knows only 5 ingredient foods) |

**Not implemented:** voice input, nutrition estimation, image-based recipe recognition beyond the 5 COCO foods.

---

## 2. Architecture

```
Browser ──► Next.js (localhost:3000)
              ├─ auth, profile, pantry, favourites, tracking ──► PostgreSQL (local, embedded, :5433)
              └─ /backend/*  (same-origin proxy, carries login cookie)
                    ▼
            FastAPI NLP service (127.0.0.1:8000)
              ├─ recipes store (SQLite: backend/data/recipes.db, built from data/13k-recipes.csv)
              ├─ NLP engine (loaded once at startup)
              │    lexicon → extraction → spelling → query parser → features
              │    retrievers: keyword | TF-IDF | MiniLM embeddings → hybrid ranker
              ├─ modify / generate (adapt or llama.cpp) / chat / meal plan / similarity
              └─ optional: llama-server on 127.0.0.1 (random port), YOLOv8n
```

Backend modules (`backend/app/nlp/`): `text.py` (normalisation), `lexicon.py` + `data/ingredients.txt` (~440 canonical ingredients, ~4.3k surface forms), `ingredients.py` (extraction), `spelling.py`, `vocab.py`, `query.py` (query understanding), `features.py` (recipe-side features), `retrieval.py`, `ranker.py`, `engine.py` (index and incremental updates), `similarity.py`, `modify.py` + `data/substitutions.json`, `generate.py`, `llm.py`, `chat.py`, `mealplan.py`, `recipe_parser.py`, `suggest.py`.

**Match percentage.** "Pantry match" is the share of a recipe's *essential* ingredients that you have. Essential means non-optional and not a staple (salt, pepper, water and cooking oils, plus any staples you add in Preferences). It is not a similarity score.

---

## 3. Data

- `data/13k-recipes.csv` (from the original repo; Epicurious-derived Kaggle dataset *"Food Ingredients and Recipe Dataset with Images"*, CC BY-SA 3.0): 13,501 rows.
- `python -m scripts.build_corpus` imports it reproducibly. It skips 12 rows with no ingredients and 14 exact duplicates, leaving **13,475 recipes**. The CSV itself is never modified, and the quality report is written to `backend/data/corpus_report.json`.
- The source has **no** nutrition, servings, cooking time, cuisine, meal type, diet labels or images. NutriChef shows *estimates* (time = sum of durations stated in the steps; cuisine/meal/difficulty/spice inferred from text), always labelled as such, and never invents nutrition.
- Indian, and especially South Indian, recipes are rare in this dataset (8 paneer recipes, 39 recipes inferred as South Indian), so those queries return few results.

---

## 4. Models

| Purpose | Model | Licence | Status |
|---|---|---|---|
| Semantic retrieval (used) | `sentence-transformers/all-MiniLM-L6-v2` | Apache-2.0 | default; recipe vectors cached in `backend/data/cache/` |
| Other embedding candidates (downloaded, not benchmarked) | `BAAI/bge-small-en-v1.5`, `intfloat/e5-small-v2`, `intfloat/multilingual-e5-small` | MIT | switch with `NUTRICHEF_EMBEDDING_MODEL` |
| Tokenisation baseline | spaCy `en_core_web_sm` 3.8 | MIT | used only as the NER baseline in the evaluation |
| Optional generation | Qwen3-4B-Instruct-2507 Q4_K_M (also downloaded: Qwen3-1.7B, Llama-3.2-3B) via llama.cpp b11819 | Apache-2.0 / Llama 3.2 licence | off by default |
| Optional photo detection | YOLOv8n (COCO), from the original repo | AGPL-3.0 (ultralytics) | shown only if `ultralytics` is installed |

Measured llama.cpp speed on this machine (Ryzen 7 7840U, 15 GB RAM, Radeon 780M iGPU), using `llama-bench`:

| Model | Backend | Prompt tok/s | Generation tok/s |
|---|---|---|---|
| Qwen3-4B-Instruct Q4_K_M | CPU, 8 threads | 107 | 6.5 |
| Qwen3-4B-Instruct Q4_K_M | Vulkan (iGPU) | 257 | 10.9 |
| Qwen3-1.7B Q4_K_M | Vulkan (iGPU) | 677 | 23.2 |

The full LLM quality benchmark (`eval/bench_llm.py`) was written but not completed, so no LLM adherence numbers are claimed.

---

## 5. Evaluation (actual measured results)

Run with `cd backend && .venv/Scripts/python -m eval.run_eval --split test`. The held-out run is saved in `backend/eval/results/eval_test_heldout.md`; the dev run is in `eval_dev.md`.

**About the labels.** The labels in `backend/eval/data/*.jsonl` were written by the developer (an AI assistant) from the raw text, before running the system on the test split. They are **not human-verified**. Dev and test are separate; the parser was tuned on dev only.

Retrieval relevance is **objective**: a recipe is relevant if its raw title and ingredient text contain every required term group and none of the excluded terms. The term lists live in `retrieval.jsonl` and are independent of NutriChef's lexicon. This measures constraint-aware matching, not taste.

### Held-out test split

**Ingredient extraction** (35 queries; precision/recall over gold ingredients)

| System | Precision | Recall | F1 |
|---|---|---|---|
| NutriChef (name + role) | 0.894 | 0.916 | **0.905** |
| NutriChef (name only) | 0.929 | 0.952 | 0.940 |
| Original app's `normalizeIngredient` (name only) | 0.435 | 0.446 | 0.440 |
| spaCy `en_core_web_sm` NER (name only) | 0.105 | 0.024 | 0.039 |

Quantity + unit accuracy: 1.0 (12 quantities). General-purpose NER doesn't recognise food ingredients, so the curated domain recogniser is justified.

**Query understanding** (30 queries): intent accuracy 0.967. Field accuracy: diets 1.0 (9), meal type 1.0 (14), cuisine 1.0 (4), time limit 1.0 (3), qualities 1.0 (6), nutrition 0.667 (3), Tamil-English detection 1.0 (2).

**Normalisation:** synonym → canonical 0.912 (34; Tamil 0.889, British 0.778). Typo correction 1.0 (20 misspellings). Correctly spelled domain words left unchanged 1.0 (10).

**Retrieval** (15 queries, top-10; MiniLM embeddings)

| System | P@5 | P@10 | MRR | nDCG@10 | Constraint violations@10 | p50 latency |
|---|---|---|---|---|---|---|
| Original keyword (substring) | 0.413 | 0.373 | 0.533 | 0.400 | 0.500 | 8 ms |
| TF-IDF | 0.547 | 0.440 | 0.629 | 0.478 | 0.517 | 11 ms |
| Embeddings (MiniLM) | 0.480 | 0.407 | 0.565 | 0.426 | 0.667 | 10 ms |
| **Hybrid (NutriChef)** | **0.827** | **0.800** | **0.917** | **0.819** | **0.167** | 32 ms |

"Constraint violations" is the share of returned top-10 recipes containing an explicitly excluded ingredient, measured by raw-text matching, which is stricter than the lexicon. Examples: "peanut butter" counts as *butter* for a dairy-free query, and words like "port" count as wine. The remaining hybrid violations come from those strict text rules and from lexicon gaps. Pure semantic search ignores "without X" and often ranks X recipes highest.

**Known test failures** (kept as measured):
- "chick peas" read as "peas"
- "no more than 250 calories" parsed as ≥
- "coriander" not mapped to cilantro after "no"
- "juice of 1 lemon" split into juice + lemon
- "invent a … taco" not recognised as generation
- missing synonyms *swede*, *mangetout*, *kara mani*

The first two and the two British synonyms were fixed **after** the held-out run, so the numbers above don't include those fixes.

**Tests:** `backend/tests` holds 21 pytest unit and API tests, all passing, plus `scripts/smoke-crud.mjs`, a 22-check end-to-end auth/CRUD/proxy test that passes.

---

## 6. Windows setup (Git Bash)

Prerequisites: Node 22+, Python 3.12 (or `uv`), Git Bash. The commands below were run on this machine.

```bash
# 1) Frontend dependencies + local PostgreSQL (first time)
cd ~/wdev/Projects/NutriChef
npm install
cp .env.example .env.local && cp .env.example .env     # then set JWT_SECRET to a long random string in both
```

```bash
# 2) Backend environment (first time)
cd ~/wdev/Projects/NutriChef/backend
python -m venv .venv                                  # or: python -m uv venv --python 3.12 .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m spacy download en_core_web_sm
cp .env.example .env                                  # JWT_SECRET must match the frontend's
.venv/Scripts/python -m scripts.build_corpus          # builds backend/data/recipes.db
.venv/Scripts/python -m scripts.download_models --embeddings sentence-transformers/all-MiniLM-L6-v2
```

### Start (three terminals)

```bash
cd ~/wdev/Projects/NutriChef && npm run db
```

```bash
cd ~/wdev/Projects/NutriChef && npm run db:migrate && npm run dev
```

```bash
cd ~/wdev/Projects/NutriChef/backend && .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Frontend: http://localhost:3000
- API: http://localhost:8000 · Docs: http://localhost:8000/docs · Health: http://localhost:8000/api/nlp/health
- Demo account (local only): set `NUTRICHEF_DEMO_PASSWORD` to a password of your choice, then run `node scripts/seed-demo-user.mjs`. The email defaults to `demo@nutrichef.test` and can be changed with `NUTRICHEF_DEMO_EMAIL`. No reusable demo password is stored in source.

The first backend start encodes the recipe embeddings (~90 s) and computes features (~25 s); later starts load the caches (~40 s). CRUD and health respond immediately while the engine loads in the background. Everything binds to localhost only.

### Optional

- **Local LLM generation:** `python -m scripts.download_models --llm qwen3-4b`, put llama.cpp's Windows build in `models/llama.cpp/vulkan-x64/` (or `cpu-x64/`), set `NUTRICHEF_LLM_BACKEND=vulkan`, then tick "Use the local language model" on the Generate page.
- **Photo detection:** `pip install ultralytics`.

### Tests and evaluation

```bash
cd ~/wdev/Projects/NutriChef/backend && .venv/Scripts/python -m pytest -q tests
```

```bash
cd ~/wdev/Projects/NutriChef/backend && .venv/Scripts/python -m eval.run_eval --split test
```

```bash
cd ~/wdev/Projects/NutriChef && node scripts/smoke-crud.mjs
```

---

## 7. Main API endpoints

`POST /api/nlp/search` · `POST /api/nlp/understand` · `POST /api/nlp/extract-ingredients` · `GET /api/nlp/suggest` · `POST /api/nlp/parse-recipe` · `POST /api/nlp/modify` · `POST /api/nlp/generate` + `GET /api/nlp/jobs/{id}` · `POST /api/nlp/chat` · `POST /api/nlp/meal-plan` · `POST /api/nlp/feedback` · `GET|POST|PUT|DELETE /api/recipes…` · `GET /api/recipes/{id}/similar` · `GET /api/recipes/{a}/compare/{b}` · `POST /api/recipes/check-duplicates` · `GET|PUT /api/me/preferences` · `GET /api/me/recommendations` · `POST /api/interactions` · `GET /api/nlp/health`

Full schemas are at http://localhost:8000/docs.

## 8. Changes to the original app

- **Removed:**
  - OpenAI image calls (`/api/detect` now proxies the local detector)
  - random nutrition and random diet labels
  - the TheMealDB seeding route
  - the Supabase REST client (favourites/pantry now use the same Postgres connection)
- **Security fixes:**
  - The SQL column injection in `PUT /api/profile` is closed (whitelisted fields).
  - Identity now comes from the verified JWT, not a client-set `userId` cookie.
  - The hardcoded JWT fallback secret is gone.
  - Uploaded images are no longer written to disk under client-supplied names.
- **Database:** the Prisma schema drift (`auth_users`, `Profile.user_id`) is fixed with additive migrations, and `UserRecipe.recipe_ref` links favourites to recipes.
- **Missing route:** `/api/logout` was referenced but missing; it is now added.

## 9. Limitations

- Evaluation labels are AI-authored and the sets are small (35–45 items per split), so the numbers have wide uncertainty.
- Recipe relevance is judged by objective term criteria, not by human taste judgements.
- The lexicon (~440 entries) misses long-tail items; about 1.7% of corpus ingredient lines are unrecognised, and those are flagged as "uncertain" in diet checks.
- Estimated times only add up durations stated in the steps, so prep time is excluded.
- Cuisine inference covers about 30% of recipes, and the dataset is US-centric.
- Allergy and diet results are NLP checks of ingredient text, **not** a guarantee of safety.
- The rule-based modifier and adapt-based generation produce suggestions that need cooking judgement. Substitutions are not universally interchangeable.
- Tamil support is transliterated Tamil-English (Tanglish) plus a few Tamil-script ingredient names. It is not general Tamil understanding.
