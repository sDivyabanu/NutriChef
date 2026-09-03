# NutriChef — NLP-Powered Smart Recipe Recommendation System

NutriChef is an intelligent recipe recommendation system that uses **Natural Language Processing (NLP)** to understand user-provided ingredients and recommend the most relevant recipes.

Unlike traditional recipe search systems that rely on exact keyword matching, NutriChef understands **ingredient variations, synonyms, spelling differences, and semantic similarity** to provide smarter and more practical recipe recommendations.

Users can provide ingredients through **text, voice, or image input**, and NutriChef processes the extracted ingredients, ranks suitable recipes, identifies missing ingredients, and provides nutritional information.

---

## Problem Statement

Traditional recipe recommendation systems often depend on exact ingredient matching.

For example:

* `capsicum` may not match `bell pepper`
* `curd` may not match `yogurt`
* `tomatoes` may not match `tomato`
* Minor spelling mistakes may prevent relevant recipes from appearing
* Users may provide only a partial list of ingredients

NutriChef solves these problems using an NLP-based pipeline that **normalizes, understands, compares, and semantically matches ingredients** instead of relying only on exact keywords.

---

## Key Features

* 📝 **Text-Based Ingredient Input**
* 🎙️ **Voice-Based Ingredient Input**
* 📷 **Image-Based Ingredient Input**
* 🧠 **NLP-Based Ingredient Extraction**
* 🔤 **Ingredient Normalization & Lemmatization**
* 🔄 **Synonym-Aware Ingredient Matching**
* 🔎 **Fuzzy Ingredient Matching**
* 📊 **TF-IDF Recipe Representation**
* 📐 **Cosine Similarity-Based Ranking**
* 🤖 **Semantic Recipe Matching**
* 📈 **Recipe Match Percentage**
* ➕ **Missing Ingredient Detection**
* 🍎 **Nutritional Information**
* 🥘 **Personalized Recipe Recommendations**

---

## NLP Pipeline

NutriChef follows a multi-stage NLP pipeline to transform raw ingredient input into meaningful recipe recommendations.

```text
User Input
   │
   ▼
Ingredient Extraction
   │
   ▼
Text Preprocessing
   │
   ├── Lowercasing
   ├── Tokenization
   ├── Noise Removal
   └── Lemmatization
   │
   ▼
Ingredient Normalization
   │
   ├── Synonym Mapping
   └── Quantity / Unit Removal
   │
   ▼
Fuzzy Matching
   │
   ▼
Recipe Vectorization
   │
   ├── TF-IDF
   └── Sentence Embeddings
   │
   ▼
Cosine Similarity
   │
   ▼
Recipe Ranking
   │
   ▼
Missing Ingredient Detection
   │
   ▼
Nutrition Summarization
   │
   ▼
Recommended Recipes
```

---

##  NLP Techniques Used

### 1. Text Preprocessing

Raw ingredient input is cleaned before matching.

The preprocessing pipeline includes:

* Lowercasing
* Tokenization
* Noise removal
* Removing quantities and measurement units
* Lemmatization
* Ingredient normalization

For example:

```text
Input:
"2 Tomatoes, 1 Onion and some Capsicum"

Normalized:
["tomato", "onion", "bell pepper"]
```

---

### 2. Synonym Normalization

Different regions may use different words for the same ingredient.

NutriChef maps these variations into a standardized representation.

```text
capsicum  → bell pepper
curd      → yogurt
tomatoes  → tomato
onions    → onion
```

This improves recipe matching even when the user's terminology differs from the recipe dataset.

---

### 3. Fuzzy Matching

Ingredient names may contain spelling mistakes or slight variations.

NutriChef uses **fuzzy string matching** based on edit-distance techniques such as **Levenshtein Distance**.

RapidFuzz can be used to efficiently calculate similarity between ingredient strings.

Example:

```text
User Input:
"tomto"

Possible Match:
"tomato"
```

---

### 4. TF-IDF Vectorization

Recipes and ingredient lists are converted into numerical vectors using **TF-IDF (Term Frequency–Inverse Document Frequency)**.

TF-IDF helps identify ingredients that are particularly meaningful for distinguishing one recipe from another.

---

### 5. Cosine Similarity

After vectorization, **Cosine Similarity** measures how closely the user's ingredients match each recipe.

```text
Similarity Score
      ↓
Recipe Ranking
      ↓
Most Relevant Recipes
```

Recipes with higher similarity scores are ranked above less relevant recipes.

---

### 6. Semantic Matching

NutriChef can further improve recommendations using **sentence embeddings**.

