"""Process-wide service container: NLP components are loaded once at startup and reused."""
from __future__ import annotations

import logging
import threading
from typing import Any

from . import db
from .config import settings

log = logging.getLogger("nutrichef")

components: dict[str, str] = {"recipe_store": "ok", "nlp_engine": "loading"}
engine = None
ranker = None
_ready = threading.Event()


def ready() -> bool:
    return _ready.is_set()


def get_engine():
    if not _ready.wait(timeout=120):
        raise RuntimeError("NLP engine is still loading")
    return engine


def derived_info(f) -> dict[str, Any] | None:
    if f is None:
        return None
    return {
        "diet": {k: bool(v) for k, v in f.diet.items()},
        "diet_uncertain": f.diet_uncertain[:10],
        "allergens": f.allergens,
        "cuisine_guess": f.cuisine,
        "meal_type_guess": f.meal_types,
        "estimated_time_min": f.est_time_min,
        "time_basis": f.time_basis,
        "difficulty": f.difficulty,
        "spice_level": f.spice_level,
    }


def enrich_recipe(rec: dict[str, Any]) -> dict[str, Any]:
    """Attach parsed ingredients and derived (labelled) info."""
    if engine is None or not ready():
        return rec
    f = engine.feature(rec["id"])
    if f is None:
        f = engine.fx.compute(rec)
    rec = dict(rec)
    rec["parsed_ingredients"] = f.parsed
    rec["derived"] = derived_info(f)
    return rec


def _on_change(recipe_id: int, action: str) -> None:
    if engine is not None and ready():
        try:
            engine.on_recipe_change(recipe_id, action)
        except Exception:  # never fail a CRUD write because indexing failed; log it
            log.exception("incremental index update failed for recipe %s", recipe_id)


def _load() -> None:
    global engine, ranker
    from .nlp.engine import NLPEngine
    from .nlp.ranker import Ranker

    try:
        eng = NLPEngine(enable_embeddings=settings.enable_embeddings)
        eng.build()
        engine = eng
        ranker = Ranker(eng)
        components.update({f"nlp.{k}": v for k, v in eng.status.items()})
        components["nlp_engine"] = "ok"
    except Exception as exc:
        log.exception("NLP engine failed to load")
        components["nlp_engine"] = f"error: {exc}"
    finally:
        _ready.set()


def startup() -> None:
    db.get_conn()
    db.on_change(_on_change)
    # Load in a background thread so the API (CRUD, health) is available immediately.
    threading.Thread(target=_load, name="nlp-loader", daemon=True).start()
