# NutriChef NLP evaluation — split: test

Recipes indexed: 13475 · run at 2026-10-22 21:46

## Ingredient extraction

| System | Precision | Recall | F1 |
|---|---|---|---|
| NutriChef (name + role) | 0.894 | 0.916 | 0.905 |
| NutriChef (name only) | 0.929 | 0.952 | 0.94 |
| Original app normaliser (name only) | 0.435 | 0.446 | 0.44 |
| spaCy en_core_web_sm NER (name only) | 0.105 | 0.024 | 0.039 |

Quantity+unit accuracy: 1.0 (n=12); items: 35

## Query understanding

Intent accuracy: **0.967** (n=30)

| Field | Accuracy | n |
|---|---|---|
| diets | 1.0 | 9 |
| meal_types | 1.0 | 14 |
| max_time_min | 1.0 | 3 |
| qualities | 1.0 | 6 |
| cuisines | 1.0 | 4 |
| nutrition | 0.667 | 3 |
| servings | 1.0 | 1 |
| similar_to | 1.0 | 1 |
| excluded_groups | 1.0 | 1 |
| tamil_english_detection | 1.0 | 2 |
| clarification_detection | 1.0 | 1 |

## Normalisation

Synonym → canonical accuracy: **0.912** (n=34) — regional 1.0 (n=10), identity 1.0 (n=3), tamil 0.889 (n=9), british 0.778 (n=9), plural 1.0 (n=1), paraphrase 1.0 (n=1), spelling 1.0 (n=1)

Typo correction: 1.0 (n=20); correct words left unchanged: 1.0 (n=10)

## Retrieval (top-10, 15 queries, embeddings: sentence-transformers/all-MiniLM-L6-v2)

| System | P@5 | P@10 | MRR | nDCG@10 | Constraint violations@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|
| keyword | 0.413 | 0.373 | 0.533 | 0.4 | 0.5 | 7.9 | 12.5 |
| tfidf | 0.547 | 0.44 | 0.629 | 0.478 | 0.517 | 10.9 | 12.5 |
| embedding | 0.48 | 0.407 | 0.565 | 0.426 | 0.667 | 10.3 | 11.9 |
| hybrid | 0.827 | 0.8 | 0.917 | 0.819 | 0.167 | 32.4 | 40.1 |

Constraint violations: share of returned top-10 recipes containing an excluded ingredient (queries with exclusions only).
