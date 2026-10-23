"""Benchmark local LLMs for recipe generation on this machine.

For each model: start llama-server, run the full NutriChef generation pipeline (retrieval grounding, constrained
JSON, validation, one repair round) on eval/data/generation.jsonl, and record speed, memory and constraint
adherence. Adherence is measured twice: by NutriChef's validator and by an independent forbidden-word scan.

Usage:
  python -m eval.bench_llm --split dev --backend vulkan
  python -m eval.bench_llm --split test --backend vulkan --models Qwen3-4B-Instruct-2507-Q4_K_M.gguf
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.nlp import llm as llm_mod  # noqa: E402
from app.nlp.engine import NLPEngine  # noqa: E402
from app.nlp.generate import RecipeGenerator  # noqa: E402
from app.nlp.ranker import Prefs, Ranker  # noqa: E402

DATA = ROOT / "eval" / "data" / "generation.jsonl"
OUT = ROOT / "eval" / "results"
ALLOWED_COMPOUNDS = [
    "coconut milk", "oat milk", "soy milk", "almond milk", "plant milk", "rice milk", "cashew milk", "vegan butter",
    "plant butter", "peanut-free", "egg-free", "dairy-free", "nut-free", "gluten-free", "vegan cheese", "coconut cream",
    "cashew cream", "coconut yogurt", "soy yogurt", "plant-based yogurt", "dairy-free yogurt", "flax egg", "chia egg",
    "eggplant", "egg replacer", "cream of tartar", "chickpea flour", "gram flour", "rice flour", "oat flour",
    "almond flour", "gluten-free flour", "coconut flour", "buckwheat flour", "corn flour", "cornflour", "tapioca flour",
    "sorghum flour", "millet flour", "besan flour", "without", "no ", "free", "vegan mayonnaise", "nutritional yeast",
    "butternut", "cocoa butter", "sunflower seed butter", "eggless", "milk-free", "dairy free", "creamy",
]


def independent_scan(text: str, forbidden: list[str]) -> list[str]:
    t = text.lower()
    for comp in sorted(ALLOWED_COMPOUNDS, key=len, reverse=True):
        t = t.replace(comp, " ")
    hits = []
    for w in forbidden:
        if re.search(r"(?<![a-z])" + re.escape(w.lower()) + r"(?:s|es)?(?![a-z])", t):
            hits.append(w)
    return hits


def has_required(text: str, alternatives: str) -> bool:
    t = text.lower()
    return any(re.search(r"(?<![a-z])" + re.escape(a.lower()), t) for a in alternatives.split("|"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--backend", default="vulkan", choices=["cpu", "vulkan"])
    ap.add_argument("--models", nargs="*", default=None)
    args = ap.parse_args()

    items = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
    items = [i for i in items if args.split == "all" or i["split"] == args.split]
    models = args.models or sorted(p.name for p in llm_mod.LLM_DIR.glob("*.gguf"))
    print(f"building engine… ({len(items)} requests, models: {models})", flush=True)
    eng = NLPEngine()
    eng.build()
    gen = RecipeGenerator(eng, Ranker(eng))
    prefs = Prefs(apply_profile=False)
    report = {"machine": {"cpu": platform.processor(), "ram_gb": round(psutil.virtual_memory().total / 1e9, 1),
                          "os": platform.platform()}, "backend": args.backend, "split": args.split, "models": {}}

    for model in models:
        path = llm_mod.LLM_DIR / model
        srv = llm_mod.LlamaServer(path, backend=args.backend)
        t0 = time.perf_counter()
        srv.start()
        load_s = time.perf_counter() - t0
        llm_mod.llm_service.server = srv
        proc = psutil.Process(srv.proc.pid)
        peak_rss = proc.memory_info().rss
        rows = []
        for it in items:
            t1 = time.perf_counter()
            res = gen.generate(it["request"], prefs, use_llm=True)
            elapsed = time.perf_counter() - t1
            peak_rss = max(peak_rss, proc.memory_info().rss)
            rec = res.recipe
            text = ""
            if rec:
                text = "\n".join(res.ingredient_lines + rec.get("steps", []) + [rec.get("title", "")])
            hits = independent_scan(text, it.get("forbidden", [])) if rec else []
            req_ok = all(has_required(text, r) for r in it.get("required", [])) if rec else False
            serv_ok = (rec or {}).get("servings") == it["servings"] if "servings" in it and rec else None
            time_ok = None
            if "max_time" in it and rec:
                time_ok = (rec.get("prep_time_min") or 0) + (rec.get("cook_time_min") or 0) <= it["max_time"]
            row = {
                "id": it["id"], "method": res.method, "json_valid": rec is not None, "attempts": res.attempts,
                "validator_pass": res.valid, "first_attempt_pass": res.valid and res.attempts == 1,
                "failed_checks": [c["check"] for c in res.checks if not c["passed"]],
                "independent_forbidden_hits": hits, "required_present": req_ok, "servings_ok": serv_ok, "time_ok": time_ok,
                "seconds": round(elapsed, 1), "tokens_per_second": res.timing.get("tokens_per_second"),
                "completion_tokens": res.timing.get("completion_tokens"), "title": (rec or {}).get("title"),
            }
            rows.append(row)
            print(json.dumps(row), flush=True)
        srv.stop()
        llm_mod.llm_service.server = None
        n = len(rows)
        llm_rows = [r for r in rows if r["method"] == "local-llm"]

        def rate(key):
            vals = [r[key] for r in rows if r[key] is not None]
            return round(sum(bool(v) for v in vals) / len(vals), 3) if vals else None

        summary = {
            "n": n, "load_seconds": round(load_s, 1), "peak_rss_gb": round(peak_rss / 1e9, 2),
            "json_valid_rate": rate("json_valid"), "validator_pass_rate": rate("validator_pass"),
            "first_attempt_pass_rate": rate("first_attempt_pass"),
            "independent_violation_rate": round(sum(bool(r["independent_forbidden_hits"]) for r in rows) / n, 3),
            "required_present_rate": rate("required_present"), "servings_ok_rate": rate("servings_ok"),
            "time_ok_rate": rate("time_ok"),
            "mean_seconds": round(sum(r["seconds"] for r in rows) / n, 1),
            "mean_tokens_per_second": round(sum(r["tokens_per_second"] or 0 for r in llm_rows) / max(1, len(llm_rows)), 1),
            "fell_back": n - len(llm_rows),
        }
        report["models"][model] = {"summary": summary, "rows": rows}
        print(model, json.dumps(summary), flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"llm_bench_{args.split}_{args.backend}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