Unlike traditional keyword matching, embeddings capture the semantic meaning of ingredient and recipe descriptions.

This allows the system to identify recipes that are conceptually relevant even when the exact words are different.

---

## Recipe Ranking

Recipes can be ranked using multiple factors:

* Ingredient match percentage
* TF-IDF / semantic similarity
* Number of missing ingredients
* Fuzzy matching score
* Nutritional information

Example:

```text
 Paneer Tikka

Match: 92%

Matched Ingredients:
✓ Paneer
✓ Yogurt
✓ Onion
✓ Bell Pepper

Missing Ingredients:
• Garam Masala
• Lemon

Nutrition:
Calories: 320 kcal
Protein: 22 g
Carbohydrates: 18 g
Fat: 17 g
```

---

##  Nutrition Analysis

NutriChef also summarizes nutritional information for recommended recipes.

The recipe dataset can contain information such as:

| Nutrient      |  Example |
| ------------- | -------: |
| Calories      | 320 kcal |
| Protein       |     22 g |
| Carbohydrates |     18 g |
| Fat           |     17 g |

This allows users to evaluate recipes not only based on available ingredients but also on nutritional value.

---

## Dataset

The recipe dataset contains information required for both NLP-based matching and recipe presentation.

Important fields include:

```text
Recipe Name
Ingredients
Instructions
Cuisine / Category
Preparation Time
Calories
Protein
Carbohydrates
Fat
```

Before being used by the recommendation engine, ingredient data is cleaned and normalized.

Example:

```text
Raw:
2 large tomatoes

Processed:
tomato
```

---

##  Tech Stack

### Frontend

* **Next.js**
* TypeScript

### Backend

* **FastAPI**
* Python

### NLP

* **spaCy**
* TF-IDF
* Cosine Similarity
* RapidFuzz / Levenshtein Distance
* Sentence Embeddings

### Database

* **MongoDB**

---

##  System Architecture

```text
                    ┌─────────────────────┐
                    │       User          │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Next.js Frontend  │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
          Text Input        Voice Input       Image Input
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  FastAPI Backend    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    NLP Pipeline     │
                    │                    │
                    │ • Preprocessing    │
                    │ • Lemmatization    │
                    │ • Synonym Mapping  │
                    │ • Fuzzy Matching   │
                    │ • TF-IDF           │
                    │ • Embeddings       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Recipe Ranking      │
                    │ Cosine Similarity   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │      MongoDB        │
                    │   Recipe Dataset    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Recommended Recipes │
                    │ + Nutrition Info    │
                    └─────────────────────┘
```

---


## 🔄 Recommendation Workflow

```text
1. User provides ingredients
          ↓
2. Ingredients are extracted
          ↓
3. Text is cleaned and normalized
          ↓
4. Ingredient synonyms are resolved
          ↓
5. Fuzzy matching handles spelling variations
          ↓
6. User ingredients are compared with recipes
          ↓
7. Similarity scores are calculated
          ↓
8. Recipes are ranked
          ↓
9. Missing ingredients are identified
          ↓
10. Nutrition information is summarized
          ↓
11. Best matching recipes are recommended
```

---

## 🧪 Example

### Input

```text
paneer, curd, onion, capsicum, tomato
```

### NLP Normalization

```text
paneer
yogurt
onion
bell pepper
tomato
```

### Output

```text
1. Paneer Tikka
   Match: 92%

2. Kadai Paneer
   Match: 85%

3. Paneer Masala
   Match: 78%
```

Each recommendation can include:

* Recipe name
* Match percentage
* Matched ingredients
* Missing ingredients
* Cooking instructions
* Preparation time
* Nutritional information

---


## Future Enhancements

NutriChef can be extended with:

* Personalized recommendations based on user preferences
* Dietary preference filtering
* Cuisine-based recommendations
* Allergy-aware ingredient filtering
* Calorie-based recipe filtering
* Advanced transformer-based semantic search
* Multilingual ingredient understanding
* User recipe history and favourites
* Improved image-based ingredient recognition
* Conversational recipe assistance

---

##  Why NutriChef?

Traditional recipe applications answer:

> **"Which recipes contain these exact words?"**

NutriChef aims to answer:

> **"What can I realistically cook with the ingredients I have?"**

By combining **NLP preprocessing, synonym normalization, fuzzy matching, TF-IDF, semantic similarity, and intelligent recipe ranking**, NutriChef provides a more flexible and practical approach to recipe discovery.

---

##  Author

**Divyabanu S**

Integrated M.Tech — Software Engineering
Vellore Institute of Technology, Chennai

---

## License

This project is developed for **academic and educational purposes**.
