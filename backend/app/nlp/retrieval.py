"""Retrievers. Each returns a score for every indexed recipe so the ranker can combine them.

A  KeywordRetriever  - port of the original NutriChef /api/recipes substring search (baseline)
B  TfidfRetriever    - TF-IDF (word 1-2 grams, sublinear tf) + cosine similarity
C  EmbeddingRetriever- sentence embeddings (local sentence-transformers model) + cosine similarity
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .text import STOPWORDS, normalize

log = logging.getLogger(__name__)


def light_stem(word: str) -> str:
    """Tiny suffix normaliser (tomatoes->tomato, berries->berry, baked->bake) used by the TF-IDF analyser."""
    if len(word) <= 3:
        return word
    for suf, rep in (("ies", "y"), ("oes", "o"), ("ches", "ch"), ("shes", "sh"), ("sses", "ss"), ("ves", "f")):
        if word.endswith(suf) and len(word) > len(suf) + 2:
            return word[: -len(suf)] + rep
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


_WORD_RE = re.compile(r"[a-z]+")


def analyse(text: str) -> list[str]:
    toks = [light_stem(w) for w in _WORD_RE.findall(normalize(text)) if w not in STOPWORDS and len(w) > 1]
    return toks + [f"{a} {b}" for a, b in zip(toks, toks[1:])]


class KeywordRetriever:
    """Baseline A: every query term must appear as a substring of the recipe's ingredient text; dataset order."""

    def __init__(self) -> None:
        self.ids: list[int] = []
        self.texts: list[str] = []

    def fit(self, recipes: list[dict]) -> None:
        self.ids = [r["id"] for r in recipes]
        self.texts = [normalize(" ".join(r["ingredients"])) for r in recipes]

    def upsert(self, rid: int, rec: dict) -> None:
        text = normalize(" ".join(rec["ingredients"]))
        if rid in self.ids:
            self.texts[self.ids.index(rid)] = text
        else:
            self.ids.append(rid)
            self.texts.append(text)

    def remove(self, rid: int) -> None:
        if rid in self.ids:
            self.texts[self.ids.index(rid)] = ""

    def search(self, terms: list[str], k: int = 20) -> list[int]:
        terms = [t.lower().strip() for t in terms if t.strip()]
        if not terms:
            return []
        out = []
        for rid, text in zip(self.ids, self.texts):
            if all(t in text for t in terms):
                out.append(rid)
                if len(out) >= k:
                    break
        return out


def tfidf_doc(rec: dict, canonical: list[str]) -> str:
    title = rec["title"]
    return " ".join([title, title, title, " ".join(canonical), " ".join(canonical), " ".join(rec["ingredients"]),
                     (rec.get("instructions") or "")[:1500]])


class TfidfRetriever:
    def __init__(self) -> None:
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.ids: np.ndarray = np.array([], dtype=np.int64)
        self.row_of: dict[int, int] = {}

    def fit(self, docs: dict[int, str]) -> None:
        self.ids = np.array(list(docs), dtype=np.int64)
        self.row_of = {int(r): i for i, r in enumerate(self.ids)}
        self.vectorizer = TfidfVectorizer(analyzer=analyse, sublinear_tf=True, min_df=2, max_df=0.6, dtype=np.float32)
        self.matrix = self.vectorizer.fit_transform([docs[int(r)] for r in self.ids])

    def scores(self, query: str) -> np.ndarray:
        if self.vectorizer is None or not query.strip():
            return np.zeros(len(self.ids), dtype=np.float32)
        qv = self.vectorizer.transform([query])
        return (self.matrix @ qv.T).toarray().ravel().astype(np.float32)

    def upsert(self, rid: int, doc: str) -> None:
        """Incremental update: new/edited recipes are vectorised with the existing vocabulary."""
        from scipy.sparse import vstack

        vec = self.vectorizer.transform([doc])
        if rid in self.row_of:
            m = self.matrix.tolil()
            m[self.row_of[rid]] = vec
            self.matrix = m.tocsr()
        else:
            self.matrix = vstack([self.matrix, vec]).tocsr()
            self.row_of[rid] = len(self.ids)
            self.ids = np.append(self.ids, rid)

    def remove(self, rid: int) -> None:
        if rid in self.row_of:
            m = self.matrix.tolil()
            m[self.row_of[rid]] = 0
            self.matrix = m.tocsr()


