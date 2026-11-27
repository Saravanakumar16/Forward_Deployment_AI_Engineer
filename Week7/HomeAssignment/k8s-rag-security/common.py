"""Shared configuration, database connections and embeddings."""
from functools import lru_cache
import os
from dotenv import load_dotenv
from psycopg import connect as pg_connect
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from pgvector.psycopg import register_vector

load_dotenv()
TENANT = os.getenv("TENANT_ID", "K8S_DOCS_DEMO")
MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
# "fastembed" (default, the real BGE model). "offline-lsa" is a test-only stand-in, see offline_embedder.py
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "fastembed")
EMBEDDER_LABEL = MODEL if EMBED_BACKEND == "fastembed" else "OFFLINE-LSA stand-in (not BGE)"
EMBED_DIM = 384
DBNAME = os.getenv("DATABASE_NAME", "k8s_raglab")
SERVER_URL = os.environ.get("POSTGRES_SERVER_URL", "")
READER_ROLE = os.environ.get("READER_ROLE", "rag_app_reader")
READER_PASSWORD = os.environ.get("READER_PASSWORD", "")
DEFAULT_STRATEGY = os.getenv("RETRIEVAL_STRATEGY", "markdown")
STRATEGIES = ("fixed", "recursive", "markdown", "semantic")
# Query prefix recommended by BAAI for bge-*-en-v1.5 short-query -> passage retrieval.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def connection_string(*, admin=False, server=False):
    """admin=True  -> privileged owner account from POSTGRES_SERVER_URL (bootstrap/ingest only)
    server=True -> same account, maintenance DB (to CREATE DATABASE)
    default      -> restricted retrieval role (RLS applies; no ACL/identity table access)"""
    if not SERVER_URL:
        raise RuntimeError("Set POSTGRES_SERVER_URL in .env (copy .env.example)")
    settings = conninfo_to_dict(SERVER_URL)
    if not server:
        settings["dbname"] = DBNAME
    if not admin and not server:
        settings["user"] = READER_ROLE
        settings["password"] = READER_PASSWORD
    return make_conninfo(**settings)


def connect(*, admin=False, server=False, autocommit=False, register=True):
    db = pg_connect(connection_string(admin=admin, server=server), autocommit=autocommit)
    if not server and register:
        register_vector(db)
    return db


@lru_cache(maxsize=1)
def get_model():
    from fastembed import TextEmbedding
    print(f"Loading local embedding model: {MODEL} (first run downloads weights)")
    return TextEmbedding(model_name=MODEL)


def embed(texts, batch_size=32):
    if EMBED_BACKEND == "offline-lsa":
        from offline_embedder import embed as lsa_embed
        return lsa_embed(texts)
    vectors = [v.tolist() for v in get_model().embed(list(texts), batch_size=batch_size)]
    if any(len(v) != EMBED_DIM for v in vectors):
        raise RuntimeError(f"Expected {EMBED_DIM}-dimensional embeddings from {MODEL}")
    return vectors


def embed_query(question):
    return embed([QUERY_PREFIX + question])[0]


@lru_cache(maxsize=1)
def get_tokenizer():
    """The model's own WordPiece tokenizer (used for token statistics). None if unavailable."""
    if EMBED_BACKEND != "fastembed":
        return None
    try:
        model = get_model().model
        tok = getattr(model, "tokenizer", None)
        if tok is None and hasattr(model, "load_onnx_model"):
            model.load_onnx_model()
            tok = model.tokenizer
        return tok
    except Exception:
        return None


def count_tokens(texts):
    tok = get_tokenizer()
    if tok is None:  # fallback approximation
        return [max(1, round(len(t) / 4)) for t in texts]
    # fastembed's tokenizer pads every text in a batch to the same length and truncates at 512:
    # switch both off to count real tokens, then restore the model's settings.
    padding, truncation = tok.padding, tok.truncation
    tok.no_padding(); tok.no_truncation()
    try:
        out = [len(e.ids) for e in tok.encode_batch(list(texts))]
    finally:
        if padding:
            tok.enable_padding(**{k: v for k, v in padding.items() if k != "length" or v})
        if truncation:
            tok.enable_truncation(**truncation)
    return out


def set_identity(db, user_id):
    """Transaction-scoped identity (SET LOCAL semantics): it disappears at COMMIT/ROLLBACK,
    so a pooled connection can never leak one user's identity to the next request."""
    db.execute("SELECT set_config('app.user_id', %s, true)", (user_id,))
    db.execute("SELECT set_config('app.tenant_id', %s, true)", (TENANT,))
