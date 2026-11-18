import argparse, datetime, json, re, sys, time
from pathlib import Path

import requests

from src import config
from src.llm import NOT_FOUND, generate_answer
from src.retriever import EmptyIndexError, HybridRetriever, family_of

_retriever = None


def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def _family(file_name):
    return re.sub(r"[_\-\s]?rev[_\-\s]?[A-Z0-9]{1,2}(?=[_\-\s]|$)", "", Path(file_name).stem, flags=re.I)


def _revision_warnings(hits):
    fam = {}
    for h in hits:
        if h["meta"]["revision"] != "N/A":
            fam.setdefault(_family(h["meta"]["file_name"]), set()).add(h["meta"]["revision"])
    return [f"Multiple revisions of {f} were retrieved (Rev {', Rev '.join(sorted(r))}). "
            f"Check the ECN / revision history before relying on a single value."
            for f, r in fam.items() if len(r) > 1]


def _src(h, tag=None):
    m = h["meta"]
    return {"tag": tag, "file_name": m["file_name"], "page_start": m["page_start"], "page_end": m["page_end"],
            "section": m["section"], "revision": m["revision"], "marking": m["marking"]}


def _per_revision(question, hits, out):
    """Answer each revision of a document separately. Returns True if handled."""
    if not re.search(r"\brev(ision)?s?\b", question, re.I):
        return False
    if re.search(r"\bchang|\bdiffer|\bECN\b|\bauthori", question, re.I):
        return False                       # change questions are answered from the ECN, normal path
    r = _get_retriever()
    named = [f for f in r.family_files if re.search(re.escape(f), question, re.I) and len(r.family_files[f]) > 1]
    fams = named or sorted({family_of(h["meta"]["file_name"]) for h in hits if h["meta"]["revision"] != "N/A"})
    fams = [f for f in fams if len(r.family_files.get(f, ())) > 1]
    if not fams:
        return False
    fam = fams[0]
    core = question
    for f in r.family_files:
        core = re.sub(re.escape(f), " ", core, flags=re.I)
    core = re.sub(r"(?i)\brev(ision)?s?\s*[A-Z]?\b|\b(and|in|of|for|the)\b|\?", " ", core)
    core = " ".join(core.split()) or question

    lines, srcs = [], []
    files = sorted(r.family_files[fam])
    letters = set(re.findall(r"(?i:rev(?:ision)?)\s*([A-Z])\b", question))
    if len(letters) == 1:                      # only one revision named -> answer from that file only
        L = letters.pop()
        files = [f for f in files if re.search(rf"rev[_\-\s]?{L}\b", f, re.I)] or files
    for fn in files:
        file_hits = r.search_file(core, fn, 2)
        raw, used = generate_answer(core + "?", file_hits)
        rev = used[0]["meta"]["revision"] if used else "?"
        text = raw.strip()
        if "not found in the documents" in text.lower():
            lines.append(f"Revision {rev} ({fn}): not found in this revision.")
            continue

        def renum(m, used=used):
            n = int(m.group(1))
            if not 1 <= n <= len(used):
                return ""
            h = used[n - 1]
            if h not in srcs:
                srcs.append(h)
            return f"[S{srcs.index(h) + 1}]"
        lines.append(f"Revision {rev} ({fn}): " + re.sub(r"\[S(\d+)\]", renum, text).replace("[Answer]", "").strip())
    out["found"] = True
    out["answer"] = "\n".join(lines)
    out["sources"] = [_src(h, i + 1) for i, h in enumerate(srcs)]
    out["warnings"].append(f"Answered separately for each revision of {fam}. "
                           "Check the ECN to see which revision is current.")
    return True


