"""OFFLINE TEST STAND-IN ONLY - not the submission model.

A 384-dimensional LSA (TF-IDF + truncated SVD) embedder fitted on the 30 documents.
It exists so the pipeline, RLS and revocation tests can run on a machine that cannot
download BAAI/bge-small-en-v1.5. Enable with EMBED_BACKEND=offline-lsa.
Results produced with it are clearly labelled and must not be reported as BGE results.
"""
from functools import lru_cache
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _model():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from preprocess import clean_markdown
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    paras = []
    for d in manifest["documents"]:
        _, _, text = clean_markdown((ROOT / "data/k8s-docs" / d["source_path"]).read_text(encoding="utf-8"))
        paras += [p for p in text.split("\n\n") if len(p.strip()) > 40]
    vec = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2, stop_words="english")
    X = vec.fit_transform(paras)
    svd = TruncatedSVD(n_components=384, random_state=7).fit(X)
    print(f"[offline-lsa] fitted stand-in embedder on {len(paras)} paragraphs (NOT BGE)")
    return vec, svd


def embed(texts):
    vec, svd = _model()
    Z = svd.transform(vec.transform(list(texts)))
    Z /= np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12
    return Z.tolist()
