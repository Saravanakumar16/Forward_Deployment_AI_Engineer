"""Permission-aware retrieval. RLS filters chunks inside PostgreSQL before ranking.

    python search.py --user priya --question "How does a Deployment manage replicas?"
    python search.py --user arjun --question "..." --strategy recursive --k 8

DEMO ONLY: --user simulates an identity that a trusted backend would take from a
verified token (OIDC/SAML session). End users never receive database credentials.
"""
import argparse
from common import connect, embed_query, set_identity, DEFAULT_STRATEGY, STRATEGIES

DEMO_USERS = ("priya", "arjun", "meena", "divya")

QUERY = """
SELECT c.document_id, d.title, c.heading_path, d.source_url, d.github_url, d.classification,
       c.chunk_no, c.chunk_text, round((c.embedding <=> %(v)s::vector)::numeric, 4) AS distance
FROM raglab.chunks c
JOIN raglab.documents d USING (document_id)          -- documents is RLS-protected as well
WHERE c.strategy = %(strategy)s
ORDER BY c.embedding <=> %(v)s::vector                -- cosine distance (pgvector <=>)
LIMIT %(k)s"""
COLS = ("document_id", "title", "heading_path", "source_url", "github_url", "classification",
        "chunk_no", "chunk_text", "distance")


def run_search(user_id, question, k=5, strategy=DEFAULT_STRATEGY, vector=None):
    """Return the top-k chunks the identity is authorized to read. Unknown ids simply get nothing."""
    vector = vector if vector is not None else embed_query(question)
    with connect() as db, db.transaction():   # restricted role; identity lives for this transaction only
        set_identity(db, user_id.lower())
        rows = db.execute(QUERY, {"v": vector, "strategy": strategy, "k": k}).fetchall()
    return [dict(zip(COLS, r)) for r in rows]


def print_results(user_id, question, results, strategy):
    print(f"IDENTITY={user_id} | STRATEGY={strategy} | QUESTION={question!r} | authorized results={len(results)}")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['document_id']:9} d={r['distance']}  {r['heading_path']}")
        print(f"     {r['source_url']}")
        print(f"     {' '.join(r['chunk_text'].split())[:150]!r}")
    if not results:
        print("  No authorized matching chunks.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--user", required=True, choices=DEMO_USERS)
    p.add_argument("--question", required=True)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--strategy", default=DEFAULT_STRATEGY, choices=STRATEGIES)
    a = p.parse_args()
    print_results(a.user, a.question, run_search(a.user, a.question, a.k, a.strategy), a.strategy)
