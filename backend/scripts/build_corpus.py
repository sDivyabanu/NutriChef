"""Reproducible import of data/13k-recipes.csv into the local SQLite recipe store.

- The CSV is never modified; original ingredient lines and instructions are stored verbatim.
- Only rows imported from the CSV are touched (source='epicurious-13k'); user-created and
  generated recipes are preserved across re-runs.
- Writes a data-quality report to backend/data/corpus_report.json.

Usage:  python -m scripts.build_corpus [--rebuild]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import db  # noqa: E402
from app.config import settings  # noqa: E402

SOURCE = "epicurious-13k"


def parse_list(cell) -> list[str]:
    if not isinstance(cell, str) or not cell.strip():
        return []
    try:
        value = ast.literal_eval(cell)  # literal_eval only evaluates Python literals (safe)
    except (ValueError, SyntaxError):
        return []
    return [str(x).strip() for x in value if str(x).strip()] if isinstance(value, list) else []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="re-import CSV rows even if already present")
    args = ap.parse_args()

    csv_path = settings.source_csv
    raw = csv_path.read_bytes()
    csv_sha = hashlib.sha256(raw).hexdigest()
    conn = db.get_conn()

    existing = conn.execute("SELECT COUNT(*) FROM recipes WHERE source = ?", (SOURCE,)).fetchone()[0]
    if existing and not args.rebuild and db.get_meta("corpus_csv_sha256") == csv_sha:
        print(f"Corpus already imported ({existing} rows, sha {csv_sha[:12]}). Use --rebuild to re-import.")
        return

    df = pd.read_csv(csv_path)
    report: Counter = Counter()
    seen: dict[str, int] = {}
    rows = []
    for _, r in df.iterrows():
        report["csv_rows"] += 1
        ingredients = parse_list(r.get("Ingredients"))
        title = r.get("Title") if isinstance(r.get("Title"), str) and r.get("Title").strip() else None
        instructions = r.get("Instructions") if isinstance(r.get("Instructions"), str) else ""
        if not ingredients:
            report["skipped_no_ingredients"] += 1
            continue
        if title is None:
            report["missing_title_filled_from_slug"] += 1
            slug = str(r.get("Image_Name") or "").replace("-", " ").strip()
            title = slug.title() if slug and slug != "#Name?" else "Untitled recipe"
        if not instructions.strip():
            report["missing_instructions"] += 1
        key = hashlib.md5(json.dumps([title.strip().lower(), ingredients, instructions.strip()]).encode()).hexdigest()
        if key in seen:
            report["skipped_exact_duplicates"] += 1
            continue
        seen[key] = 1
        now = time.time()
        rows.append(
            (SOURCE, str(r.iloc[0]), title.strip(), json.dumps(ingredients, ensure_ascii=False),
             instructions.strip(), r.get("Image_Name") if isinstance(r.get("Image_Name"), str) else None, now, now)
        )

    with db.tx() as c:
        c.execute("DELETE FROM recipes WHERE source = ?", (SOURCE,))
        c.executemany(
            "INSERT INTO recipes (source, source_ref, title, ingredients, instructions, image_name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    report["imported"] = len(rows)
    titles = Counter(r[2].lower() for r in rows)
    report["titles_shared_by_multiple_recipes"] = sum(1 for t, n in titles.items() if n > 1)
    db.set_meta("corpus_csv_sha256", csv_sha)
    db.set_meta("corpus_imported_at", str(time.time()))

    out = {
        "source_csv": str(csv_path.name),
        "sha256": csv_sha,
        "counts": dict(report),
        "fields_absent_in_source": ["nutrition", "servings", "cooking_time", "cuisine", "meal_type", "diet_labels", "images"],
    }
    (settings.data_dir / "corpus_report.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
