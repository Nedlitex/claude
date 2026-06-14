"""Wipe every row in the edu_test database (keeping the super_admin sentinel
user id=1). The ``review-admin-ui`` skill runs this BEFORE and AFTER a review so
the run never leaves data behind in the shared ``edu_test`` DB.

Row-level ``DELETE`` only (no ``DROP``/``TRUNCATE`` DDL), in reverse
foreign-key order via ``Base.metadata.sorted_tables`` — the same approach as
``tests/conftest.py``'s e2e cleanup, so FK constraints never trip.

Target DB = ``EDU_TEST_DB`` (default ``edu_test``). It REFUSES to run against
the dev ``edu`` DB (defense-in-depth alongside ``settings._enforce_test_mode``).
Connection params come from the standard ``DATABASE__PG_*`` env vars, defaulting
to the project's local test creds (localhost:5432 / postgres / postgres).

Usage (run with the project venv from the repo root):
    .venv/Scripts/python .claude/skills/review-admin-ui/reset_edu_test.py
    .venv/Scripts/python .claude/skills/review-admin-ui/reset_edu_test.py --check

``--check`` connects and reports per-table row counts WITHOUT deleting — use it
to confirm wiring before a run.

Must run AFTER the backend has booted (schema present); it deletes rows, it does
not create tables.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DBNAME = os.environ.get("EDU_TEST_DB", "edu_test")
if _DBNAME in ("edu", ""):
    sys.exit(
        f"[reset_edu_test] refusing to wipe '{_DBNAME}' — "
        "set EDU_TEST_DB to a test database (e.g. edu_test)."
    )

_HOST = os.environ.get("DATABASE__PG_HOST", "localhost")
_PORT = os.environ.get("DATABASE__PG_PORT", "5432")
_USER = os.environ.get("DATABASE__PG_USERNAME", "postgres")
_PW = os.environ.get("DATABASE__PG_PASSWORD", "postgres")

# Make the app's `src/` importable so we reuse the ORM metadata (single source
# of truth for the table set + FK order).
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "src"))

from sqlalchemy import create_engine, text  # noqa: E402

import db.models  # noqa: E402,F401 — registers every ORM model on Base.metadata
from db.base import Base  # noqa: E402

_CHECK = "--check" in sys.argv[1:]
_URL = f"postgresql://{_USER}:{_PW}@{_HOST}:{_PORT}/{_DBNAME}"


def main() -> int:
    engine = create_engine(_URL)
    tables = list(reversed(Base.metadata.sorted_tables))
    with engine.connect() as conn:
        if _CHECK:
            total = 0
            for table in tables:
                n = conn.execute(
                    text(f"SELECT count(*) FROM {table.name}")  # noqa: S608 — table names from ORM metadata
                ).scalar_one()
                total += int(n)
                if n:
                    print(f"  {table.name}: {n}")
            print(
                f"[reset_edu_test] --check: '{_DBNAME}' holds {total} rows across {len(tables)} tables"
            )
            return 0

        for table in tables:
            if table.name == "users":
                # Preserve the super_admin sentinel (ADMIN_USER_ID=1) so local
                # super-admin login keeps working after the wipe.
                conn.execute(text("DELETE FROM users WHERE id != 1"))
            else:
                conn.execute(text(f"DELETE FROM {table.name}"))  # noqa: S608 — ORM metadata
        conn.commit()
    print(f"[reset_edu_test] wiped all rows in '{_DBNAME}' (kept users.id=1 sentinel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
