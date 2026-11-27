"""Exercise D - same question, different identities, different (authorized) results.

For each test question it records, per identity: rank, document ID, heading, source link,
cosine distance and whether the result was authorized. Authorization is re-checked by an
independent oracle (users.json x manifest.json, computed in Python, not by the database),
so a bug in the RLS policy would show up as "NO" here.

It also shows the unrestricted top-k (admin, never exposed to users) so you can see which
highly relevant documents were withheld from each identity.

Writes results/exercise_d.md and results/exercise_d.json.
"""
import json
from pathlib import Path
from common import connect, embed_query, DEFAULT_STRATEGY, EMBEDDER_LABEL
from search import run_search, DEMO_USERS

ROOT = Path(__file__).resolve().parent
K = 5
QUESTIONS = [
    ("How does a Kubernetes Deployment manage application replicas?", "Application Engineering"),
    ("What are PersistentVolumes and PersistentVolumeClaims?", "Platform Engineering"),
    ("What are recommended Kubernetes RBAC practices?", "Security Engineering"),
    ("What are the main Kubernetes components?", "Shared knowledge"),
]


def oracle():
    users = {u["user_id"]: set(u["groups"]) for u in json.loads((ROOT / "data/users.json").read_text(encoding="utf-8"))["users"]}
    acl = {d["document_id"]: set(d["permitted_groups"])
           for d in json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))["documents"]}
    return lambda user, doc: bool(users.get(user, set()) & acl.get(doc, set()))


def unrestricted(vector, strategy):
    with connect(admin=True) as db:
        return db.execute("""SELECT c.document_id, d.classification, round((c.embedding <=> %s::vector)::numeric,4)
                             FROM raglab.chunks c JOIN raglab.documents d USING (document_id)
                             WHERE c.strategy=%s ORDER BY c.embedding <=> %s::vector LIMIT %s""",
                          (vector, strategy, vector, K)).fetchall()


def main():
    allowed = oracle()
    out, md = [], [f"# Exercise D - Same question, different results\n",
                   f"Strategy: **{DEFAULT_STRATEGY}** | embedder: **{EMBEDDER_LABEL}** | top-{K} | "
                   "distance = pgvector cosine distance (`<=>`, lower is closer)\n",
                   "`Authorized` is verified by an independent oracle (users.json x manifest.json), not by the database.\n"]
    violations = 0
    for q, area in QUESTIONS:
        v = embed_query(q)
        ref = unrestricted(v, DEFAULT_STRATEGY)
        ref_docs = list(dict.fromkeys(r[0] for r in ref))
        md += [f"\n## {q}\n", f"Primary knowledge area: **{area}**  ",
               f"Unrestricted top-{K} (admin reference, never shown to users): "
               + ", ".join(f"{d} ({c})" for d, c, _ in ref) + "\n"]
        entry = {"question": q, "area": area, "unrestricted_top": [[d, c, float(x)] for d, c, x in ref], "by_user": {}}
        for user in DEMO_USERS:
            res = run_search(user, q, K, DEFAULT_STRATEGY, vector=v)
            got = [r["document_id"] for r in res]
            withheld = [d for d in ref_docs if d not in got and not allowed(user, d)]
            md += [f"\n**{user.title()}** - {len(res)} authorized results"
                   + (f"; withheld by RLS: {', '.join(withheld)}" if withheld else "") + "\n",
                   "| # | Document | Section | Source | Distance | Authorized |", "|---|---|---|---|---|---|"]
            rows = []
            for i, r in enumerate(res, 1):
                ok = allowed(user, r["document_id"])
                violations += not ok
                md.append(f"| {i} | {r['document_id']} | {r['heading_path']} | [{r['source_url'].split('/docs/')[1]}]"
                          f"({r['source_url']}) | {r['distance']} | {'YES' if ok else '**NO - VIOLATION**'} |")
                rows.append({"rank": i, "document_id": r["document_id"], "heading": r["heading_path"],
                             "source_url": r["source_url"], "distance": float(r["distance"]), "authorized": ok})
            entry["by_user"][user] = {"results": rows, "withheld_relevant_docs": withheld}
            print(f"{user:6} {q[:55]:55} -> {', '.join(got)}" + (f"   [withheld: {', '.join(withheld)}]" if withheld else ""))
        out.append(entry)
    md.append(f"\n**Authorization violations across all {len(QUESTIONS) * len(DEMO_USERS)} searches: {violations}**\n")
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/exercise_d.md").write_text("\n".join(md), encoding="utf-8")
    (ROOT / "results/exercise_d.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Authorization violations: {violations}. Wrote results/exercise_d.md")
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
