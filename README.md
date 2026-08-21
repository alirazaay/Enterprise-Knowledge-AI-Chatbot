# Enterprise Knowledge AI

Enterprise Knowledge AI is a modular enterprise knowledge assistant foundation. Later phases will add document ingestion and retrieval-augmented answers with citations.

## Current status

Phase 4 complete — Document Upload & File Management. The project includes PostgreSQL/pgvector persistence, secure admin authentication, local PDF/DOCX document storage, document metadata APIs, and a protected Knowledge Base frontend.

Document parsing, page counting, chunking, embeddings, vector retrieval, LLM integration, citations, and chat remain unimplemented.

## Technology stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router
- Backend: Python, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy 2.x, Alembic, psycopg 3, pgvector
- Authentication: pwdlib/Argon2, PyJWT, HTTP Bearer
- Storage: configurable local filesystem storage with UUID-based filenames
- Infrastructure: PostgreSQL + pgvector through Docker Compose
- Planned later: Sentence Transformers, Ollama, Qwen

## Repository structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/             # Health and authentication endpoints
│   │   ├── core/            # Settings, database, security
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # Authentication and document services
│   │   └── scripts/         # Operational CLI commands
│   ├── alembic/             # Migration environment and revisions
│   ├── tests/
│   ├── .env.example
│   ├── pyproject.toml
│   └── README.md
├── frontend/
│   ├── src/context/         # Authentication provider
│   ├── src/pages/           # Login and protected placeholder pages
│   ├── src/services/        # API and auth clients
│   ├── src/types/
│   └── package.json
├── docs/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Environment configuration

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
Copy-Item .env.example .env
```

Replace local placeholders as needed. `.env` files are ignored by Git; `.env.example` files are intentionally tracked. Authentication requires `JWT_SECRET_KEY` of at least 32 characters. `JWT_ALGORITHM` defaults to `HS256`, and `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 60. `UPLOAD_DIR` defaults to `uploads`, and `MAX_UPLOAD_SIZE_MB` defaults to 25. Never commit or log the real secret.

## PostgreSQL and migrations

Docker is required for the local database. The Compose service uses `pgvector/pgvector:pg17` with a persistent named volume.

```powershell
docker compose up -d
docker compose ps

cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run alembic current
uv run alembic history
```

Rollback and re-apply:

```powershell
uv run alembic downgrade -1
uv run alembic upgrade head
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health` — application health, independent of PostgreSQL
- `GET /health/db` — database connectivity
- `POST /auth/login` — email/password login
- `GET /auth/me` — current authenticated user

Swagger: <http://127.0.0.1:8000/docs>

## Document upload and Knowledge Base

Authenticated admins can manage PDF and DOCX documents through:

- `POST /documents` — upload a document using multipart form data
- `GET /documents` — list metadata with pagination and basic filters
- `GET /documents/{id}` — inspect metadata
- `GET /documents/{id}/file` — download the stored file
- `DELETE /documents/{id}` — remove metadata and the physical file

Files are streamed to the configured local storage directory using generated UUID filenames. Original filenames are stored only as metadata and are sanitized when returned for download. The default upload limit is 25 MB. The storage service is isolated behind a small interface so a later S3, Azure Blob, or Google Cloud Storage implementation can replace it.

New files remain in the `uploaded` state with `page_count` unset and `chunk_count` equal to zero. This phase does not parse files or create chunks.

## Create the first admin

After migrations are applied, run:

```powershell
cd backend
python -m app.scripts.create_admin
```

The command prompts for name, email, and password without storing plaintext credentials in source code. Passwords must be at least 8 characters. Duplicate email addresses are rejected.

## Frontend authentication and Knowledge Base

```powershell
cd frontend
npm install
npm run dev
```

Unauthenticated users are sent to `/login`. Successful login stores the access token through one centralized auth service, restores the user through `/auth/me` on startup, and redirects to `/dashboard`. Admins can open `/knowledge-base` to upload, list, inspect, download, and delete documents. Logout clears the token and returns to login. The API base URL comes from `VITE_API_BASE_URL`.

Production checks:

```powershell
npm run lint
npm run build
```

## Database architecture

```mermaid
erDiagram
    USERS ||--o{ DOCUMENTS : uploads
    USERS ||--o{ CONVERSATIONS : owns
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : contains
    CONVERSATIONS ||--o{ MESSAGES : contains

    USERS { uuid id PK; string email UK; string role }
    DOCUMENTS { uuid id PK; uuid uploaded_by FK; string status }
    DOCUMENT_CHUNKS { uuid id PK; uuid document_id FK; vector embedding }
    CONVERSATIONS { uuid id PK; uuid user_id FK }
    MESSAGES { uuid id PK; uuid conversation_id FK; string role; jsonb sources }
```

Tables currently implemented: `users`, `documents`, `document_chunks`, `conversations`, and `messages`.
