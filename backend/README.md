# Backend

FastAPI and synchronous SQLAlchemy backend for Enterprise Knowledge AI. Phase 5 includes PostgreSQL/pgvector persistence, authentication, admin-only PDF/DOCX file management, PyMuPDF/python-docx parsing, and persisted extracted content. Chunking, embeddings, and retrieval remain out of scope.

Install with `python -m pip install -e ".[dev]"`, then run `python -m uvicorn app.main:app --reload`.

Run migrations from this directory with `alembic upgrade head`. `DATABASE_URL`, `JWT_SECRET_KEY`, `UPLOAD_DIR`, and `MAX_UPLOAD_SIZE_MB` are configured in `backend/.env` or the environment. The first admin is created with `python -m app.scripts.create_admin`. Processing is explicitly triggered with `POST /documents/{id}/process`.
