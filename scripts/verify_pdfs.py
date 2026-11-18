# scripts/verify_pdfs.py   (run from project root)
from pathlib import Path
import fitz
for p in sorted(Path("documents").rglob("*.pdf")):
    with p.open("rb") as f:
        head = f.read(5)
    if head != b"%PDF-":
        print(f"BAD  {p.name}: not a PDF (probably an HTML page saved as .pdf)"); continue
    try:
        with fitz.open(p) as d:
            chars = sum(len(pg.get_text()) for pg in d)
            kind = "scanned? (OCR needed)" if chars < 50 * len(d) else "text OK"
            print(f"OK   {p.name}: {len(d)} pages, {chars} chars, {kind}")
    except Exception as e:
        print(f"BAD  {p.name}: {e}")