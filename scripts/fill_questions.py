import json
qs = json.load(open("test_questions.json", encoding="utf-8"))
new = {
 "q06": ("What monetary loss qualifies as Catastrophic (Severity Category 1) under MIL-STD-882E?",
         "Monetary loss equal to or exceeding $10 million.", ["10 million"], "MIL-STD-882E.pdf", 19),
 "q07": ("What does Probability Level F represent in MIL-STD-882E?",
         "Eliminated: the hazard is no longer present.", ["eliminated"], "MIL-STD-882E.pdf", 19),
 "q08": ("How many elements are included in the MIL-STD-882E system safety process?",
         "Eight elements.", ["eight"], "MIL-STD-882E.pdf", 17),
 "q15": ("How does NASA define systems engineering in its Systems Engineering Handbook?",
         "A methodical, multidisciplinary approach for the design, realization, technical management, operations, and retirement of a system.",
         ["multidisciplinary"], "NASA-SP-2016-6105-Rev2.pdf", 16),
}
for q in qs:
    if q["id"] in new:
        t, a, k, f, p = new[q["id"]]
        q.update(question=t, expected_answer=a, expected_keywords=k, expected_sources=[{"file": f, "page": p}])
json.dump(qs, open("test_questions.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("done")