from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "documents"
DATA_DIR = ROOT / "data"
CHUNK_DIR = DATA_DIR / "chunks"
HASH_FILE = DATA_DIR / "file_hashes.json"
VECTOR_DIR = ROOT / "vector_store"

OLLAMA_URL = "http://localhost:11434"
CHAT_MODEL = "llama3.2:3b"          # change to "qwen2.5:7b" if you have 16 GB+ RAM
EMBED_MODEL = "nomic-embed-text"
COLLECTION = "engineering_docs"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# extraction / chunking
MIN_TEXT_CHARS = 50        # PDF page with less text than this is treated as scanned -> OCR
OCR_DPI = 200
MAX_CHUNK_CHARS = 1800
MAX_TABLE_CHARS = 4000     # tables up to this size are never split

# retrieval
TOP_K = 6
POOL = 20                  # candidates taken from each retriever before fusion
RRF_K = 60
VEC_MIN_SIM = 0.55         # not-found gate: best cosine similarity...
BM25_MIN = 8.0             # ...or best BM25 score must reach one of these
MAX_CONTEXT_CHARS = 8000
NUM_CTX = 4096