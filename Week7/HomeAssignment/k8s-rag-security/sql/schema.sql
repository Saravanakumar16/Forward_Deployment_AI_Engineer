-- Run by bootstrap.py as the database owner/admin, never as the retrieval role.
-- Idempotent: safe to re-run; does not drop data.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS raglab;
REVOKE ALL ON SCHEMA raglab FROM PUBLIC;

-- ---------------------------------------------------------------- identity (private)
CREATE TABLE IF NOT EXISTS raglab.groups (
    group_name  text PRIMARY KEY,
    description text NOT NULL
);
CREATE TABLE IF NOT EXISTS raglab.app_users (
    user_id      text PRIMARY KEY,
    display_name text NOT NULL,
    tenant_id    text NOT NULL,
    is_active    boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS raglab.user_groups (
    user_id    text NOT NULL REFERENCES raglab.app_users(user_id) ON DELETE CASCADE,
    group_name text NOT NULL REFERENCES raglab.groups(group_name),
    granted_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, group_name)
);

-- ---------------------------------------------------------------- documents + ACL
CREATE TABLE IF NOT EXISTS raglab.documents (
    document_id    text PRIMARY KEY,
    tenant_id      text NOT NULL,
    category       text NOT NULL CHECK (category IN ('APPLICATION','PLATFORM','SECURITY','SHARED')),
    classification text NOT NULL CHECK (classification IN ('restricted','shared')),
    title          text NOT NULL,
    description    text NOT NULL DEFAULT '',
    file_name      text NOT NULL,
    source_path    text NOT NULL,          -- path inside github.com/kubernetes/website
    source_url     text NOT NULL,          -- published page on kubernetes.io
    github_url     text NOT NULL,          -- exact file at the pinned commit
    commit_sha     text NOT NULL,
    license        text NOT NULL,
    content_sha256 text NOT NULL,
    char_count     integer NOT NULL,
    ingested_at    timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS raglab.document_acl (
    document_id text NOT NULL REFERENCES raglab.documents(document_id) ON DELETE CASCADE,
    group_name  text NOT NULL REFERENCES raglab.groups(group_name),
    PRIMARY KEY (document_id, group_name)
);

-- ---------------------------------------------------------------- chunks + vectors
CREATE TABLE IF NOT EXISTS raglab.chunks (
    chunk_id     bigserial PRIMARY KEY,
    document_id  text NOT NULL REFERENCES raglab.documents(document_id) ON DELETE CASCADE,
    tenant_id    text NOT NULL,
    strategy     text NOT NULL CHECK (strategy IN ('fixed','recursive','markdown','semantic')),
    chunk_no     integer NOT NULL,
    heading_path text NOT NULL,            -- e.g. "Deployments > Rolling Back a Deployment"
    chunk_text   text NOT NULL,            -- exact substring of the cleaned document
    embed_text   text NOT NULL,            -- text actually embedded (markdown adds the breadcrumb)
    start_char   integer NOT NULL,         -- offset of chunk_text in the cleaned document
    char_count   integer NOT NULL,
    token_count  integer NOT NULL,         -- bge WordPiece tokens of embed_text
    embedding    vector(384) NOT NULL,
    UNIQUE (document_id, strategy, chunk_no)
);
CREATE INDEX IF NOT EXISTS chunks_document_idx ON raglab.chunks(document_id);
CREATE INDEX IF NOT EXISTS chunks_strategy_idx ON raglab.chunks(strategy);

-- ---------------------------------------------------------------- authorization
-- SECURITY DEFINER: evaluates the private ACL/identity tables on behalf of the
-- retrieval role, which has no SELECT on them. Identity comes from the
-- transaction-local settings app.user_id / app.tenant_id set by the trusted backend.
CREATE OR REPLACE FUNCTION raglab.may_read(p_document_id text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, raglab
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM raglab.documents d
    JOIN raglab.document_acl a ON a.document_id = d.document_id
    JOIN raglab.user_groups ug ON ug.group_name = a.group_name
    JOIN raglab.app_users u    ON u.user_id = ug.user_id
    WHERE d.document_id = p_document_id
      AND u.is_active
      AND u.user_id   = nullif(current_setting('app.user_id',   true), '')
      AND d.tenant_id = nullif(current_setting('app.tenant_id', true), '')
      AND u.tenant_id = d.tenant_id
  );
$$;
REVOKE ALL ON FUNCTION raglab.may_read(text) FROM PUBLIC;

-- Row-Level Security on BOTH tables the retrieval role can see. FORCE makes the
-- table owner subject to RLS too (superusers / BYPASSRLS roles are still exempt).
ALTER TABLE raglab.chunks    ENABLE ROW LEVEL SECURITY;
ALTER TABLE raglab.chunks    FORCE  ROW LEVEL SECURITY;
ALTER TABLE raglab.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE raglab.documents FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS authorized_chunks ON raglab.chunks;
CREATE POLICY authorized_chunks ON raglab.chunks FOR SELECT
USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')
       AND raglab.may_read(document_id));

DROP POLICY IF EXISTS authorized_documents ON raglab.documents;
CREATE POLICY authorized_documents ON raglab.documents FOR SELECT
USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')
       AND raglab.may_read(document_id));

-- The ingestion account (whoever runs this file) may maintain all rows.
-- Needed when it is a non-superuser owner, because FORCE RLS applies to owners.
DROP POLICY IF EXISTS ingest_maintenance ON raglab.chunks;
CREATE POLICY ingest_maintenance ON raglab.chunks FOR ALL TO CURRENT_USER USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS ingest_maintenance ON raglab.documents;
CREATE POLICY ingest_maintenance ON raglab.documents FOR ALL TO CURRENT_USER USING (true) WITH CHECK (true);
