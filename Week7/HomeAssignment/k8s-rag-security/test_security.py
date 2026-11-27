"""Exercise E - negative tests, revocation and hardening of the retrieval role.

Every check runs through the RESTRICTED retrieval role (RLS applies). The admin connection
is only used to (1) revoke/restore a membership, as an identity provider sync would, and
(2) fingerprint the chunk table to prove nothing was re-embedded or re-ingested.

Output is printed and also saved to results/exercise_e_security_tests.txt as evidence.
Revoked memberships are always restored in a finally block.
"""
import sys, time
from datetime import datetime
from pathlib import Path
import psycopg
from common import connect, set_identity, embed_query, TENANT, DEFAULT_STRATEGY, EMBEDDER_LABEL
from search import run_search

ROOT = Path(__file__).resolve().parent
LOG = []
FAILS = 0
TARGET = "SEC-01"   # Role Based Access Control Good Practices - restricted to SECURITY_ENG
QUESTION = "What are recommended Kubernetes RBAC practices?"


def log(line=""):
    print(line); LOG.append(line)


def check(label, actual, expected, detail=""):
    global FAILS
    ok = actual == expected
    FAILS += not ok
    log(f"{'PASS' if ok else 'FAIL'}  {label} => {actual}" + (f"   ({detail})" if detail else ""))


def visible_chunks(user, doc, tenant=TENANT):
    """How many chunks of `doc` the identity can see through RLS (all strategies)."""
    with connect() as db, db.transaction():
        if user is not None:
            db.execute("SELECT set_config('app.user_id', %s, true)", (user,))
        if tenant is not None:
            db.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
        return db.execute("SELECT count(*) FROM raglab.chunks WHERE document_id=%s", (doc,)).fetchone()[0]


def visible_title(user, doc):
    with connect() as db, db.transaction():
        set_identity(db, user)
        r = db.execute("SELECT title FROM raglab.documents WHERE document_id=%s", (doc,)).fetchone()
        return r[0] if r else None


def top_docs(user, vec):
    return [r["document_id"] for r in run_search(user, QUESTION, 5, DEFAULT_STRATEGY, vector=vec)]


def fingerprint():
    with connect(admin=True) as db:
        return db.execute("""SELECT count(*), max(chunk_id),
                                    md5(string_agg(embedding::text, ',' ORDER BY chunk_id))
                             FROM raglab.chunks""").fetchone()


def admin(sql_text, params=()):
    with connect(admin=True) as db:
        db.execute(sql_text, params); db.commit()


def denied(sql_text, user="meena"):
    """Run a statement as the restricted role; return the error class name if refused."""
    try:
        with connect() as db, db.transaction():
            set_identity(db, user)
            db.execute(sql_text)
            return "ALLOWED"
    except psycopg.Error as e:
        return type(e).__name__


