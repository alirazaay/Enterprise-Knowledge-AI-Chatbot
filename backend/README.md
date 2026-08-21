# Backend

FastAPI and synchronous SQLAlchemy backend for Enterprise Knowledge AI. Phase 4 includes PostgreSQL/pgvector persistence, authentication, and admin-only PDF/DOCX document file management. Parsing, chunking, embeddings, and retrieval remain out of scope.

Install with `python -m pip install -e ".[dev]"`, then run `python -m uvicorn app.main:app --reload`.

Run migrations from this directory with `alembic upgrade head`. `DATABASE_URL`, `JWT_SECRET_KEY`, `UPLOAD_DIR`, and `MAX_UPLOAD_SIZE_MB` are configured in `backend/.env` or the environment. The first admin is created with `python -m app.scripts.create_admin`.
