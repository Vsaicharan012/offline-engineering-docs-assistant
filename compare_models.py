import json, subprocess, sys

from src import config
from ask import answer_question

sys.stdout.reconfigure(encoding="utf-8")
qs = {q["id"]: q for q in json.load(open("test_questions.json", encoding="utf-8"))}
IDS = ["q01", "q02", "q12", "q18"]          # 3 factual/table + 1 not-found
SETUPS = [("llama3.2:3b", 4096), ("llama3.2:1b", 4096), ("llama3.2:3b", 2048)]
rows = []
for model, ctx in SETUPS:
    config.CHAT_MODEL, config.NUM_CTX = model, ctx
    ok, secs = 0, []
    for i in IDS:
        q = qs[i]
        r = answer_question(q["question"])
        secs.append(r["seconds"])
        if q["category"] == "not_found":
            ok += (not r["found"])
        else:
            ok += bool(r["found"] and all(k.lower() in r["answer"].lower() for k in q["expected_keywords"]))
    ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout.splitlines()
    row = next((l for l in ps if l.startswith(model)), "")
    mem = " ".join(row.split()[2:4]) if row else "n/a"
    rows.append(f"| {model} | {ctx} | {mem} | {sum(secs)/len(secs):.0f} s/answer | {ok}/{len(IDS)} |")
    print(rows[-1], flush=True)

print("\n| model | num_ctx | memory (ollama ps) | speed | correct |\n|---|---|---|---|---|")
print("\n".join(rows))