"""Ingest the 30 Kubernetes documents: clean, chunk with all four strategies, embed, store with ACLs.

    python ingest.py                         # all strategies
    python ingest.py --strategies markdown   # only one (e.g. for a quick demo)
Re-running replaces the chunks and ACL rows of the same documents (idempotent).
"""
import argparse, hashlib, json, time
from pathlib import Path
from common import connect, embed, count_tokens, TENANT, STRATEGIES
from preprocess import clean_markdown
from chunkers import chunk_document

ROOT = Path(__file__).resolve().parent


def load_documents():
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    docs = []
    for d in manifest["documents"]:
        path = ROOT / "data/k8s-docs" / d["source_path"]
        if not path.exists():
            raise FileNotFoundError(f"{path} missing - run: python scripts/fetch_dataset.py")
        raw = path.read_text(encoding="utf-8")
        title, desc, text = clean_markdown(raw)
        docs.append({**d, "title": title, "description": desc, "text": text,
                     "file_name": Path(d["source_path"]).name,
                     "github_url": f"{manifest['repository']}/blob/{manifest['commit']}/{d['source_path']}",
                     "commit_sha": manifest["commit"], "license": manifest["license"],
                     "content_sha256": hashlib.sha256(raw.encode()).hexdigest()})
    if len(docs) != 30:
        raise ValueError(f"Expected 30 documents, found {len(docs)}")
    return docs


def build_chunks(docs, strategies):
    rows = []
    for s in strategies:
        t0 = time.monotonic()
        n = 0
        for d in docs:
            for no, c in enumerate(chunk_document(s, d["text"], d["title"], embed_fn=embed)):
                rows.append({"document_id": d["document_id"], "strategy": s, "chunk_no": no,
                             "heading_path": c.heading_path, "chunk_text": c.text,
                             "embed_text": c.embed_text, "start_char": c.start})
                n += 1
        print(f"  {s:9} {n:5} chunks  ({time.monotonic() - t0:.1f}s)")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategies", nargs="+", default=list(STRATEGIES), choices=STRATEGIES)
    a = ap.parse_args()
    started = time.monotonic()
    docs = load_documents()
    print(f"Loaded {len(docs)} documents ({sum(len(d['text']) for d in docs):,} cleaned chars). Chunking:")
    rows = build_chunks(docs, a.strategies)
    print(f"Embedding {len(rows)} chunks with the passage encoder ...")
    texts = [r["embed_text"] for r in rows]
    vectors = []
    for i in range(0, len(texts), 256):
        vectors += embed(texts[i:i + 256])
        print(f"  embedded {len(vectors)}/{len(texts)}")
    tokens = count_tokens(texts)

    with connect(admin=True) as db, db.transaction():
        for d in docs:
            db.execute("""INSERT INTO raglab.documents (document_id, tenant_id, category, classification, title,
                              description, file_name, source_path, source_url, github_url, commit_sha, license,
                              content_sha256, char_count)
                          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                          ON CONFLICT (document_id) DO UPDATE SET tenant_id=excluded.tenant_id,
                              category=excluded.category, classification=excluded.classification,
                              title=excluded.title, description=excluded.description, file_name=excluded.file_name,
                              source_path=excluded.source_path, source_url=excluded.source_url,
                              github_url=excluded.github_url, commit_sha=excluded.commit_sha,
                              license=excluded.license, content_sha256=excluded.content_sha256,
                              char_count=excluded.char_count, ingested_at=now()""",
                       (d["document_id"], TENANT, d["category"], d["classification"], d["title"],
                        d["description"], d["file_name"], d["source_path"], d["source_url"], d["github_url"],
                        d["commit_sha"], d["license"], d["content_sha256"], len(d["text"])))
            db.execute("DELETE FROM raglab.document_acl WHERE document_id=%s", (d["document_id"],))
            for g in d["permitted_groups"]:
                db.execute("INSERT INTO raglab.document_acl(document_id, group_name) VALUES (%s,%s)",
                           (d["document_id"], g))
            db.execute("DELETE FROM raglab.chunks WHERE document_id=%s AND strategy = ANY(%s)",
                       (d["document_id"], a.strategies))
        with db.cursor() as cur:
            cur.executemany("""INSERT INTO raglab.chunks (document_id, tenant_id, strategy, chunk_no, heading_path,
                                   chunk_text, embed_text, start_char, char_count, token_count, embedding)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            [(r["document_id"], TENANT, r["strategy"], r["chunk_no"], r["heading_path"],
                              r["chunk_text"], r["embed_text"], r["start_char"], len(r["chunk_text"]), t, v)
                             for r, t, v in zip(rows, tokens, vectors)])
    print(f"Finished: {len(docs)} documents, {len(rows)} chunks in {time.monotonic() - started:.0f}s")
    print('Next: python search.py --user priya --question "How does a Kubernetes Deployment manage application replicas?"')


if __name__ == "__main__":
    main()