def _answer(question, top_k, out):
    question = (question or "").strip()
    if not question:
        out["error"] = 'Empty question. Usage: python ask.py "your question"'
        return
    try:
        res = _get_retriever().search(question, top_k)
        out["diagnostics"] = {"best_vec_sim": round(res["best_vec_sim"], 3), "best_bm25": round(res["best_bm25"], 2)}
        out["retrieved"] = [dict(_src(h), vec_sim=h["vec_sim"], bm25=h["bm25"]) for h in res["hits"]]
        if res["best_vec_sim"] < config.VEC_MIN_SIM and res["best_bm25"] < config.BM25_MIN:
            out["answer"] = NOT_FOUND                      # scores too low -> no LLM call
            return
        if _per_revision(question, res["hits"], out):
            return
        raw, used = generate_answer(question, res["hits"])
        out["context_revisions"] = _revision_warnings(used)
    except EmptyIndexError as e:
        out["error"] = str(e); return
    except requests.exceptions.ConnectionError:
        out["error"] = f"Cannot reach Ollama at {config.OLLAMA_URL}. Start it with: ollama serve"; return
    except requests.exceptions.Timeout:
        out["error"] = "Ollama timed out. Try a smaller model or fewer chunks."; return
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"; return

    text = raw.strip().replace("[Answer]", "").strip()
    valid = sorted({int(t) for t in re.findall(r"\[S(\d+)\]", text) if 1 <= int(t) <= len(used)})
    low = text.lower()
    plain = re.sub(r"\[S\d+\]", "", text)
    qtok = {t.lower().strip(".-") for t in re.findall(r"[\w.\-]+", question)}
    rest = " ".join(t for t in re.findall(r"[\w.\-]+", plain) if t.lower().strip(".-") not in qtok)
    negative = (re.search(r"not (mentioned|specified|stated|provided|found)|does not (mention|contain|specify|state)", plain, re.I)
                and not re.search(r"\d", rest))
    if not text or negative or low.startswith("not found in the documents") or ("not found in the documents" in low and not valid):
        out["answer"] = NOT_FOUND
        return
    out["found"] = True
    out["answer"] = re.sub(r"\[S(\d+)\]", lambda m: m.group(0) if 1 <= int(m.group(1)) <= len(used) else "", text)
    out["sources"] = [_src(used[t - 1], t) for t in valid]
    if not valid:
        out["warnings"].append("The model gave no valid citation. Verify against the retrieved chunks (--debug).")
    out["warnings"] += _revision_warnings([used[t - 1] for t in valid])
    cited_warn = set(out["warnings"])
    for w in out.get("context_revisions", []):
        if w not in cited_warn:
            out["warnings"].append(w + " The answer above may reflect only one revision; "
                                       "run with --debug to see all retrieved revisions.")


def answer_question(question, top_k=config.TOP_K):
    t0 = time.perf_counter()
    out = {"question": question, "found": False, "answer": "", "sources": [], "retrieved": [],
           "warnings": [], "diagnostics": {}, "error": None}
    _answer(question, top_k, out)
    out["seconds"] = round(time.perf_counter() - t0, 1)
    try:                                                   # traceability log (Day 2 task 8)
        config.DATA_DIR.mkdir(exist_ok=True)
        with open(config.DATA_DIR / "query_log.jsonl", "a", encoding="utf-8") as lf:
            lf.write(json.dumps({
                "time": datetime.datetime.now().isoformat(timespec="seconds"),
                "question": question, "model": config.CHAT_MODEL, "found": out["found"],
                "sources": [f"{s['file_name']} p{s['page_start']}" for s in out["sources"]],
                "seconds": out["seconds"]}, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return out


def _pages(s):
    return f"Page {s['page_start']}" if s["page_start"] == s["page_end"] else f"Pages {s['page_start']}-{s['page_end']}"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Ask questions about your engineering documents")
    ap.add_argument("question", nargs="*")
    ap.add_argument("--top-k", type=int, default=config.TOP_K)
    ap.add_argument("--debug", action="store_true", help="show retrieval scores and retrieved chunks")
    a = ap.parse_args()
    r = answer_question(" ".join(a.question), a.top_k)
    if r["error"]:
        print("Error:", r["error"]); return 1
    print(f"\nQuestion: {r['question']}\n\nAnswer: {r['answer']}")
    if r["sources"]:
        print("\nSources:")
        for s in r["sources"]:
            print(f"  [S{s['tag']}] {s['file_name']}, {_pages(s)} "
                  f"(Section {s['section'] or 'n/a'}, Revision {s['revision']}, Marking {s['marking']})")
    for w in r["warnings"]:
        print(f"\nWARNING: {w}")
    if a.debug:
        print(f"\n[debug] {r['diagnostics']} | {r['seconds']}s")
        for h in r["retrieved"]:
            print(f"  {h['file_name']} p{h['page_start']} sec={h['section']} vec={h['vec_sim'] or 0:.2f} bm25={h['bm25'] or 0:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())