"""Stage 12 — episodic/semantic memory on PostgreSQL + pgvector (KB_14 §"Mem0 schema", research §19).

A direct pgvector-backed store on the `mem0_memories` table (NOT the `mem0ai` library — KB_14's own schema +
offline/free constraint; research §19.1). Real semantic embeddings via sentence-transformers (env-configurable;
default BAAI/bge-large-en-v1.5 / 1024-dim per KB_14). HNSW cosine search (research §19.2).

Namespace isolation (NIST RMF — no cross-tenant memory leakage, KB_14 §"Namespacing rules"): the adapter is bound to
a context (an incident + optional operator). It may read/write its OWN `incident:<id>` and `operator:<id>` namespaces
and the SHARED `semantic:*` / `procedural:*` / `agent:*` namespaces — but asking for ANOTHER incident's/operator's
namespace raises `CrossNamespaceAccessError`. Honest: if the embedder can't load, embedding-dependent ops raise
`EmbedderUnavailable` — never a fabricated/random embedding (Rule 1a).
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

_SHARED_PREFIXES = ("semantic:", "procedural:", "agent:")
# Default retention by namespace (KB_14 §"Retention policy"). None = indefinite.
_RETENTION_DAYS = {"incident:": 365, "operator:": None, "semantic:": None, "procedural:": None, "agent:": None}


class CrossNamespaceAccessError(PermissionError):
    """Raised when a callsite asks for a namespace outside its bound context (cross-tenant leakage guard)."""


class EmbedderUnavailable(RuntimeError):
    """Raised when the sentence-transformers embedder can't load — never a fake embedding."""


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def embed_dim() -> int:
    try:
        return int(os.environ.get("MEM0_EMBED_DIM", "1024"))
    except ValueError:
        return 1024


# ---- embedder (lazy, process-wide) -----------------------------------------

_embed_lock = threading.Lock()
_model: Any = None


def _embedder():
    global _model
    with _embed_lock:
        if _model is None:
            name = os.environ.get("MEM0_EMBED_MODEL", "BAAI/bge-large-en-v1.5")
            try:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(name, device="cpu")
            except Exception as e:  # noqa: BLE001
                raise EmbedderUnavailable(f"cannot load embedder {name!r}: {e}") from e
            _dim_fn = getattr(_model, "get_embedding_dimension", None) or _model.get_sentence_embedding_dimension
            got = int(_dim_fn())
            if got != embed_dim():
                raise EmbedderUnavailable(
                    f"embedder {name!r} is {got}-dim but MEM0_EMBED_DIM={embed_dim()} "
                    f"(mem0_memories.embedding is vector({embed_dim()})) — set a matching model/dim")
        return _model


def embed(text: str) -> list[float]:
    """Real semantic embedding (normalized for cosine). Raises EmbedderUnavailable if the model can't load."""
    vec = _embedder().encode(text, normalize_embeddings=True)
    return [float(x) for x in vec]


def _connect():
    dsn = _dsn()
    if not dsn:
        raise RuntimeError("mem0_adapter: no DATABASE_URL/POSTGRES_URL configured")
    import psycopg
    from pgvector.psycopg import register_vector
    conn = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
    register_vector(conn)
    return conn


def _mem0_app_dsn() -> Optional[str]:
    """DSN that logs in AS the non-superuser `mem0_app` role (migration 0009) — so FORCE RLS is enforced by the
    CONNECTION ROLE itself, not the best-effort per-op `SET ROLE` (G-076/R8). Built by swapping the userinfo of the
    primary DSN. Password from MEM0_APP_PASSWORD (prod) → POSTGRES_PASSWORD → dev default. Returns None if unbuildable."""
    dsn = _dsn()
    if not dsn:
        return None
    pwd = (os.environ.get("MEM0_APP_PASSWORD") or os.environ.get("POSTGRES_PASSWORD") or "devpass2026")
    from urllib.parse import urlsplit, urlunsplit, quote
    p = urlsplit(dsn)
    if not p.hostname:
        return None
    netloc = f"mem0_app:{quote(pwd, safe='')}@{p.hostname}" + (f":{p.port}" if p.port else "")
    return urlunsplit((p.scheme, netloc, p.path, p.query, p.fragment))


