import json
qs = json.load(open("test_questions.json", encoding="utf-8"))
for q in qs:
    if q["id"] == "q07":
        q["expected_sources"] = [{"file": "MIL-STD-882E.pdf", "page": 19}, {"file": "MIL-STD-882E.pdf", "page": 20}]
json.dump(qs, open("test_questions.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("done")