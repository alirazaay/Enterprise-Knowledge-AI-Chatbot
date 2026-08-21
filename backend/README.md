# Backend

FastAPI and synchronous SQLAlchemy foundation for Enterprise Knowledge AI. Phase 2 adds PostgreSQL/pgvector models and Alembic migrations; application features remain intentionally out of scope.

Install with `python -m pip install -e ".[dev]"`, then run `python -m uvicorn app.main:app --reload`.

Run migrations from this directory with `alembic upgrade head`. `DATABASE_URL` must be configured in `backend/.env` or the environment.
