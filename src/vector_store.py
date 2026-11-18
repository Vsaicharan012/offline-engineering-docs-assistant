import chromadb
from chromadb.config import Settings
from tqdm import tqdm

from src import config
from src.embeddings import embed_texts
from src.models import Chunk, context_header

_client = chromadb.PersistentClient(path=str(config.VECTOR_DIR), settings=Settings(anonymized_telemetry=False))


def get_collection():
    return _client.get_or_create_collection(config.COLLECTION, metadata={"hnsw:space": "cosine"})


def reset():
    try:
        _client.delete_collection(config.COLLECTION)
    except Exception:
        pass


def delete_source(source_path: str):
    get_collection().delete(where={"source_path": source_path})


def add_chunks(chunks: list[Chunk], batch=32) -> int:
    col = get_collection()
    for i in tqdm(range(0, len(chunks), batch), desc="    embedding", leave=False):
        b = chunks[i:i + batch]
        vecs = embed_texts([context_header(c.meta()) + "\n" + c.text for c in b])
        col.upsert(ids=[c.chunk_id for c in b], embeddings=vecs,
                   documents=[c.text for c in b], metadatas=[c.meta() for c in b])
    return len(chunks)


def count() -> int:
    return get_collection().count()