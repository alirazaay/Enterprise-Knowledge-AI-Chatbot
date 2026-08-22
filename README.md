# Enterprise Knowledge AI

Enterprise Knowledge AI is a modular enterprise knowledge assistant foundation. Later phases will add chunking, embeddings, retrieval, and grounded answers with citations.

## Current status

Phase 6 complete — Local RAG Ingestion & Vector Indexing. The project now supports secure admin document upload, PDF/DOCX parsing, structure-aware chunking, local embeddings, and pgvector persistence.

Question retrieval, OCR, LLM integration, citations, and chat remain unimplemented.

## Technology stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router
- Backend: Python, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy 2.x, Alembic, psycopg 3, pgvector
- Authentication: pwdlib/Argon2, PyJWT, HTTP Bearer
- Parsing: PyMuPDF, python-docx
- Indexing: sentence-transformers/all-MiniLM-L6-v2, pgvector VECTOR(384)
- Storage: configurable local filesystem storage with UUID-based filenames
- Infrastructure: PostgreSQL + pgvector through Docker Compose

## Environment configuration

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
Copy-Item .env.example .env
```

Important backend settings include `DATABASE_URL`, `JWT_SECRET_KEY`, `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION=384`, `EMBEDDING_BATCH_SIZE=32`, `CHUNK_SIZE_WORDS=600`, and `CHUNK_OVERLAP_WORDS=100`. `.env` files are ignored by Git; `.env.example` files are tracked placeholders.

## Run locally

```powershell
docker compose up -d

cd backend
uv sync --extra dev
uv run alembic upgrade head
python -m app.scripts.create_admin
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Authentication and document workflow

Admins sign in at `/login`, open `/knowledge-base`, upload a PDF or DOCX, explicitly choose `Process`, then choose `Index`. Uploading remains fast and does not automatically run parsing or embedding inference.

Document endpoints:

- `POST /documents` — upload PDF/DOCX metadata and file
- `GET /documents` — list metadata
- `GET /documents/{id}` — inspect metadata and processing state
- `GET /documents/{id}/file` — download source file
- `DELETE /documents/{id}` — remove source and metadata
- `POST /documents/{id}/process` — extract PDF/DOCX text
- `GET /documents/{id}/content` — inspect extracted pages/sections
- `POST /documents/{id}/index` — chunk extracted content and store local embeddings
- `GET /documents/{id}/chunks` — inspect chunks and metadata without vector arrays

Swagger is available at <http://127.0.0.1:8000/docs>.

## Parsing behavior

PDFs are parsed page by page with PyMuPDF. User-facing page numbers are 1-based and `page_count` is populated from the PDF.

DOCX files are parsed in logical XML order. Paragraphs, headings, and tables are preserved as source blocks. DOCX page numbers are not reliable through `python-docx`, so they remain `null`.

Text cleaning is conservative: line endings, repeated whitespace, excessive blank lines, and invalid control characters are normalized without removing headings, punctuation, IDs, acronyms, or numbers.

Scanned/image-only PDFs, encrypted PDFs, corrupt files, empty files, and documents without meaningful text become `failed` with a safe `processing_error`. OCR is not implemented.

Lifecycle:

```text
uploaded -> processing -> processed
                    \-> failed
```

Reprocessing replaces prior extracted blocks atomically and preserves the original uploaded file. Extracted content is stored in `document_pages`.

## Chunking and local embeddings

Chunking is word-based and page/section-aware. Defaults are 600 target words with 100 overlapping words. PDF chunks retain page numbers; DOCX chunks retain logical ordering and use `null` page numbers. The local `sentence-transformers/all-MiniLM-L6-v2` model is loaded lazily, batched, normalized, and validated before vectors are stored as PostgreSQL `VECTOR(384)`. No ANN index is created yet.

Indexing replaces existing chunks atomically and supports re-indexing:

```text
uploaded -> processing -> processed -> indexing -> indexed
                                      \-> failed
```

Indexing failures use `indexing_error`; parsing failures use `processing_error`. Source files and extracted pages are retained after failure.

## Migrations and verification

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
uv run alembic history
uv run alembic downgrade -1
uv run alembic upgrade head
uv run pytest
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

## Repository structure

```text
.
├── backend/app/api/          # Health, auth, document endpoints
├── backend/app/core/         # Settings, database, storage, security
├── backend/app/models/       # SQLAlchemy models including document_pages
├── backend/app/schemas/      # Pydantic API schemas
├── backend/app/services/     # Storage, parser, processing, chunking, indexing services
├── backend/alembic/          # Migration environment and revisions
├── backend/tests/            # Auth, storage, parser, processing, API tests
├── frontend/src/pages/       # Login, dashboard, Knowledge Base
├── docker-compose.yml
└── README.md
```
