import re
from rank_bm25 import BM25Okapi
from src.models import context_header

_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-/][a-z0-9]+)*")
_STOP = set("a an the of to in on for and or is are was were be by with at as from that this what which who "
            "how does do did it its than then there into per shall".split())


def tokenize(text: str):
    toks = []
    for t in _TOKEN.findall(text.lower()):
        if t in _STOP:
            continue
        toks.append(t)
        if re.search(r"[.\-/]", t):                       # also index the parts: 7741-0032 -> 7741, 0032
            toks.extend(p for p in re.split(r"[.\-/]", t) if p and p not in _STOP)
    return toks


class BM25Index:
    def __init__(self, ids, docs, metas):
        self.ids = ids
        self.bm25 = BM25Okapi([tokenize(context_header(m) + "\n" + d) for d, m in zip(docs, metas)])

    def search(self, query: str, n: int):
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:n]
        return [(self.ids[i], float(scores[i])) for i in order if scores[i] > 0]