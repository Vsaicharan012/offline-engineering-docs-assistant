import csv, re, sys
from pathlib import Path
from typing import Literal

import fitz
import requests
from pydantic import BaseModel, ValidationError

from src import config

FILE = "documents/synthetic/EQ-SPEC-1001_RevB.pdf"
USE_LLM = "--fast" not in sys.argv
Path("data").mkdir(exist_ok=True)
ERR = open("data/requirements_errors.log", "w", encoding="utf-8")


class Cls(BaseModel):
    type: Literal["performance", "environmental", "safety", "interface"]


def fallback(t: str) -> str:
    t = t.lower()
    if any(w in t for w in ["temperature", "humidity", "vibration", "shock", "altitude", "ip65", "810h"]):
        return "environmental"
    if any(w in t for w in ["protection", "polarity", "damage", "461g"]):
        return "safety"
    if any(w in t for w in ["connector", "signal", "marked", "interface"]):
        return "interface"
    return "performance"


def classify(rid: str, text: str) -> str:
    if not USE_LLM:
        return fallback(text)
    for attempt in (1, 2):                       # first try + one retry
        try:
            r = requests.post(f"{config.OLLAMA_URL}/api/chat", timeout=300, json={
                "model": config.CHAT_MODEL, "stream": False,
                "options": {"temperature": 0, "num_ctx": 2048},
                "format": Cls.model_json_schema(),
                "messages": [{"role": "user", "content":
                    "Classify this engineering requirement as exactly one of: performance, environmental, "
                    "safety, interface. Reply as JSON.\nRequirement: " + text}]})
            r.raise_for_status()
            llm_type = Cls.model_validate_json(r.json()["message"]["content"]).type
            kw_type = fallback(text)
            if llm_type == "performance" and kw_type != "performance":
                ERR.write(f"{rid}: LLM said performance, keyword rule says {kw_type}; using {kw_type}\n")
                return kw_type
            return llm_type
        except (ValidationError, KeyError, ValueError, requests.RequestException) as e:
            ERR.write(f"{rid} attempt {attempt}: {type(e).__name__}: {e}\n")
    ERR.write(f"{rid}: gave up, used keyword fallback\n")
    return fallback(text)


items = []                                        # [id, text, page]
for pno, page in enumerate(fitz.open(FILE), 1):
    cur = None
    for line in page.get_text().splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(\d+(?:\.\d+)+)\s+(\S.*)$", s)
        if m:
            cur = [m.group(1), m.group(2), pno]
            items.append(cur)
        elif re.match(r"^\d+\s+[A-Z]", s):        # top-level heading, stop collecting
            cur = None
        elif cur:                                  # wrapped continuation line
            cur[1] += " " + s

rows = []
for rid, text, pno in items:
    if re.search(r"\bshall\b", text, re.I):
        rows.append({"requirement_id": rid, "text": text, "type": classify(rid, text),
                     "section": ".".join(rid.split(".")[:2]), "page": pno})
        print(rid, rows[-1]["type"])

with open("data/requirements.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["requirement_id", "text", "type", "section", "page"])
    w.writeheader()
    w.writerows(rows)
ERR.close()
print(f"saved data/requirements.csv: {len(rows)} requirements (errors logged in data/requirements_errors.log)")