def embedding_doc(rec: dict, canonical: list[str]) -> str:
    names = ", ".join(canonical[:25]) if canonical else ", ".join(rec["ingredients"][:15])
    return f"{rec['title']}. Ingredients: {names}."


class EmbeddingRetriever:
    """Dense retrieval with a local sentence-transformers model; vectors cached on disk per model+corpus."""

    QUERY_PREFIX = {"intfloat/": ("query: ", "passage: "), "BAAI/bge": ("Represent this sentence for searching relevant passages: ", "")}

    def __init__(self, model_name: str, cache_dir: Path, device: str = "cpu") -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = device
        self.model = None
        self.ids: np.ndarray = np.array([], dtype=np.int64)
        self.matrix: np.ndarray = np.zeros((0, 1), dtype=np.float32)
        self.row_of: dict[int, int] = {}
        self._lock = threading.Lock()
        self.load_seconds = 0.0
        self.encode_seconds = 0.0
        q, p = "", ""
        for prefix, pair in self.QUERY_PREFIX.items():
            if model_name.startswith(prefix):
                q, p = pair
        self.q_prefix, self.p_prefix = q, p

    def load_model(self) -> None:
        from sentence_transformers import SentenceTransformer

        t = time.perf_counter()
        self.model = SentenceTransformer(self.model_name, device=self.device, local_files_only=True)
        self.load_seconds = time.perf_counter() - t

    def _encode(self, texts: list[str], prefix: str) -> np.ndarray:
        vecs = self.model.encode([prefix + t for t in texts], batch_size=64, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)
        return vecs.astype(np.float32)

    def fit(self, docs: dict[int, str]) -> None:
        if self.model is None:
            self.load_model()
        ids = list(docs)
        digest = hashlib.sha1(json.dumps([[i, docs[i]] for i in ids], ensure_ascii=False).encode()).hexdigest()[:16]
        safe = re.sub(r"[^a-zA-Z0-9]+", "_", self.model_name)
        path = self.cache_dir / f"emb_{safe}_{digest}.npz"
        if path.exists():
            data = np.load(path, allow_pickle=False)
            self.ids, self.matrix = data["ids"], data["vecs"]
            log.info("loaded %d cached embeddings from %s", len(self.ids), path.name)
        else:
            t = time.perf_counter()
            self.ids = np.array(ids, dtype=np.int64)
            self.matrix = self._encode([docs[i] for i in ids], self.p_prefix)
            self.encode_seconds = time.perf_counter() - t
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            np.savez(path, ids=self.ids, vecs=self.matrix)
            log.info("encoded %d recipes with %s in %.1fs", len(ids), self.model_name, self.encode_seconds)
        self.row_of = {int(r): i for i, r in enumerate(self.ids)}

    def encode_query(self, text: str) -> np.ndarray:
        with self._lock:
            return self._encode([text], self.q_prefix)[0]

    def scores(self, query: str | np.ndarray) -> np.ndarray:
        if isinstance(query, str):
            if not query.strip():
                return np.zeros(len(self.ids), dtype=np.float32)
            query = self.encode_query(query)
        return self.matrix @ query

    def vector(self, rid: int) -> np.ndarray | None:
        i = self.row_of.get(rid)
        return None if i is None else self.matrix[i]

    def upsert(self, rid: int, doc: str) -> None:
        with self._lock:
            vec = self._encode([doc], self.p_prefix)
        if rid in self.row_of:
            self.matrix[self.row_of[rid]] = vec[0]
        else:
            self.matrix = np.vstack([self.matrix, vec])
            self.row_of[rid] = len(self.ids)
            self.ids = np.append(self.ids, rid)

    def remove(self, rid: int) -> None:
        if rid in self.row_of:
            self.matrix[self.row_of[rid]] = 0.0
