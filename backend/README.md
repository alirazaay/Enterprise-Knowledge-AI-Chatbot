# Backend

FastAPI and synchronous SQLAlchemy backend for Enterprise Knowledge AI. Phase 6 includes PostgreSQL/pgvector persistence, authentication, admin-only PDF/DOCX file management, PyMuPDF/python-docx parsing, word-based chunking, local sentence-transformer embeddings, and pgvector storage. Retrieval and chat remain out of scope.

Install with `python -m pip install -e ".[dev]"`, then run `python -m uvicorn app.main:app --reload`.

Run migrations from this directory with `alembic upgrade head`. `DATABASE_URL`, `JWT_SECRET_KEY`, `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `EMBEDDING_BATCH_SIZE`, `CHUNK_SIZE_WORDS`, and `CHUNK_OVERLAP_WORDS` are configured in `backend/.env` or the environment. The first admin is created with `python -m app.scripts.create_admin`. Processing is explicitly triggered with `POST /documents/{id}/process`, followed by `POST /documents/{id}/index`.

The default model is `sentence-transformers/all-MiniLM-L6-v2`; its 384-dimensional normalized vectors are stored in `document_chunks.embedding` as `VECTOR(384)`. The model is loaded lazily on the first indexing request, so the first run may download model files. `GET /documents/{id}/chunks` exposes ordered chunk text and metadata, never embedding arrays.
