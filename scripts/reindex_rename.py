import json
from src import config, vector_store
from src.chunker import chunk_document
from src.document_loader import file_sha256, load_document

OLD = "real/ASSIST_DLA/AC1BEAE2630A48ADB5332F6CF8EA2881--2.pdf"
NEW = "real/ASSIST_DLA/MIL-STD-882E.pdf"

reg = json.loads(config.HASH_FILE.read_text("utf-8"))
vector_store.delete_source(OLD)
reg.pop(OLD, None)
for f in config.CHUNK_DIR.glob("AC1BEAE2*"):
    f.unlink()

path = config.DOCS_DIR / NEW
h = file_sha256(path)
pages = load_document(path)
chunks = chunk_document(pages, NEW, h)
(config.CHUNK_DIR / f"MIL-STD-882E_{h[:8]}.json").write_text(
    json.dumps([c.model_dump() for c in chunks], indent=1, ensure_ascii=False), "utf-8")
vector_store.add_chunks(chunks)
reg[NEW] = {"sha256": h, "pages": len(pages), "chunks": len(chunks), "ocr_pages": 0}
config.HASH_FILE.write_text(json.dumps(reg, indent=1), "utf-8")
print("done:", len(chunks), "chunks, total in index:", vector_store.count())