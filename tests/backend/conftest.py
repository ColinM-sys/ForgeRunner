"""Backend test setup: a temp SQLite file, the scoring engines stubbed, and a client per test.

The environment is set before backend is imported, because settings and the database engine are created at import.
Nothing here loads a model, uses a GPU or reaches the network.
"""
import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="forgerunner-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/test.db"
os.environ["UPLOAD_DIR"] = os.path.join(_TMP, "uploads")
os.environ["EXPORT_DIR"] = os.path.join(_TMP, "exports")
os.environ["EMBEDDING_CACHE_DIR"] = os.path.join(_TMP, "embeddings")

import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import backend.database as database  # noqa: E402
import backend.main as main  # noqa: E402


class FakeOrchestrator:
    """Stands in for ScoringOrchestrator: no engines are loaded, and nothing is scored."""

    forge_embedder = None

    def __init__(self):
        self.started = False

    async def initialize(self):
        self.started = True

    async def shutdown(self):
        self.started = False


@pytest.fixture(autouse=True)
def fresh_database(monkeypatch):
    """A new, empty database file for each test. NullPool, so no connection outlives its test's event loop."""
    path = os.path.join(_TMP, f"{os.urandom(6).hex()}.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "async_session", session_factory)
    monkeypatch.setattr(main, "ScoringOrchestrator", FakeOrchestrator)
    yield path
    engine.sync_engine.dispose()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def sample_jsonl(tmp_path):
    """A small training file: three valid conversations and one line that does not parse."""
    import json
    rows = [
        {"messages": [{"role": "system", "content": "Be brief."},
                      {"role": "user", "content": "What is the refund window?"},
                      {"role": "assistant", "content": "Refunds are accepted within 30 days."}]},
        {"messages": [{"role": "user", "content": "Summarise the FAQ."},
                      {"role": "assistant", "content": "Shipping takes two days."}]},
        {"messages": [{"role": "user", "content": "¿Cuánto cuesta el plan?"},
                      {"role": "assistant", "content": "Depende del plan."}]},
    ]
    path = tmp_path / "sample.jsonl"
    lines = [json.dumps(r, ensure_ascii=False) for r in rows] + ["{not json"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clean_dirs():
    yield
    for name in ("uploads", "exports", "embeddings"):
        shutil.rmtree(os.path.join(_TMP, name), ignore_errors=True)