def _connect_ns(namespace: str):
    """Connect AND set the per-session RLS namespace (migrations 0008/0009): Postgres FORCE row-level security then
    filters every query on `mem0_memories` to this namespace — DB-enforced isolation behind the Python `_authorize`
    gate. Pass `*ALL*` only from trusted maintenance (the retention sweep).

    R8/G-076: PREFER connecting AS the non-superuser `mem0_app` LOGIN role (RLS enforced by the role, holds even if a
    code path forgets `SET ROLE`). Fall back to superuser + best-effort `SET ROLE` if the login role is unavailable
    (older DB / no password) — honest degradation; the Python `_authorize` gate is the first line either way."""
    import psycopg
    from pgvector.psycopg import register_vector

    if os.environ.get("MEM0_RLS_DIRECT_ROLE", "1") != "0":
        app_dsn = _mem0_app_dsn()
        if app_dsn:
            try:
                conn = psycopg.connect(app_dsn, autocommit=True, connect_timeout=5)
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute("SELECT set_config('app.mem0_namespace', %s, false)", (namespace,))
                return conn
            except Exception:  # noqa: BLE001 - login role absent/misconfigured -> fall back honestly
                pass

    conn = _connect()  # superuser DSN; drop privileges per-op (best-effort) so FORCE RLS applies
    with conn.cursor() as cur:
        try:
            cur.execute("SET ROLE mem0_app")
        except Exception:  # noqa: BLE001
            conn.rollback() if not conn.autocommit else None
        cur.execute("SELECT set_config('app.mem0_namespace', %s, false)", (namespace,))  # session-scoped (autocommit)
    return conn


def _retained_until(namespace: str) -> Optional[datetime]:
    for prefix, days in _RETENTION_DAYS.items():
        if namespace.startswith(prefix):
            return None if days is None else datetime.now(timezone.utc) + timedelta(days=days)
    return None


class Mem0Adapter:
    """Namespace-isolated episodic/semantic memory bound to one incident (+ optional operator) context."""

    def __init__(self, incident_id: Optional[str] = None, operator_id: Optional[str] = None) -> None:
        self.incident_id = incident_id
        self.operator_id = operator_id

    def _authorize(self, namespace: str) -> None:
        if namespace.startswith(_SHARED_PREFIXES):
            return
        if self.incident_id is not None and namespace == f"incident:{self.incident_id}":
            return
        if self.operator_id is not None and namespace == f"operator:{self.operator_id}":
            return
        raise CrossNamespaceAccessError(
            f"namespace {namespace!r} is outside this context "
            f"(incident={self.incident_id!r}, operator={self.operator_id!r})")

    def add(self, namespace: str, content: str, metadata: Optional[dict] = None,
            retained_until: Optional[datetime] = None) -> str:
        """Embed + store one memory in `namespace`. Returns the row id (uuid str)."""
        self._authorize(namespace)
        vec = embed(content)
        ru = retained_until if retained_until is not None else _retained_until(namespace)
        import json
        conn = _connect_ns(namespace)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO mem0_memories (namespace, content, embedding, metadata, retained_until)
                       VALUES (%s, %s, %s, %s::jsonb, %s) RETURNING id""",
                    (namespace, content, vec, json.dumps(metadata or {}), ru),
                )
                return str(cur.fetchone()[0])
        finally:
            conn.close()

    def search(self, namespace: str, query: str, k: int = 5) -> list[dict]:
        """Cosine-nearest memories WITHIN `namespace` (authorized). Returns [{id, content, score, metadata}]."""
        self._authorize(namespace)
        qvec = embed(query)
        conn = _connect_ns(namespace)
        try:
            with conn.cursor() as cur:
                # 1 - cosine_distance = cosine similarity. HNSW index serves the ORDER BY.
                # Cast the query param to `vector` explicitly: outside an INSERT there is no column-type context,
                # so psycopg would otherwise send the list as float8[] and `<=>` (vector,vector) wouldn't match.
                cur.execute(
                    """SELECT id, content, metadata, 1 - (embedding <=> %s::vector) AS score
                       FROM mem0_memories
                       WHERE namespace = %s AND (retained_until IS NULL OR retained_until > now())
                       ORDER BY embedding <=> %s::vector LIMIT %s""",
                    (qvec, namespace, qvec, int(k)),
                )
                return [{"id": str(r[0]), "content": r[1], "metadata": r[2], "score": float(r[3])}
                        for r in cur.fetchall()]
        finally:
            conn.close()

    def count(self, namespace: str) -> int:
        self._authorize(namespace)
        conn = _connect_ns(namespace)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM mem0_memories WHERE namespace = %s", (namespace,))
                return int(cur.fetchone()[0])
        finally:
            conn.close()


__all__ = ["Mem0Adapter", "CrossNamespaceAccessError", "EmbedderUnavailable", "embed", "embed_dim"]
