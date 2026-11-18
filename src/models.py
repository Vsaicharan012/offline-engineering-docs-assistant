from pydantic import BaseModel

class Chunk(BaseModel):
    chunk_id: str
    text: str
    source_path: str          # relative to documents/, e.g. "synthetic/MM-3300_RevA.pdf"
    file_name: str            # base name, used in citations
    page_start: int
    page_end: int
    section: str = ""
    section_title: str = ""
    revision: str = "N/A"
    marking: str = "UNMARKED"
    is_table: bool = False
    ocr: bool = False
    doc_hash: str

    def meta(self) -> dict:                 # what is stored in ChromaDB next to the text
        return self.model_dump(exclude={"text"})

def context_header(meta: dict) -> str:
    """Prepended to chunk text for embedding and BM25 so file/revision/section are searchable."""
    return f"Document: {meta['file_name']} | Revision: {meta['revision']} | Section: {meta['section']} {meta['section_title']}".strip()