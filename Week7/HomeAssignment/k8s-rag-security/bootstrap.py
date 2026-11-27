"""One-time, re-runnable setup: database, schema, RLS, retrieval role, groups and demo identities."""
import json
from pathlib import Path
from psycopg import sql
from common import connect, DBNAME, READER_ROLE, READER_PASSWORD, TENANT

ROOT = Path(__file__).resolve().parent
PRIVATE_TABLES = ("raglab.groups", "raglab.app_users", "raglab.user_groups", "raglab.document_acl")


def main():
    if not READER_PASSWORD:
        raise RuntimeError("READER_PASSWORD is missing in .env")
    with connect(server=True, autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DBNAME,)).fetchone():
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DBNAME)))
            print(f"Created database {DBNAME}")
        else:
            print(f"Using existing database {DBNAME}")

    with connect(admin=True, register=False) as db:
        db.execute((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))
        role = sql.Identifier(READER_ROLE)
        exists = db.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (READER_ROLE,)).fetchone()
        # Retrieval role: can log in, cannot bypass RLS, owns nothing, inherits nothing.
        db.execute(sql.SQL("{} ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT PASSWORD {}")
                   .format(sql.SQL("ALTER" if exists else "CREATE"), role, sql.Literal(READER_PASSWORD)))
        db.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(DBNAME), role))
        db.execute(sql.SQL("GRANT USAGE ON SCHEMA raglab TO {}").format(role))
        db.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA raglab FROM {}").format(role))
        db.execute(sql.SQL("GRANT SELECT ON raglab.chunks, raglab.documents TO {}").format(role))
        db.execute(sql.SQL("GRANT EXECUTE ON FUNCTION raglab.may_read(text) TO {}").format(role))
        print(f"Retrieval role {READER_ROLE}: SELECT on chunks/documents (RLS), EXECUTE may_read; "
              f"no access to {', '.join(PRIVATE_TABLES)}")

        cfg = json.loads((ROOT / "data/users.json").read_text(encoding="utf-8"))
        for g, desc in cfg["groups"].items():
            db.execute("""INSERT INTO raglab.groups(group_name, description) VALUES (%s,%s)
                          ON CONFLICT (group_name) DO UPDATE SET description=excluded.description""", (g, desc))
        for u in cfg["users"]:
            db.execute("""INSERT INTO raglab.app_users(user_id, display_name, tenant_id, is_active)
                          VALUES (%s,%s,%s,true) ON CONFLICT (user_id) DO UPDATE
                          SET display_name=excluded.display_name, tenant_id=excluded.tenant_id, is_active=true""",
                       (u["user_id"], u["display_name"], TENANT))
            db.execute("DELETE FROM raglab.user_groups WHERE user_id=%s", (u["user_id"],))
            for g in u["groups"]:
                db.execute("INSERT INTO raglab.user_groups(user_id, group_name) VALUES (%s,%s)", (u["user_id"], g))
            print(f"  identity {u['user_id']:6} -> {', '.join(u['groups'])}")
    print("Next: python ingest.py")


if __name__ == "__main__":
    main()
