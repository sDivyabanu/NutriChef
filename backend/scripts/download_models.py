"""One-time download of the open-source models NutriChef runs locally.

After this, the API loads everything from ./models with HF_HUB_OFFLINE=1 (no network at runtime).

Usage:
  python -m scripts.download_models                 # embedding models used by search (default + benchmark candidates)
  python -m scripts.download_models --llm qwen3-4b  # optional GGUF model for recipe generation
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MODELS = ROOT / "models"
os.environ["HF_HOME"] = str(MODELS / "hf")
os.environ.pop("HF_HUB_OFFLINE", None)

# (repo id, license) — all permissively licensed
EMBEDDING_MODELS = {
    "sentence-transformers/all-MiniLM-L6-v2": "Apache-2.0",
    "BAAI/bge-small-en-v1.5": "MIT",
    "intfloat/multilingual-e5-small": "MIT",
    "intfloat/e5-small-v2": "MIT",
}
# GGUF builds for llama.cpp (CPU). Sizes are the Q4_K_M files.
LLMS = {
    "qwen3-4b": ("unsloth/Qwen3-4B-Instruct-2507-GGUF", "Qwen3-4B-Instruct-2507-Q4_K_M.gguf", "Apache-2.0", "~2.5 GB"),
    "qwen3-1.7b": ("unsloth/Qwen3-1.7B-GGUF", "Qwen3-1.7B-Q4_K_M.gguf", "Apache-2.0", "~1.1 GB"),
    "llama3.2-3b": ("bartowski/Llama-3.2-3B-Instruct-GGUF", "Llama-3.2-3B-Instruct-Q4_K_M.gguf", "Llama 3.2 Community", "~2.0 GB"),
    "phi4-mini": ("unsloth/Phi-4-mini-instruct-GGUF", "Phi-4-mini-instruct-Q4_K_M.gguf", "MIT", "~2.5 GB"),
}


def main() -> None:
    from huggingface_hub import hf_hub_download, snapshot_download

    ap = argparse.ArgumentParser()
    ap.add_argument("--embeddings", nargs="*", default=list(EMBEDDING_MODELS), help="embedding repo ids")
    ap.add_argument("--llm", nargs="*", default=[], choices=list(LLMS), help="GGUF models to fetch")
    args = ap.parse_args()

    for repo in args.embeddings:
        print(f"[embeddings] {repo} ({EMBEDDING_MODELS.get(repo, '?')})", flush=True)
        snapshot_download(repo, allow_patterns=["*.json", "*.txt", "*.safetensors", "*.model", "1_Pooling/*",
                                                "modules.json", "sentence_*", "tokenizer*", "vocab*", "special_tokens*"])
    for key in args.llm:
        repo, filename, lic, size = LLMS[key]
        print(f"[llm] {repo}/{filename} ({lic}, {size})", flush=True)
        path = hf_hub_download(repo, filename, local_dir=MODELS / "llm")
        print("  ->", path)
    print("done")


if __name__ == "__main__":
    sys.exit(main())
