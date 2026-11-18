import csv, json, sys
from src.retriever import HybridRetriever

sys.stdout.reconfigure(encoding="utf-8")
r = HybridRetriever()
qs = {q["id"]: q for q in json.load(open("test_questions.json", encoding="utf-8"))}
rows = {x["id"]: x for x in csv.DictReader(open("data/eval_results.csv", encoding="utf-8"))}
for i in ["q06", "q07", "q10", "q11", "q15", "q16", "q18", "q19"]:
    print("\n==", i, qs[i]["question"])
    print("expected:", qs[i].get("expected_sources"), qs[i].get("expected_keywords"))
    print("ANSWER:", rows[i]["answer"][:400])
    for h in r.search(qs[i]["question"])["hits"]:
        m = h["meta"]
        print("  ", m["file_name"], "p", m["page_start"], "-", m["page_end"], "sec", m["section"])