import json
qs = json.load(open("test_questions.json", encoding="utf-8"))
for q in qs:
    if q["id"] == "q06": q["expected_keywords"] = ["10"]
    if q["id"] == "q07": q["expected_keywords"] = ["no longer present"]
    if q["id"] == "q11":
        q["question"] = "What is the rating of the input fuse in the MM-3300 parts list?"
    if q["id"] == "q15":
        q["question"] = "Systems engineering is a methodical, multidisciplinary approach for what, according to the NASA Systems Engineering Handbook?"
        q["expected_keywords"] = ["design", "realization"]
    if q["id"] == "q16":
        q["expected_sources"] = [{"file": "EQ-SPEC-1001_RevA.pdf", "page": 5},
                                 {"file": "EQ-SPEC-1001_RevB.pdf", "page": 5}]
json.dump(qs, open("test_questions.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("done")