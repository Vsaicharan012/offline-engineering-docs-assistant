import csv, json, sys

from ask import answer_question
from src import config


def _match(srcs, e):
    return any(e["file"].lower() == s["file_name"].lower() and s["page_start"] <= e["page"] <= s["page_end"] for s in srcs)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    qs = json.load(open("test_questions.json", encoding="utf-8"))
    if len(sys.argv) > 1:
        qs = [q for q in qs if q["id"] in sys.argv[1:]]
    rows = []
    for q in qs:
        if "FILL" in json.dumps(q):
            print(f"{q['id']:4} {q['category']:17} SKIP (placeholder not filled)")
            rows.append({"id": q["id"], "category": q["category"], "status": "SKIP"}); continue
        r = answer_question(q["question"])
        row = {"id": q["id"], "category": q["category"], "answer": r["answer"].replace("\n", " "),
               "seconds": r.get("seconds"), "retrieval_ok": "", "citation_ok": "", "keywords_ok": ""}
        if r["error"]:
            row["status"] = "ERROR"; row["answer"] = r["error"]
        elif q["category"] == "not_found":
            row["status"] = "PASS" if not r["found"] else "FAIL"
        else:
            check = all if q.get("require_all_sources") else any
            kw = all(k.lower() in r["answer"].lower() for k in q["expected_keywords"])
            cite = check(_match(r["sources"], e) for e in q["expected_sources"])
            retr = check(_match(r["retrieved"], e) for e in q["expected_sources"])
            row.update(keywords_ok=kw, citation_ok=cite, retrieval_ok=retr,
                       status="PASS" if (r["found"] and kw and cite) else "FAIL")
        rows.append(row)
        print(f"{q['id']:4} {q['category']:17} {row['status']:5} retrieval={row['retrieval_ok']} "
              f"citation={row['citation_ok']} kw={row['keywords_ok']} ({row.get('seconds')}s)")

    scored = [r for r in rows if r["status"] in ("PASS", "FAIL")]
    print(f"\nOVERALL: {sum(r['status']=='PASS' for r in scored)}/{len(scored)} passed (skipped {len(rows)-len(scored)})")
    for c in sorted({r['category'] for r in scored}):
        cs = [r for r in scored if r["category"] == c]
        print(f"  {c:17} {sum(r['status']=='PASS' for r in cs)}/{len(cs)}")
    out = config.DATA_DIR / "eval_results.csv"
    fields = ["id", "category", "status", "retrieval_ok", "citation_ok", "keywords_ok", "seconds", "answer"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print("Saved", out)


if __name__ == "__main__":
    main()