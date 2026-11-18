import argparse, json, sys

from src import config, vector_store
from src.chunker import chunk_document
from src.document_loader import file_sha256, load_document


def main():
    ap = argparse.ArgumentParser(description="Ingest PDFs/DOCX into the search index")
    ap.add_argument("--reset", action="store_true", help="wipe the index and re-ingest everything")
    ap.add_argument("--no-ocr", action="store_true", help="disable OCR fallback")
    ap.add_argument("--force-ocr", metavar="SUBSTR", help="OCR every PDF whose filename contains SUBSTR")
    a = ap.parse_args()

    config.CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    if a.reset:
        vector_store.reset(); registry = {}
        for f in config.CHUNK_DIR.glob("*.json"):
            f.unlink()
    else:
        registry = json.loads(config.HASH_FILE.read_text("utf-8")) if config.HASH_FILE.exists() else {}

    files = sorted(p for p in config.DOCS_DIR.rglob("*")
                   if p.suffix.lower() in (".pdf", ".docx") and not p.name.startswith("~$"))
    if not files:
        sys.exit(f"No PDF/DOCX files found under {config.DOCS_DIR}")

    known = {v["sha256"] for v in registry.values()}
    stats = {"new": 0, "skipped": 0, "failed": 0}
    for path in files:
        rel = path.relative_to(config.DOCS_DIR).as_posix()
        h = file_sha256(path)
        if rel in registry and registry[rel]["sha256"] == h:
            print(f"[skip]      {rel} (unchanged)"); stats["skipped"] += 1; continue
        if rel not in registry and h in known:
            print(f"[skip]      {rel} (duplicate content)"); stats["skipped"] += 1; continue
        print(f"[ingesting] {rel}")
        try:
            if rel in registry:
                vector_store.delete_source(rel)            # file changed -> drop stale chunks
            force = bool(a.force_ocr) and a.force_ocr.lower() in path.name.lower()
            pages = load_document(path, ocr=not a.no_ocr, force_ocr=force)
            chunks = chunk_document(pages, rel, h)
            if not chunks:
                raise ValueError("no text extracted (scanned file and OCR unavailable?)")
            (config.CHUNK_DIR / f"{path.stem}_{h[:8]}.json").write_text(
                json.dumps([c.model_dump() for c in chunks], indent=1, ensure_ascii=False), "utf-8")
            vector_store.add_chunks(chunks)
            registry[rel] = {"sha256": h, "pages": len(pages), "chunks": len(chunks),
                             "ocr_pages": sum(p["ocr"] for p in pages)}
            known.add(h)
            config.HASH_FILE.write_text(json.dumps(registry, indent=1), "utf-8")
            print(f"            {len(pages)} pages -> {len(chunks)} chunks (OCR pages: {registry[rel]['ocr_pages']})")
            stats["new"] += 1
        except Exception as e:
            print(f"[FAILED]    {rel}: {type(e).__name__}: {e}"); stats["failed"] += 1
    print(f"\nDone: {stats} | total chunks in index: {vector_store.count()}")


if __name__ == "__main__":
    main()