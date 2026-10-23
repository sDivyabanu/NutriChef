"""Runtime configuration. Everything is local; paths and model names are configurable via env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines); existing env vars win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("NUTRICHEF_DATA_DIR", BACKEND_DIR / "data"))
    source_csv: Path = Path(os.getenv("NUTRICHEF_SOURCE_CSV", PROJECT_DIR / "data" / "13k-recipes.csv"))
    db_path: Path = Path(os.getenv("NUTRICHEF_DB", BACKEND_DIR / "data" / "recipes.db"))
    models_dir: Path = Path(os.getenv("NUTRICHEF_MODELS_DIR", PROJECT_DIR / "models"))
    # Sentence-embedding model (local directory or HF id already present in the local cache).
    embedding_model: str = os.getenv("NUTRICHEF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    enable_embeddings: bool = os.getenv("NUTRICHEF_ENABLE_EMBEDDINGS", "1") == "1"
    # Local GGUF model used for recipe generation (llama.cpp). Optional.
    llm_path: str = os.getenv("NUTRICHEF_LLM_PATH", "")
    llm_threads: int = int(os.getenv("NUTRICHEF_LLM_THREADS", "8"))
    llm_ctx: int = int(os.getenv("NUTRICHEF_LLM_CTX", "4096"))
    generation_timeout_s: float = float(os.getenv("NUTRICHEF_GENERATION_TIMEOUT", "180"))
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv(
            "NUTRICHEF_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
    )


settings = Settings()

# Never reach out to the Hugging Face Hub at runtime; models must be fetched by scripts/download_models.py.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HOME", str(settings.models_dir / "hf"))
