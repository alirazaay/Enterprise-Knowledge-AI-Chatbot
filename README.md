# Enterprise Knowledge AI

Enterprise Knowledge AI is the foundation for a modular enterprise knowledge assistant. Later phases will add document ingestion and retrieval-augmented answers with citations; Phase 1 establishes only the development environment and application skeleton.

## Current status

Phase 1 — project foundation. The repository currently includes a minimal FastAPI backend with a health check and a React/TypeScript/Vite frontend placeholder. No database, authentication, document processing, embeddings, vector search, LLM integration, or chat features are implemented.

## Planned architecture

The monorepo keeps the presentation layer (`frontend`) separate from the API (`backend`). Future retrieval and model integrations should be implemented behind backend service interfaces so Ollama can be replaced by OpenAI, Gemini, AWS Bedrock, or another provider without changing API consumers.

## Technology stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: Python, FastAPI, Uvicorn, Pydantic Settings
- Planned later: PostgreSQL, pgvector, SQLAlchemy, Alembic, Sentence Transformers, Ollama, Qwen

## Repository structure

```text
.
├── backend/
│   ├── app/                 # FastAPI application package
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
├── .gitignore
└── README.md
```

## Environment configuration

Copy the example files before running locally:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Phase 1 does not require a database or Ollama. Their settings are present as placeholders for later phases. Secrets must remain in local `.env` files, which are ignored by Git.

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
