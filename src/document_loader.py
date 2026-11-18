import hashlib, io, shutil
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image

from src import config

try:
    import pytesseract
    _cmd = config.TESSERACT_CMD if Path(config.TESSERACT_CMD).exists() else shutil.which("tesseract")
    if _cmd:
        pytesseract.pytesseract.tesseract_cmd = _cmd
    _OCR_OK = bool(_cmd)
except ImportError:
    _OCR_OK = False


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def table_to_markdown(rows) -> str:
    lines = []
    for r in rows:
        cells = [(c or "").replace("\n", " ").strip() for c in r]
        if any(cells):
            lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _pdf_page_text(page) -> str:
    """Reading-order text; tables are emitted as '| a | b |' rows at their position."""
    try:
        tables = page.find_tables().tables
    except Exception:
        tables = []
    if not tables:
        return page.get_text("text", sort=True)
    items = []
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, txt, _, btype = b[:7]
        if btype != 0:
            continue
        center = fitz.Point((x0 + x1) / 2, (y0 + y1) / 2)
        if any(fitz.Rect(t.bbox).contains(center) for t in tables):
            continue                               # text belongs to a table
        items.append((y0, txt.strip()))
    for t in tables:
        items.append((t.bbox[1], table_to_markdown(t.extract())))
    items.sort(key=lambda x: x[0])
    return "\n".join(t for _, t in items if t)


def _ocr_page(page) -> str:
    pix = page.get_pixmap(dpi=config.OCR_DPI)
    return pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))))


def load_pdf(path: Path, ocr=True, force_ocr=False):
    pages = []
    with fitz.open(path) as doc:
        if doc.needs_pass:
            raise ValueError("PDF is password protected")
        for i, page in enumerate(doc, start=1):
            text = "" if force_ocr else _pdf_page_text(page)
            used_ocr = False
            if len(text.strip()) < config.MIN_TEXT_CHARS and ocr:
                if _OCR_OK:
                    print(f"    [OCR] {path.name} page {i}")
                    text, used_ocr = _ocr_page(page), True
                else:
                    print(f"    [WARN] page {i} needs OCR but Tesseract is not available")
            pages.append({"page": i, "text": text, "ocr": used_ocr})
    return pages


def load_docx(path: Path):
    doc = Document(path)
    header = " ".join(p.text.strip() for s in doc.sections for p in s.header.paragraphs if p.text.strip())
    pages = [[header] if header else []]
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[1]
        if tag == "p":
            para = Paragraph(child, doc)
            if para.text.strip():
                pages[-1].append(para.text.strip())
            if 'w:type="page"' in child.xml:          # explicit page break
                pages.append([])
        elif tag == "tbl":
            rows = [[c.text for c in r.cells] for r in Table(child, doc).rows]
            pages[-1].append(table_to_markdown(rows))
    return [{"page": i, "text": "\n".join(p), "ocr": False} for i, p in enumerate(pages, 1) if p]


def load_document(path: Path, ocr=True, force_ocr=False):
    ext = path.suffix.lower()
    if ext == ".pdf":
        return load_pdf(path, ocr, force_ocr)
    if ext == ".docx":
        return load_docx(path)
    raise ValueError(f"Unsupported file type: {ext}")