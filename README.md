# Enterprise Knowledge AI

Enterprise Knowledge AI is the foundation for a modular enterprise knowledge assistant. Later phases will add document ingestion and retrieval-augmented answers with citations.

## Current status

Phase 2 complete — Database Foundation. The repository now includes a migration-first PostgreSQL + pgvector layer with SQLAlchemy models, Alembic migrations, and a database health check. Authentication, document processing, embeddings, vector retrieval, LLM integration, and chat remain unimplemented.

## Planned architecture

The monorepo keeps the presentation layer (`frontend`) separate from the API (`backend`). Future retrieval and model integrations should be implemented behind backend service interfaces so Ollama can be replaced by OpenAI, Gemini, AWS Bedrock, or another provider without changing API consumers.

## Technology stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: Python, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy 2.x, Alembic, psycopg 3, pgvector
- Infrastructure: PostgreSQL + pgvector through Docker Compose
- Planned later: Sentence Transformers, Ollama, Qwen

## Repository structure

```text
.
├── backend/
│   ├── app/                 # FastAPI application package
│   ├── alembic/             # Migration environment and revisions
│   ├── alembic.ini
│   ├── tests/               # Backend tests
│   ├── .env.example
│   ├── pyproject.toml
│   └── README.md
├── frontend/
│   ├── src/                 # React application source
│   ├── .env.example
│   ├── package.json
│   └── vite.config.ts
├── docs/
├── docker-compose.yml       # Local PostgreSQL + pgvector
├── .env.example              # Compose development variables
├── .gitignore
└── README.md
```

## Environment configuration

Copy the example files before running locally:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
Copy-Item .env.example .env
```

The backend `DATABASE_URL` and Compose `POSTGRES_*` values are development placeholders. Replace them locally as needed; do not commit `.env` files. Ollama settings remain placeholders and are not used.

## PostgreSQL and pgvector

Docker is required for the local database. The Compose service uses the standard `pgvector/pgvector:pg17` image and a named persistent volume. The initial Alembic migration enables the `vector` extension and creates the five Phase 2 tables.

Start and stop the database:

```powershell
docker compose up -d
docker compose ps
docker compose down
```

Apply and inspect migrations from `backend`:

```powershell
alembic upgrade head
alembic current
alembic history
alembic downgrade -1
alembic upgrade head
```

The database health endpoint is `GET http://127.0.0.1:8000/health/db`; the original `/health` endpoint remains independent of database availability.

### Database architecture

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

## Run the backend

From `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check: <http://127.0.0.1:8000/health>

## Run the frontend

From `frontend`:

```powershell
npm install
npm run dev
```

Production checks:

```powershell
npm run lint
npm run build
```

The frontend API base URL is configured through `VITE_API_BASE_URL`; application code should use the shared API client rather than hard-coding URLs.
