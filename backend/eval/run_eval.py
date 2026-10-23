"""Reproducible NLP evaluation for NutriChef.

Usage:  python -m eval.run_eval [--split dev|test|all]
Writes eval/results/eval_<split>.json and eval/results/eval_<split>.md.

Labels: written by the developer (an AI assistant) from the raw text following the guidelines in eval/README.md;
they are not human-verified. Retrieval relevance is defined by explicit, objective term criteria per query
(eval/data/retrieval.jsonl) matched against the raw recipe text, independent of NutriChef's lexicon.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db  # noqa: E402
from app.nlp.engine import NLPEngine  # noqa: E402
from app.nlp.ranker import Prefs, Ranker  # noqa: E402
from app.nlp.text import normalize  # noqa: E402

DATA = ROOT / "eval" / "data"
OUT = ROOT / "eval" / "results"


def load(name: str, split: str) -> list[dict]:
    rows = [json.loads(l) for l in (DATA / name).read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if split == "all" or r["split"] == split]


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3), "tp": tp, "fp": fp, "fn": fn}


# ------------------------------------------------------------------ extraction
def gold_pairs(expect: dict) -> list[tuple[set, set]]:
    """[(accepted roles, accepted names)] per gold ingredient."""
    out = []
    for roles, names in expect.items():
        if roles == "excluded_groups":
            continue
        for n in names:
            out.append((set(roles.split("|")), set(n.split("|"))))
    return out


def match_items(pred: list[tuple[str, str]], gold: list[tuple[set, set]], use_role: bool) -> tuple[int, int, int]:
    used = set()
    tp = 0
    for roles, names in gold:
        for i, (pn, pr) in enumerate(pred):
            if i in used:
                continue
            if pn in names and (not use_role or pr in roles):
                used.add(i)
                tp += 1
                break
    return tp, len(pred) - tp, len(gold) - tp


def naive_baseline(text: str) -> list[str]:
    """Port of the original app's src/lib/normalizeIngredient.ts applied to comma/and-split input."""
    parts = re.split(r",|\band\b|\bwith\b", text.lower())
    out = []
    for s in parts:
        s = re.sub(r"\d+\s*\d*/?\d*", "", s).strip()
        s = re.sub(r"\((.*?)\)", "", s)
        s = re.sub(r"\b(cups?|tablespoons?|tbsp|teaspoons?|tsp|grams?|g|kg|ml|ltr|lbs?|pounds?)\b", "", s)
        s = re.sub(r"\b(of|and|or)\b", "", s)
        s = re.sub(r"[^a-z\s-]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        exc = {"scallions": "scallion", "tomatoes": "tomato", "potatoes": "potato", "mushrooms": "mushroom", "berries": "berry"}
        if s in exc:
            s = exc[s]
        elif s.endswith("es"):
            s = s[:-2]
        elif s.endswith("s"):
            s = s[:-1]
        if s:
            out.append(s)
    return out


def eval_extraction(eng: NLPEngine, split: str) -> dict:
    items = load("extraction.jsonl", split)
    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = None
    tot = {"role": [0, 0, 0], "name": [0, 0, 0], "naive": [0, 0, 0], "ner": [0, 0, 0]}
    qty_ok = qty_n = 0
    by_tag: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    errors = []
    for it in items:
        pq = eng.parser.parse(it["text"])
        pred = [(r.name, r.role) for r in pq.ingredients]
        # group exclusions that the parser represents as groups (e.g. "no soy")
        pred += [(g, "excluded") for g in pq.excluded_groups if g in it["expect"].get("excluded_groups", [])]
        gold = gold_pairs(it["expect"])
        gold += [({"excluded"}, {g}) for g in it["expect"].get("excluded_groups", [])]
        for key, use_role in (("role", True), ("name", False)):
            tp, fp, fn = match_items(pred, gold, use_role)
            for k in range(3):
                tot[key][k] += (tp, fp, fn)[k]
        tp, fp, fn = match_items(pred, gold, True)
        exact = fp == 0 and fn == 0
        for tag in it.get("tags", []):
            by_tag[tag][0] += exact
            by_tag[tag][1] += 1
        if not exact:
            errors.append({"id": it["id"], "text": it["text"], "pred": pred, "expect": it["expect"]})
        for name, (q, u) in (it.get("quantities") or {}).items():
            qty_n += 1
            r = next((x for x in pq.ingredients if x.name == name), None)
            if r and r.quantity is not None and abs(r.quantity - q) < 1e-6 and (u is None or r.unit == u):
                qty_ok += 1
        # baselines: name-only, mapped through the lexicon so naming differences don't count against them
        naive = [(eng.lex.lookup(s) or s, "x") for s in naive_baseline(it["text"])]
        tp, fp, fn = match_items(naive, gold, False)
        for k in range(3):
            tot["naive"][k] += (tp, fp, fn)[k]
        if nlp:
            ents = [(eng.lex.lookup(e.text) or e.text.lower(), "x") for e in nlp(it["text"]).ents]
            tp, fp, fn = match_items(ents, gold, False)
            for k in range(3):
                tot["ner"][k] += (tp, fp, fn)[k]
    return {
        "n": len(items),
        "nutrichef_name_and_role": prf(*tot["role"]),
        "nutrichef_name_only": prf(*tot["name"]),
        "baseline_original_normalizer_name_only": prf(*tot["naive"]),
        "baseline_spacy_ner_name_only": prf(*tot["ner"]) if nlp else None,
        "quantity_accuracy": round(qty_ok / qty_n, 3) if qty_n else None, "quantity_n": qty_n,
        "exact_item_accuracy_by_tag": {k: {"acc": round(v[0] / v[1], 3), "n": v[1]} for k, v in sorted(by_tag.items())},
        "errors": errors,
    }


# ------------------------------------------------------------------ query understanding
FIELDS = ("diets", "cuisines", "meal_types", "max_time_min", "nutrition", "qualities", "similar_to", "excluded_groups", "servings")


def eval_queries(eng: NLPEngine, split: str) -> dict:
    items = load("queries.jsonl", split)
    intent_ok = 0
    field = defaultdict(lambda: [0, 0])
    lang = [0, 0]
    clar = [0, 0]
    conf = [0, 0]
    errors = []
    confusion: Counter = Counter()
    for it in items:
        pq = eng.parser.parse(it["text"])
        ok_i = pq.intent == it["intent"]
        intent_ok += ok_i
        confusion[(it["intent"], pq.intent)] += 1
        errs = [] if ok_i else [f"intent {pq.intent}"]
        for f in FIELDS:
            if f not in it:
                continue
            got = getattr(pq, f)
            exp = it[f]
            if f == "nutrition":
                got = sorted([n.nutrient, n.op, n.value] for n in got)
                exp = sorted(exp)
            elif f == "qualities":
                ok = set(exp) <= set(got)
                field[f][0] += ok
                field[f][1] += 1
                if not ok:
                    errs.append(f"{f}: {got}")
                continue
            elif isinstance(exp, list):
                got, exp = sorted(got), sorted(exp)
            ok = got == exp
            field[f][0] += ok
            field[f][1] += 1
            if not ok:
                errs.append(f"{f}: got {got}, expected {exp}")
        if "language" in it:
            lang[0] += pq.language == it["language"]
            lang[1] += 1
        if "clarification" in it:
            clar[0] += bool(pq.clarification) == it["clarification"]
            clar[1] += 1
        if "conflict" in it:
            conf[0] += bool(pq.conflicts) == it["conflict"]
            conf[1] += 1
        if errs:
            errors.append({"id": it["id"], "text": it["text"], "errors": errs})
    return {
        "n": len(items), "intent_accuracy": round(intent_ok / len(items), 3),
        "field_accuracy": {f: {"acc": round(v[0] / v[1], 3), "n": v[1]} for f, v in field.items()},
        "tamil_english_detection": {"acc": round(lang[0] / lang[1], 3), "n": lang[1]} if lang[1] else None,
        "clarification_detection": {"acc": round(clar[0] / clar[1], 3), "n": clar[1]} if clar[1] else None,
        "conflict_detection": {"acc": round(conf[0] / conf[1], 3), "n": conf[1]} if conf[1] else None,
        "intent_confusions": {f"{a}->{b}": c for (a, b), c in confusion.items() if a != b},
        "errors": errors,
    }


def eval_synonyms(eng: NLPEngine, split: str) -> dict:
    items = load("synonyms.jsonl", split)
    by_kind = defaultdict(lambda: [0, 0])
    errors = []
    for it in items:
        ms = eng.fx.extractor.mentions(normalize(it["surface"]), strict_ambiguous=False)
        got = ms[0].name if len(ms) == 1 else (eng.lex.lookup(it["surface"]) or (ms[0].name if ms else None))
        ok = got == it["canonical"]
        by_kind[it["kind"]][0] += ok
        by_kind[it["kind"]][1] += 1
        if not ok:
            errors.append({"surface": it["surface"], "expected": it["canonical"], "got": got})
    n_ok = sum(v[0] for v in by_kind.values())
    return {"n": len(items), "accuracy": round(n_ok / len(items), 3),
            "by_kind": {k: {"acc": round(v[0] / v[1], 3), "n": v[1]} for k, v in by_kind.items()}, "errors": errors}


def eval_typos(eng: NLPEngine, split: str) -> dict:
    items = load("typos.jsonl", split)
    fix = [0, 0]
    keep = [0, 0]
    errors = []
    for it in items:
        c = eng.speller.correct_word(it["word"])
        out = c.corrected if c else it["word"]
        if it.get("must_not_change"):
            keep[1] += 1
            keep[0] += out == it["word"]
            if out != it["word"]:
                errors.append({"word": it["word"], "wrongly_changed_to": out})
        else:
            fix[1] += 1
            ok = out in it["expect"].split("|")
            fix[0] += ok
            if not ok:
                errors.append({"word": it["word"], "got": out, "expected": it["expect"]})
    return {"misspellings_corrected": {"acc": round(fix[0] / fix[1], 3), "n": fix[1]},
            "correct_words_left_unchanged": {"acc": round(keep[0] / keep[1], 3), "n": keep[1]}, "errors": errors}


# ------------------------------------------------------------------ retrieval
def term_hit(text: str, term: str) -> bool:
    if term.endswith(" "):
        return term in text
    return re.search(r"(?<![a-z])" + re.escape(term) + r"(?:s|es)?(?![a-z])", text) is not None


def relevant(rec: dict, crit: dict) -> tuple[bool, bool]:
    text = normalize(rec["title"] + " \n " + " \n ".join(rec["ingredients"]))
    has_all = all(any(term_hit(text, t) for t in group) for group in crit["all"])
    violates = any(term_hit(text, t) for t in crit["none"])
    return has_all and not violates, violates


def eval_retrieval(eng: NLPEngine, ranker: Ranker, split: str, k: int = 10) -> dict:
    items = load("retrieval.jsonl", split)
    systems = ["keyword", "tfidf", "embedding", "hybrid"]
    res = {s: defaultdict(list) for s in systems}
    for it in items:
        pq = eng.parser.parse(it["query"])
        for s in systems:
            t0 = time.perf_counter()
            out = ranker.search(pq, Prefs(apply_profile=False), k=k, mode=s)
            res[s]["latency_ms"].append((time.perf_counter() - t0) * 1000)
            recs = db.get_recipes([h.recipe_id for h in out.hits])
            rels, viol = [], []
            for h in out.hits[:k]:
                r, v = relevant(recs[h.recipe_id], it)
                rels.append(r)
                viol.append(v)
            rels += [False] * (k - len(rels))
            res[s]["p@5"].append(sum(rels[:5]) / 5)
            res[s]["p@10"].append(sum(rels[:k]) / k)
            first = next((i for i, r in enumerate(rels) if r), None)
            res[s]["mrr"].append(1 / (first + 1) if first is not None else 0.0)
            dcg = sum(1 / math.log2(i + 2) for i, r in enumerate(rels) if r)
            idcg = sum(1 / math.log2(i + 2) for i in range(k))
            res[s]["ndcg@10"].append(dcg / idcg)
            res[s]["violation@10"].append(sum(viol) / max(1, len(out.hits[:k])) if it["none"] else None)
            res[s]["returned"].append(len(out.hits))
    summary = {}
    for s in systems:
        d = res[s]
        viol = [v for v in d["violation@10"] if v is not None]
        lat = sorted(d["latency_ms"])
        summary[s] = {
            "p@5": round(statistics.mean(d["p@5"]), 3), "p@10": round(statistics.mean(d["p@10"]), 3),
            "mrr": round(statistics.mean(d["mrr"]), 3), "ndcg@10": round(statistics.mean(d["ndcg@10"]), 3),
            "constraint_violation_rate@10": round(statistics.mean(viol), 3) if viol else None,
            "latency_ms_p50": round(lat[len(lat) // 2], 1), "latency_ms_p95": round(lat[int(len(lat) * 0.95) - 1], 1),
        }
    return {"n_queries": len(items), "k": k, "embedding_model": eng.embedding_model, "systems": summary}


def to_markdown(r: dict) -> str:
    L = [f"# NutriChef NLP evaluation — split: {r['split']}", "", f"Recipes indexed: {r['recipes']} · run at {r['timestamp']}", ""]
    ex = r["extraction"]
    L += ["## Ingredient extraction", "", "| System | Precision | Recall | F1 |", "|---|---|---|---|"]
    for key, label in (("nutrichef_name_and_role", "NutriChef (name + role)"), ("nutrichef_name_only", "NutriChef (name only)"),
                       ("baseline_original_normalizer_name_only", "Original app normaliser (name only)"),
                       ("baseline_spacy_ner_name_only", "spaCy en_core_web_sm NER (name only)")):
        v = ex.get(key)
        if v:
            L.append(f"| {label} | {v['precision']} | {v['recall']} | {v['f1']} |")
    L += ["", f"Quantity+unit accuracy: {ex['quantity_accuracy']} (n={ex['quantity_n']}); items: {ex['n']}", ""]
    q = r["queries"]
    L += ["## Query understanding", "", f"Intent accuracy: **{q['intent_accuracy']}** (n={q['n']})", "", "| Field | Accuracy | n |", "|---|---|---|"]
    for f, v in q["field_accuracy"].items():
        L.append(f"| {f} | {v['acc']} | {v['n']} |")
    for key in ("tamil_english_detection", "clarification_detection", "conflict_detection"):
        if q.get(key):
            L.append(f"| {key} | {q[key]['acc']} | {q[key]['n']} |")
    s = r["synonyms"]
    t = r["typos"]
    L += ["", "## Normalisation", "", f"Synonym → canonical accuracy: **{s['accuracy']}** (n={s['n']}) — "
          + ", ".join(f"{k} {v['acc']} (n={v['n']})" for k, v in s["by_kind"].items()),
          "", f"Typo correction: {t['misspellings_corrected']['acc']} (n={t['misspellings_corrected']['n']}); "
          f"correct words left unchanged: {t['correct_words_left_unchanged']['acc']} (n={t['correct_words_left_unchanged']['n']})", ""]
    rt = r["retrieval"]
    L += [f"## Retrieval (top-{rt['k']}, {rt['n_queries']} queries, embeddings: {rt['embedding_model']})", "",
          "| System | P@5 | P@10 | MRR | nDCG@10 | Constraint violations@10 | p50 ms | p95 ms |", "|---|---|---|---|---|---|---|---|"]
    for sname, v in rt["systems"].items():
        L.append(f"| {sname} | {v['p@5']} | {v['p@10']} | {v['mrr']} | {v['ndcg@10']} | {v['constraint_violation_rate@10']} | {v['latency_ms_p50']} | {v['latency_ms_p95']} |")
    L += ["", "Constraint violations: share of returned top-10 recipes containing an excluded ingredient (queries with exclusions only).", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    args = ap.parse_args()
    t0 = time.perf_counter()
    eng = NLPEngine()
    eng.build()
    build_s = time.perf_counter() - t0
    ranker = Ranker(eng)
    report = {"split": args.split, "timestamp": time.strftime("%Y-%m-%d %H:%M"), "recipes": len(eng.ids),
              "engine_build_seconds_warm_cache": round(build_s, 1),
              "extraction": eval_extraction(eng, args.split), "queries": eval_queries(eng, args.split),
              "synonyms": eval_synonyms(eng, args.split), "typos": eval_typos(eng, args.split),
              "retrieval": eval_retrieval(eng, ranker, args.split)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"eval_{args.split}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md = to_markdown(report)
    (OUT / f"eval_{args.split}.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
