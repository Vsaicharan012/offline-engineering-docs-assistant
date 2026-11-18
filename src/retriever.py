from collections import defaultdict

from src import config, vector_store
from src.bm25_index import BM25Index
from src.embeddings import embed_texts
import re
from pathlib import Path


def family_of(file_name: str) -> str:
    """EQ-SPEC-1001_RevB.pdf -> EQ-SPEC-1001"""
    return re.sub(r"[_\-\s]?rev[_\-\s]?[A-Z0-9]{1,2}(?=[_\-\s]|$)", "", Path(file_name).stem, flags=re.I)

class EmptyIndexError(RuntimeError):
    pass


class HybridRetriever:
    def __init__(self):
        self.col = vector_store.get_collection()
        data = self.col.get(include=["documents", "metadatas"])
        if not data["ids"]:
            raise EmptyIndexError("The index is empty. Run: python ingestion.py")
        self.ids = data["ids"]
        self.docs = dict(zip(data["ids"], data["documents"]))
        self.metas = dict(zip(data["ids"], data["metadatas"]))
        self.bm25 = BM25Index(data["ids"], data["documents"], data["metadatas"])
        self.family_files = defaultdict(set)
        self.all_files = {m["file_name"] for m in data["metadatas"]}
        for m in data["metadatas"]:
            if m["revision"] != "N/A":
                self.family_files[family_of(m["file_name"])].add(m["file_name"])

    def search_file(self, query: str, file_name: str, n: int = 2):
        """Best chunks from ONE file (used for per-revision answering)."""
        qv = embed_texts([query], is_query=True)[0]
        r = self.col.query(query_embeddings=[qv], n_results=n,
                           where={"file_name": file_name}, include=["distances"])
        return [{"id": i, "text": self.docs[i], "meta": self.metas[i],
                 "vec_sim": 1.0 - d, "bm25": None, "rrf": 0.0}
                for i, d in zip(r["ids"][0], r["distances"][0])]

    
    def search(self, query: str, top_k: int = config.TOP_K):
        pool = min(config.POOL, len(self.ids))
        qv = embed_texts([query], is_query=True)[0]
        v = self.col.query(query_embeddings=[qv], n_results=pool, include=["distances"])
        vec = {i: 1.0 - d for i, d in zip(v["ids"][0], v["distances"][0])}      # cosine similarity
        bm = dict(self.bm25.search(query, pool))

        fused = defaultdict(float)
        for rank, i in enumerate(vec):                    # dict preserves best-first order
            fused[i] += 1.0 / (config.RRF_K + rank + 1)
        for rank, i in enumerate(bm):
            fused[i] += 1.0 / (config.RRF_K + rank + 1)
        # exact-term boost: a clearly strong BM25 match (e.g. a part number) should not be outvoted
        if bm:
            top_id, top_score = next(iter(bm.items()))
            if top_score >= config.BM25_MIN:
                fused[top_id] += 0.02

        hits = [{"id": i, "text": self.docs[i], "meta": self.metas[i],
                 "vec_sim": vec.get(i), "bm25": bm.get(i), "rrf": fused[i]}
                for i in sorted(fused, key=fused.get, reverse=True)[:top_k]]

        # if the question names a document ID (e.g. MM-3300), always include that document's best chunks
        q_low = query.lower()
        named = sorted(f for f in self.all_files if family_of(f).lower() in q_low)
        seen = {h["id"] for h in hits}
        front = []
        for fn in named:
            for h in self.search_file(query, fn, 2):
                if h["id"] not in seen:
                    front.append(h); seen.add(h["id"])
        hits = front + hits

        # revision expansion
        present = {h["meta"]["file_name"] for h in hits}
        wants_revs = re.search(r"\brev(ision)?s?\b|\bcompar|\bchang|\bdiffer|\blatest\b|\bcurrent\b", query, re.I)
        for fam in ({family_of(f) for f in present} if wants_revs else set()):
            for fn in sorted(self.family_files.get(fam, ())):
                if fn in present:
                    continue
                qv2 = embed_texts([re.sub(r"(?i)\brev(ision)?\s*[A-Z]?\b|\bEQ-SPEC-\d+\b|\band\b|\bin\b|\bof\b", " ", query)], is_query=True)[0]
                r = self.col.query(query_embeddings=[qv2], n_results=1,
                                   where={"file_name": fn}, include=["distances"])
                if r["ids"][0]:
                    i = r["ids"][0][0]
                    hits.append({"id": i, "text": self.docs[i], "meta": self.metas[i],
                                 "vec_sim": 1.0 - r["distances"][0][0], "bm25": bm.get(i), "rrf": 0.0})
                    present.add(fn)
        return {"hits": hits,
                "best_vec_sim": max(vec.values()) if vec else 0.0,
                "best_bm25": max(bm.values()) if bm else 0.0}

if __name__ == "__main__":                                 # quick retrieval test: python -m src.retriever "query"
    import sys
    q = " ".join(sys.argv[1:]) or "maximum operating temperature"
    res = HybridRetriever().search(q)
    print(f"best_vec_sim={res['best_vec_sim']:.3f}  best_bm25={res['best_bm25']:.2f}")
    for h in res["hits"]:
        m = h["meta"]
        print(f"rrf={h['rrf']:.4f} vec={h['vec_sim'] or 0:.2f} bm25={h['bm25'] or 0:.1f} | "
              f"{m['file_name']} p{m['page_start']} sec={m['section']} rev={m['revision']}")