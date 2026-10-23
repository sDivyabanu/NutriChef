# NutriChef NLP evaluation — split: dev

Recipes indexed: 13475 · run at 2026-10-22 21:45

## Ingredient extraction

| System | Precision | Recall | F1 |
|---|---|---|---|
| NutriChef (name + role) | 0.98 | 1.0 | 0.99 |
| NutriChef (name only) | 0.98 | 1.0 | 0.99 |
| Original app normaliser (name only) | 0.357 | 0.357 | 0.357 |
| spaCy en_core_web_sm NER (name only) | 0.042 | 0.01 | 0.016 |

Quantity+unit accuracy: 1.0 (n=16); items: 45

## Query understanding

Intent accuracy: **1.0** (n=35)

| Field | Accuracy | n |
|---|---|---|
| diets | 1.0 | 12 |
| meal_types | 1.0 | 15 |
| max_time_min | 1.0 | 5 |
| qualities | 1.0 | 10 |
| excluded_groups | 1.0 | 3 |
| nutrition | 1.0 | 3 |
| cuisines | 1.0 | 5 |
| similar_to | 1.0 | 2 |
| servings | 1.0 | 1 |
| tamil_english_detection | 1.0 | 2 |
| clarification_detection | 1.0 | 1 |
| conflict_detection | 1.0 | 1 |

## Normalisation

Synonym → canonical accuracy: **1.0** (n=30) — regional 1.0 (n=13), british 1.0 (n=8), plural 1.0 (n=3), tamil 1.0 (n=4), spelling 1.0 (n=1), identity 1.0 (n=1)

Typo correction: 0.95 (n=20); correct words left unchanged: 1.0 (n=10)

## Retrieval (top-10, 15 queries, embeddings: sentence-transformers/all-MiniLM-L6-v2)

| System | P@5 | P@10 | MRR | nDCG@10 | Constraint violations@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|
| keyword | 0.28 | 0.22 | 0.4 | 0.254 | 0.429 | 10.8 | 14.0 |
| tfidf | 0.44 | 0.393 | 0.576 | 0.424 | 0.771 | 10.0 | 13.7 |
| embedding | 0.347 | 0.293 | 0.432 | 0.314 | 0.829 | 11.8 | 14.3 |
| hybrid | 0.853 | 0.807 | 0.9 | 0.817 | 0.086 | 38.3 | 49.7 |

Constraint violations: share of returned top-10 recipes containing an excluded ingredient (queries with exclusions only).
