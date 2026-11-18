import re
from pathlib import Path

from src import config
from src.models import Chunk

HEAD_RE = re.compile(r"^((?:METHOD\s+)?\d+(?:\.\d+){0,4})\.?\s+([A-Z][A-Za-z0-9 ,;:/&()\-]{2,90})$")
REQ_WORDS = re.compile(r"\b(shall|should|will|must|may)\b", re.I)
MARK_RE = re.compile(r"^\W*(TOP SECRET|SECRET|CONFIDENTIAL|RESTRICTED|CUI|UNCLASSIFIED(?://FOUO)?)\W*$", re.M)
REV_RE = re.compile(r"^\s*(?:Revision|REVISION|Rev\.?|REV\.?)\s*[:\-]?\s*([A-Z]{1,2})\s*$", re.M)


def parse_heading(line: str):
    if len(line) > 100 or line.endswith(".") or "...." in line:
        return None
    m = HEAD_RE.match(line)
    if not m:
        return None
    title = m.group(2)
    if REQ_WORDS.search(title) or len(title.split()) > 10:
        return None
    return m.group(1), title


def extract_doc_metadata(pages, filename: str):
    first = pages[0]["text"][:1500] if pages else ""
    m = MARK_RE.search(first)
    marking = m.group(1).upper() if m else "UNMARKED"
    r = REV_RE.search(first)
    revision = r.group(1) if r else ""
    if not revision:
        f = (re.search(r"MIL-(?:STD|HDBK)-\d+([A-Z])\b", filename, re.I)
             or re.search(r"(?:^|[_\-\s])Rev[_\-\s]?([A-Z0-9]{1,2})(?=[_\-\s.]|$)", filename, re.I))
        revision = f.group(1).upper() if f else "N/A"
    return {"marking": marking, "revision": revision}


def _flush(segs, kind, buf, page, ocr):
    if buf:
        segs.append({"page": page, "kind": kind, "text": "\n".join(buf), "ocr": ocr})
        buf.clear()


def segment_pages(pages):
    """Pages -> ordered segments: heading | text | table (each tagged with its page)."""
    segs = []
    for p in pages:
        pg, ocr, text_buf, tbl_buf = p["page"], p["ocr"], [], []
        for line in p["text"].splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("|"):
                _flush(segs, "text", text_buf, pg, ocr)
                tbl_buf.append(s)
                continue
            _flush(segs, "table", tbl_buf, pg, ocr)
            h = parse_heading(s)
            if h:
                _flush(segs, "text", text_buf, pg, ocr)
                segs.append({"page": pg, "kind": "heading", "text": s, "num": h[0], "title": h[1], "ocr": ocr})
            else:
                text_buf.append(s)
        _flush(segs, "text", text_buf, pg, ocr)
        _flush(segs, "table", tbl_buf, pg, ocr)
    return segs


def _split_piece(text, kind):
    limit = config.MAX_TABLE_CHARS if kind == "table" else config.MAX_CHUNK_CHARS
    if len(text) <= limit:
        return [text]
    lines = text.split("\n")
    header = lines[0] if kind == "table" else None      # repeat table header row in every piece
    out, cur, size = [], [], 0
    for ln in (lines[1:] if header else lines):
        if cur and size + len(ln) + 1 > limit:
            out.append("\n".join(([header] if header else []) + cur)); cur, size = [], 0
        cur.append(ln); size += len(ln) + 1
    if cur:
        out.append("\n".join(([header] if header else []) + cur))
    return out


class _Acc:
    def __init__(self): self.reset()
    def reset(self):
        self.parts, self.pages = [], set()
        self.body = self.table = self.ocr = False
        self.size, self.section = 0, ("", "")


def chunk_document(pages, source_path: str, doc_hash: str):
    name = Path(source_path).name
    meta = extract_doc_metadata(pages, name)
    chunks, acc, cur_sec = [], _Acc(), ("", "")

    def emit():
        if acc.body:
            chunks.append(Chunk(
                chunk_id=f"{doc_hash[:10]}_{len(chunks):04d}", text="\n".join(acc.parts),
                source_path=source_path, file_name=name,
                page_start=min(acc.pages), page_end=max(acc.pages),
                section=acc.section[0], section_title=acc.section[1],
                is_table=acc.table, ocr=acc.ocr, doc_hash=doc_hash, **meta))
        acc.reset()

    for seg in segment_pages(pages):
        if seg["kind"] == "heading":
            if acc.body:
                emit()
            cur_sec = (seg["num"], seg["title"])
            acc.section = cur_sec
            acc.parts.append(seg["text"]); acc.pages.add(seg["page"])
            continue
        for piece in _split_piece(seg["text"], seg["kind"]):
            if acc.body and acc.size + len(piece) > config.MAX_CHUNK_CHARS:
                emit()
            if not acc.parts:
                acc.section = cur_sec
            acc.parts.append(piece); acc.pages.add(seg["page"])
            acc.body, acc.size = True, acc.size + len(piece)
            acc.table |= seg["kind"] == "table"
            acc.ocr |= seg["ocr"]
    emit()
    return chunks