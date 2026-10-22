"""NLP engine: owns the recipe index (features, inverted ingredient index, TF-IDF, embeddings).

Built once at startup; recipe create/update/delete events update it incrementally.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .. import db
from ..config import settings
from .features import FEATURE_VERSION, FeatureExtractor, RecipeFeatures, text_hash
from .lexicon import Lexicon, get_lexicon
from .query import QueryParser
from .retrieval import EmbeddingRetriever, KeywordRetriever, TfidfRetriever, embedding_doc, tfidf_doc
from .spelling import SpellCorrector
from .text import normalize
from .vocab import CUISINE_PHRASES, DIET_PHRASES, MEAL_PHRASES, QUALITY_PHRASES, QUERY_WORDS, TANGLISH_WORDS

log = logging.getLogger(__name__)


class NLPEngine:
    def __init__(self, embedding_model: str | None = None, cache_dir: Path | None = None, enable_embeddings: bool = True):
        self.lex: Lexicon = get_lexicon()
        self.fx = FeatureExtractor(self.lex)
        self.cache_dir = cache_dir or settings.data_dir / "cache"
        self.embedding_model = embedding_model or settings.embedding_model
        self.enable_embeddings = enable_embeddings
        self.lock = threading.RLock()
        self.ids: list[int] = []
        self.pos_of: dict[int, int] = {}
        self.features: list[RecipeFeatures | None] = []
        self.titles: list[str] = []
        self.sources: list[str] = []
        self.active: np.ndarray = np.zeros(0, dtype=bool)
        self.index: dict[str, set[int]] = defaultdict(set)
        self.keyword = KeywordRetriever()
        self.tfidf = TfidfRetriever()
        self.embed: EmbeddingRetriever | None = None
        self.parser: QueryParser | None = None
        self.status: dict[str, str] = {}
        self.timings: dict[str, float] = {}

    # ------------------------------------------------------------------ build
    def build(self) -> None:
        t0 = time.perf_counter()
        recipes = list(db.iter_all_recipes())
        feats = self._load_or_compute_features(recipes)
        self.timings["features_s"] = round(time.perf_counter() - t0, 2)
        with self.lock:
            self.ids = [r["id"] for r in recipes]
            self.pos_of = {rid: i for i, rid in enumerate(self.ids)}
            self.features = [feats[r["id"]] for r in recipes]
            self.titles = [r["title"] for r in recipes]
            self.sources = [r["source"] for r in recipes]
            self.owners = [r.get("owner_id") for r in recipes]
            self.nutrition = [r.get("nutrition") for r in recipes]
            self.active = np.ones(len(self.ids), dtype=bool)
            self.index = defaultdict(set)
            for i, f in enumerate(self.features):
                self._index_features(i, f)
            self._build_arrays()
        self.status["features"] = f"ok ({len(self.ids)} recipes, v{FEATURE_VERSION})"

        t = time.perf_counter()
        self.keyword.fit(recipes)
        self.tfidf.fit({r["id"]: tfidf_doc(r, feats[r["id"]].ingredients) for r in recipes})
        self.timings["tfidf_s"] = round(time.perf_counter() - t, 2)
        self.status["tfidf"] = "ok"

        t = time.perf_counter()
        self._build_speller(recipes)
        self.parser = QueryParser(self.speller, self.lex)
        self.timings["speller_s"] = round(time.perf_counter() - t, 2)
        self.status["query_parser"] = "ok"

        if self.enable_embeddings:
            try:
                t = time.perf_counter()
                self.embed = EmbeddingRetriever(self.embedding_model, self.cache_dir)
                self.embed.fit({r["id"]: embedding_doc(r, feats[r["id"]].ingredients) for r in recipes})
                self.timings["embeddings_s"] = round(time.perf_counter() - t, 2)
                self.status["embeddings"] = f"ok ({self.embedding_model})"
            except Exception as exc:  # model not downloaded -> lexical-only search still works
                log.warning("embeddings unavailable: %s", exc)
                self.embed = None
                self.status["embeddings"] = f"unavailable: {type(exc).__name__} (run scripts/download_models.py)"
        else:
            self.status["embeddings"] = "disabled"
        self.timings["build_total_s"] = round(time.perf_counter() - t0, 2)
        log.info("NLP engine ready: %s %s", self.status, self.timings)

    def _load_or_compute_features(self, recipes: list[dict]) -> dict[int, RecipeFeatures]:
        path = self.cache_dir / f"features_v{FEATURE_VERSION}.jsonl"
        cached: dict[int, dict] = {}
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    d = json.loads(line)
                    cached[d["recipe_id"]] = d
        out: dict[int, RecipeFeatures] = {}
        recomputed = 0
        for r in recipes:
            d = cached.get(r["id"])
            if d and d["text_hash"] == text_hash(r):
                out[r["id"]] = RecipeFeatures(**d)
            else:
                out[r["id"]] = self.fx.compute(r)
                recomputed += 1
        if recomputed or not path.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                for f in out.values():
                    fh.write(json.dumps(f.to_json(), ensure_ascii=False) + "\n")
            tmp.replace(path)
        log.info("features: %d cached, %d computed", len(recipes) - recomputed, recomputed)
        return out

    def _index_features(self, i: int, f: RecipeFeatures) -> None:
        for n in f.ingredients:
            e = self.lex.get(n)
            for a in (e.ancestors if e else (n,)):
                self.index[a].add(i)
            if e:
                for g in e.allergens:
                    self.index[f"allergen:{g}"].add(i)
                for g in e.maybe_allergens:
                    self.index[f"maybe:{g}"].add(i)
                if e.animal:
                    self.index[f"animal:{e.animal}"].add(i)
                if "nonveg" in e.tags:
                    self.index["animal:other"].add(i)
        for n in f.essential:
            e = self.lex.get(n)
            for a in (e.ancestors if e else (n,)):
                self.index[f"essential:{a}"].add(i)

    def _build_arrays(self) -> None:
        n = len(self.features)
        self.diet_arr = {k: np.array([bool(f and f.diet.get(k)) for f in self.features]) for k in
                         ("vegetarian", "eggetarian", "vegan", "pescatarian", "gluten_free", "dairy_free", "egg_free", "nut_free")}
        self.time_arr = np.array([f.est_time_min if f and f.est_time_min is not None else np.nan for f in self.features], dtype=np.float32)
        self.n_essential = np.array([len(f.essential) if f else 0 for f in self.features], dtype=np.float32)
        self.meal_sets = [set(f.meal_types) if f else set() for f in self.features]
        self.spice_arr = np.array([{"mild": 0, "medium": 1, "hot": 2}[f.spice_level] if f else 0 for f in self.features])
        assert len(self.time_arr) == n

    def _build_speller(self, recipes: list[dict]) -> None:
        counts: Counter = Counter()
        for r in recipes:
            counts.update(re.findall(r"[a-z]+", normalize(r["title"] + " " + " ".join(r["ingredients"]) + " " + (r["instructions"] or ""))))
        domain: set[str] = set()
        for s in self.lex.all_surface_forms():
            domain.update(s.split())
        for table in (DIET_PHRASES, CUISINE_PHRASES, MEAL_PHRASES, QUALITY_PHRASES):
            for k in table:
                domain.update(k.replace("-", " ").split())
        from .vocab import AVAILABLE_CUES, EXCLUDE_CUES, PREFER_CUES, REQUIRE_CUES, TAMIL_POST_EXCLUDE

        protected = QUERY_WORDS | TANGLISH_WORDS | EXCLUDE_CUES | AVAILABLE_CUES | REQUIRE_CUES | PREFER_CUES | TAMIL_POST_EXCLUDE
        self.word_counts = counts
        self.speller = SpellCorrector(counts, domain, protected)

    # ------------------------------------------------------------------ incremental updates
    def on_recipe_change(self, rid: int, action: str) -> None:
        rec = db.get_recipe(rid) if action != "delete" else None
        with self.lock:
            if action == "delete" or rec is None:
                i = self.pos_of.get(rid)
                if i is not None:
                    self.active[i] = False
                    self.tfidf.remove(rid)
                    self.keyword.remove(rid)
                    if self.embed:
                        self.embed.remove(rid)
                return
            f = self.fx.compute(rec)
            if rid in self.pos_of:
                i = self.pos_of[rid]
                for key in list(self.index):
                    self.index[key].discard(i)
                self.features[i] = f
                self.titles[i] = rec["title"]
                self.nutrition[i] = rec.get("nutrition")
                self.active[i] = True
            else:
                i = len(self.ids)
                self.ids.append(rid)
                self.pos_of[rid] = i
                self.features.append(f)
                self.titles.append(rec["title"])
                self.sources.append(rec["source"])
                self.owners.append(rec.get("owner_id"))
                self.nutrition.append(rec.get("nutrition"))
                self.active = np.append(self.active, True)
            self._index_features(i, f)
            self._build_arrays()
            self.keyword.upsert(rid, rec)
            self.tfidf.upsert(rid, tfidf_doc(rec, f.ingredients))
            if self.embed:
                self.embed.upsert(rid, embedding_doc(rec, f.ingredients))

    # ------------------------------------------------------------------ helpers used by ranker/features API
    def contains(self, name: str) -> set[int]:
        return self.index.get(name, set())

    def feature(self, rid: int) -> RecipeFeatures | None:
        i = self.pos_of.get(rid)
        return self.features[i] if i is not None else None

    def embedding_scores(self, text: str) -> np.ndarray:
        if not self.embed or not text.strip():
            return np.zeros(len(self.ids), dtype=np.float32)
        s = self.embed.scores(text)
        return self._align(s, self.embed.ids)

    def embedding_scores_vec(self, vec: np.ndarray) -> np.ndarray:
        return self._align(self.embed.matrix @ vec, self.embed.ids)

    def tfidf_scores(self, text: str) -> np.ndarray:
        return self._align(self.tfidf.scores(text), self.tfidf.ids)

    def _align(self, scores: np.ndarray, ids: np.ndarray) -> np.ndarray:
        if len(ids) == len(self.ids) and (len(ids) == 0 or (ids[0] == self.ids[0] and ids[-1] == self.ids[-1])):
            return scores
        out = np.zeros(len(self.ids), dtype=np.float32)
        for j, rid in enumerate(ids):
            i = self.pos_of.get(int(rid))
            if i is not None:
                out[i] = scores[j]
        return out