def main():
    log(f"# Exercise E evidence - {datetime.now().isoformat(timespec='seconds')}")
    log(f"# strategy={DEFAULT_STRATEGY} embedder={EMBEDDER_LABEL} target={TARGET} question={QUESTION!r}")
    vec = embed_query(QUESTION)

    log("\n## 1. Authorized vs unauthorized access to the same restricted document")
    check(f"Meena (SECURITY_ENG) retrieves {TARGET} in top-5", TARGET in top_docs("meena", vec), True, ", ".join(top_docs("meena", vec)))
    check(f"Divya (APP_ENG+SECURITY_ENG) retrieves {TARGET} in top-5", TARGET in top_docs("divya", vec), True)
    check(f"Arjun (PLATFORM_ENG) gets no SEC-* chunk in top-5", any(d.startswith("SEC-") for d in top_docs("arjun", vec)), False, ", ".join(top_docs("arjun", vec)))
    check(f"Priya (APP_ENG) gets no SEC-* chunk in top-5", any(d.startswith("SEC-") for d in top_docs("priya", vec)), False)
    check(f"Arjun direct SELECT on {TARGET} chunks returns 0 rows", visible_chunks("arjun", TARGET), 0)
    check(f"Arjun cannot even see the title of {TARGET}", visible_title("arjun", TARGET), None)
    check(f"Meena sees {TARGET} title", visible_title("meena", TARGET), "Role Based Access Control Good Practices")
    check("Priya blocked from PLAT-01 (storage)", visible_chunks("priya", "PLAT-01"), 0)
    check("Arjun reads PLAT-01 (storage)", visible_chunks("arjun", "PLAT-01") > 0, True)
    check("Meena blocked from APP-01 (workloads)", visible_chunks("meena", "APP-01"), 0)
    for u in ("priya", "arjun", "meena", "divya"):
        check(f"{u.title()} reads SHARED-02 (all employees)", visible_chunks(u, "SHARED-02") > 0, True)

    log("\n## 2. Unknown, missing and forged identity context")
    check("Unknown identity 'mallory' sees 0 restricted chunks", visible_chunks("mallory", TARGET), 0)
    check("Unknown identity 'mallory' sees 0 shared chunks", visible_chunks("mallory", "SHARED-02"), 0)
    check("No app.user_id set -> 0 chunks", visible_chunks(None, "SHARED-02"), 0)
    check("Empty app.user_id -> 0 chunks", visible_chunks("", "SHARED-02"), 0)
    check("Valid user but no tenant set -> 0 chunks", visible_chunks("meena", TARGET, tenant=None), 0)
    check("Valid user with wrong tenant -> 0 chunks", visible_chunks("meena", TARGET, tenant="OTHER_TENANT"), 0)
    check("Unknown identity search returns nothing", len(run_search("mallory", QUESTION, 5, vector=vec)), 0)
    with connect() as db:          # one pooled connection, two requests
        with db.transaction():
            set_identity(db, "meena")
            first = db.execute("SELECT count(*) FROM raglab.chunks WHERE document_id=%s", (TARGET,)).fetchone()[0]
        with db.transaction():     # next request on the same connection forgets to set identity
            second = db.execute("SELECT count(*) FROM raglab.chunks WHERE document_id=%s", (TARGET,)).fetchone()[0]
    check("Identity does not leak to the next transaction on a pooled connection", (first > 0, second), (True, 0))

    log("\n## 3. Revocation takes effect immediately, without re-embedding or re-ingesting")
    before = fingerprint()
    log(f"INFO  chunk table fingerprint before: rows={before[0]} max_id={before[1]} md5(embeddings)={before[2]}")
    try:
        t0 = time.perf_counter()
        admin("DELETE FROM raglab.user_groups WHERE user_id='meena' AND group_name='SECURITY_ENG'")
        n = visible_chunks("meena", TARGET)
        ms = (time.perf_counter() - t0) * 1000
        check(f"Meena sees 0 {TARGET} chunks right after revocation", n, 0, f"revoke + query in {ms:.0f} ms")
        docs = top_docs("meena", vec)
        check("Meena's RBAC search now returns no SEC-* chunk", any(d.startswith("SEC-") for d in docs), False, ", ".join(docs))
        check("Meena still reads shared SHARED-02 (ALL_EMPLOYEES kept)", visible_chunks("meena", "SHARED-02") > 0, True)
        check("Divya (other SECURITY_ENG member) unaffected", visible_chunks("divya", TARGET) > 0, True)
        after = fingerprint()
        check("Chunk table unchanged (no re-embedding / re-ingestion)", after, before)
    finally:
        admin("INSERT INTO raglab.user_groups(user_id, group_name) VALUES ('meena','SECURITY_ENG') ON CONFLICT DO NOTHING")
        log("INFO  membership meena -> SECURITY_ENG restored")

    log("\n## 4. Restoring the legitimate membership restores access")
    check(f"Meena sees {TARGET} chunks again", visible_chunks("meena", TARGET) > 0, True)
    check(f"Meena's RBAC search returns {TARGET} again", TARGET in top_docs("meena", vec), True)

    log("\n## 5. Deactivating an identity (leaver) removes all access, including shared")
    try:
        admin("UPDATE raglab.app_users SET is_active=false WHERE user_id='arjun'")
        check("Deactivated Arjun sees 0 shared chunks", visible_chunks("arjun", "SHARED-02"), 0)
    finally:
        admin("UPDATE raglab.app_users SET is_active=true WHERE user_id='arjun'")
    check("Reactivated Arjun reads SHARED-02 again", visible_chunks("arjun", "SHARED-02") > 0, True)

    log("\n## 6. The retrieval role cannot read or change the authorization data")
    for t in ("document_acl", "user_groups", "app_users", "groups"):
        check(f"SELECT raglab.{t} refused", denied(f"SELECT * FROM raglab.{t} LIMIT 1"), "InsufficientPrivilege")
    check("Self-grant INSERT INTO user_groups refused",
          denied("INSERT INTO raglab.user_groups VALUES ('arjun','SECURITY_ENG')", "arjun"), "InsufficientPrivilege")
    check("UPDATE chunks refused", denied("UPDATE raglab.chunks SET tenant_id=tenant_id"), "InsufficientPrivilege")
    check("DELETE chunks refused", denied("DELETE FROM raglab.chunks"), "InsufficientPrivilege")
    check("ALTER TABLE ... DISABLE ROW LEVEL SECURITY refused",
          denied("ALTER TABLE raglab.chunks DISABLE ROW LEVEL SECURITY"), "InsufficientPrivilege")
    check("DROP POLICY refused", denied("DROP POLICY authorized_chunks ON raglab.chunks"), "InsufficientPrivilege")
    check("SET row_security=off cannot bypass RLS",
          denied("SET LOCAL row_security = off; SELECT count(*) FROM raglab.chunks"), "InsufficientPrivilege")

    log("\n## 7. Documented trust boundary (informational)")
    log("INFO  The database trusts app.user_id from whoever holds the retrieval-role password. That is why the")
    log("INFO  password lives only in the trusted backend, which sets app.user_id from a verified token. Users never")
    log("INFO  get database credentials; --user in search.py is a local demo stand-in for that verified identity.")

    log(f"\n{'ALL CHECKS PASSED' if FAILS == 0 else f'{FAILS} CHECK(S) FAILED'}")
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/exercise_e_security_tests.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
