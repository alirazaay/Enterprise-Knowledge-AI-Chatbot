from fastapi.testclient import TestClient

import app.core.database as database
from app.main import app


def test_database_health_reports_missing_configuration(monkeypatch) -> None:
    database.get_engine.cache_clear()
    database.get_session_factory.cache_clear()
    monkeypatch.setattr(
        database,
        "_database_url",
        lambda: (_ for _ in ()).throw(RuntimeError("DATABASE_URL is required")),
    )

    response = TestClient(app).get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database configuration is unavailable."}

    database.get_engine.cache_clear()
    database.get_session_factory.cache_clear()
