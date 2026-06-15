"""Lifecycle helper for the DEDICATED admin-UI-review database.

The ``review-admin-ui`` skill runs its browser review against its OWN database
(default ``<prefix>_test_review``, e.g. ``edu2_test_review``) — never ``edu``
(dev) and never the pytest DBs (``<prefix>_test`` / ``_test_e2e`` / ``_test_prod``;
the prefix is the repo folder name). This gives the review full
isolation: it can create/delete freely and is torn down at the end, with zero
chance of colliding with a running test suite.

Subcommands::

    python review_db.py recreate   # DROP + CREATE the review DB + extensions (pristine; run BEFORE the backend)
    python review_db.py create     # CREATE if missing + extensions (idempotent)
    python review_db.py seed        # wipe all rows + ensure the users.id=1 sentinel (run AFTER the backend migrates)
    python review_db.py wipe        # alias of seed
    python review_db.py drop        # DROP the review DB entirely (teardown)
    python review_db.py check       # report per-table row counts, no mutation

DB name comes from ``EDU_TEST_DB`` (default ``<prefix>_test_review``) — the same env var
the backend reads under ``EDU_TEST_MODE=1`` to point at this DB. Connection params
come from the standard ``DATABASE__PG_*`` env vars (defaults: localhost:5432 /
postgres / postgres).

Destructive subcommands (recreate / drop / seed / wipe) REFUSE to run against the
dev ``edu`` DB or any canonical pytest DB — a hard wall so this skill can never
damage those.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Reuse the ORM metadata (single source of truth for the table set + FK order).
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "src"))

# Per-clone DB prefix from the repo folder (edu→"edu", edu2→"edu2"), matching
# tests/_db_prefix.py for the main checkout. The review DB is the clone's
# DEDICATED, disposable `<prefix>_test_review` (e.g. edu2_test_review).
_PREFIX = re.sub(r"[^a-z0-9]+", "_", _REPO.name.lower()).strip("_") or "edu"

# DBs this review tool must NEVER create/drop/wipe: the dev DB + this clone's
# pytest DBs. (The review DB `<prefix>_test_review` is NOT protected — it's the
# target — and is namespaced away from the pytest `<prefix>_test*` DBs.)
_PROTECTED = {
    "edu",
    _PREFIX,
    f"{_PREFIX}_test",
    f"{_PREFIX}_test_e2e",
    f"{_PREFIX}_test_prod",
}

_DBNAME = os.environ.get("EDU_TEST_DB", f"{_PREFIX}_test_review")

_HOST = os.environ.get("DATABASE__PG_HOST", "localhost")
_PORT = os.environ.get("DATABASE__PG_PORT", "5432")
_USER = os.environ.get("DATABASE__PG_USERNAME", "postgres")
_PW = os.environ.get("DATABASE__PG_PASSWORD", "postgres")

from sqlalchemy import create_engine, text  # noqa: E402

import db.models  # noqa: E402,F401 — registers every ORM model on Base.metadata
from db.base import Base  # noqa: E402

_ADMIN_URL = f"postgresql://{_USER}:{_PW}@{_HOST}:{_PORT}/postgres"
_DB_URL = f"postgresql://{_USER}:{_PW}@{_HOST}:{_PORT}/{_DBNAME}"

_USAGE = "usage: review_db.py {recreate|create|seed|wipe|drop|check}"


def _guard_destructive() -> None:
    if _DBNAME in _PROTECTED or _DBNAME == "":
        sys.exit(
            f"[review_db] refusing a destructive op on '{_DBNAME}' — that is the "
            "dev or a pytest DB. Set EDU_TEST_DB to a dedicated review DB "
            f"(e.g. {_PREFIX}_test_review)."
        )


def _create(*, recreate: bool) -> None:
    _guard_destructive()
    admin = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if recreate:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{_DBNAME}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{_DBNAME}"'))
        else:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _DBNAME}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{_DBNAME}"'))
    admin.dispose()
    # Extensions (need superuser; idempotent). The alembic migrations also carry
    # CREATE EXTENSION IF NOT EXISTS, but provisioning them here makes a fresh DB
    # safe even if migration order changes.
    eng = create_engine(_DB_URL, isolation_level="AUTOCOMMIT")
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    eng.dispose()
    print(
        f"[review_db] {'recreated' if recreate else 'ensured'} '{_DBNAME}' (+ vector, pg_trgm)"
    )


def _drop() -> None:
    _guard_destructive()
    admin = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{_DBNAME}" WITH (FORCE)'))
    admin.dispose()
    print(f"[review_db] dropped '{_DBNAME}'")


def _seed() -> None:
    """Wipe all rows (reverse FK order) and ensure the super-admin sentinel.

    Mirrors tests/conftest.py: keep/insert users.id=1 (ADMIN_USER_ID) so the app's
    row-attribution sentinel and local super-admin path keep working; everything
    else is emptied. Requires the schema to already exist (run after the backend
    has auto-migrated the DB).
    """
    _guard_destructive()
    eng = create_engine(_DB_URL)
    with eng.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name == "users":
                conn.execute(text("DELETE FROM users WHERE id != 1"))
            else:
                conn.execute(text(f"DELETE FROM {table.name}"))  # noqa: S608 — ORM metadata
        # Ensure the sentinel exists on a freshly-migrated DB.
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hashed, role, "
                "is_active, last_login_session, state, create_timestamp) "
                "VALUES (1, '__system__', 'x', 'admin', true, 0, 0, NOW()) "
                "ON CONFLICT (id) DO NOTHING"
            )
        )
        conn.execute(text("SELECT setval('users_id_seq', 1, true)"))
        conn.commit()
    eng.dispose()
    print(f"[review_db] wiped '{_DBNAME}' to a clean slate (kept users.id=1 sentinel)")


def _check() -> None:
    eng = create_engine(_DB_URL)
    tables = list(reversed(Base.metadata.sorted_tables))
    total = 0
    with eng.connect() as conn:
        for table in tables:
            n = int(
                conn.execute(text(f"SELECT count(*) FROM {table.name}")).scalar_one()
            )  # noqa: S608
            total += n
            if n:
                print(f"  {table.name}: {n}")
    eng.dispose()
    print(
        f"[review_db] check: '{_DBNAME}' holds {total} rows across {len(tables)} tables"
    )


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.exit(_USAGE)
    action = argv[0]
    if action == "recreate":
        _create(recreate=True)
    elif action == "create":
        _create(recreate=False)
    elif action in ("seed", "wipe"):
        _seed()
    elif action == "drop":
        _drop()
    elif action == "check":
        _check()
    else:
        sys.exit(_USAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
