import requests
from src import config


def embed_texts(texts, is_query=False, batch=16):
    prefix = "search_query: " if is_query else "search_document: "
    out = []
    for i in range(0, len(texts), batch):
        r = requests.post(f"{config.OLLAMA_URL}/api/embed", timeout=300,
                          json={"model": config.EMBED_MODEL, "input": [prefix + t for t in texts[i:i + batch]]})
        r.raise_for_status()
        out.extend(r.json()["embeddings"])
    return out