# 🤖 RAG Document Assistant

A full-stack **Retrieval-Augmented Generation (RAG)** application that lets you upload documents and chat with them using AI, with support for **100% free local execution** or cloud LLM providers.

## 🏗️ Architecture

```
                    USER
                      │
                      ▼
            React 18 Frontend (:3000)
                      │
                      │ POST /upload, POST /chat
                      │ GET /chat/history
                      ▼
            FastAPI Backend (:8000)
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
      PostgreSQL   LangChain    Qdrant
    (Docs & Chat)      │       (Vectors)
                       ├─────────────────┐
                       ▼                 ▼
                 FastEmbed ONNX     LLM Engine
               (BAAI/bge-small) (Local/OpenAI/OpenRouter)
                       │                 │
                       └────────┬────────┘
                                ▼
                             Response
```

## 🛠️ Tech Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | React 18 + Vite | Modern dark-themed UI with document selector & chat |
| **Backend** | FastAPI (Python 3.11) | Async REST API & document processing pipeline |
| **Embeddings** | FastEmbed / OpenAI | FastEmbed `BAAI/bge-small-en-v1.5` (Local CPU, ONNX) or OpenAI |
| **LLM Provider** | Local / OpenRouter / Ollama / OpenAI | Local Grounded Engine (Free, Offline) or cloud models |
| **Vector DB** | Qdrant | High-performance vector database with dynamic dimensioning |
| **Metadata & History DB** | PostgreSQL 16 | Stores uploaded document metadata & persistent chat history |
| **Orchestration** | LangChain | RAG retrieval chain & prompt engineering |
| **Infrastructure** | Docker Compose | Multi-container orchestration |

## 📄 Supported Document Formats

📄 PDF · 📝 TXT · 📋 DOCX · 📑 Markdown · 📊 CSV · 🌐 HTML

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### 1. Clone & Launch

```bash
git clone <your-repo-url>
cd ragflow-ai-document-assistant

# Start all services (PostgreSQL, Qdrant, Backend, Frontend)
docker compose up -d --build
```

### 2. Access the Application

- **React Frontend**: [http://localhost:3000](http://localhost:3000)
- **FastAPI API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

## ⚙️ Model Configuration

Configuration is managed via `backend/.env`.

### Option A: Free / Local Execution (Default)
No API keys or paid quotas required. Runs FastEmbed ONNX locally on CPU:

```env
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

LLM_PROVIDER=local
LLM_MODEL=local-grounded
```

### Option B: OpenAI
```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-actual-key-here
```

### Option C: OpenRouter / Ollama
```env
LLM_PROVIDER=openrouter
LLM_MODEL=meta-llama/llama-3.2-1b-instruct:free
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

## 🗄️ Database Setup & Configuration Guide

The application uses **PostgreSQL 16** for storing document metadata and persistent chat history.

### 1. `DATABASE_URL` Format

Configured in `backend/.env`:

```env
DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/<database_name>
```

#### Connection Scenarios:

- **Docker Compose (Default)**:
  ```env
  DATABASE_URL=postgresql://raguser:ragpass@db:5432/ragdb
  ```
- **Local Machine (Standalone PostgreSQL)**:
  ```env
  DATABASE_URL=postgresql://raguser:ragpass@localhost:5432/ragdb
  ```
- **Cloud Database (AWS RDS / Supabase / Neon / Cloud SQL)**:
  ```env
  DATABASE_URL=postgresql://user:password@db.example.com:5432/ragdb?sslmode=require
  ```

---

### 2. Database Schema

Tables are managed automatically by SQLAlchemy on app startup (`Base.metadata.create_all`):

#### `documents` Table
Stores metadata for every uploaded file:
- `id` (INT, Primary Key)
- `filename` (VARCHAR)
- `file_type` (VARCHAR: pdf, txt, docx, md, csv, html)
- `file_size` (INT, in bytes)
- `chunk_count` (INT)
- `status` (VARCHAR: processing | ready | error)
- `uploaded_at` (TIMESTAMP)

#### `chat_messages` Table
Stores persistent QA exchanges:
- `id` (INT, Primary Key)
- `document_id` (INT, Optional filter)
- `question` (TEXT)
- `answer` (TEXT)
- `sources` (TEXT, JSON-serialized snippet metadata)
- `created_at` (TIMESTAMP)

---

### 3. Database Management Commands

#### Inspect PostgreSQL via Docker:
```bash
# Connect to PostgreSQL shell
docker exec -it ragflow-ai-document-assistant-db-1 psql -U raguser -d ragdb

# List all relations/tables
\dt

# View uploaded document records
SELECT id, filename, file_type, status, uploaded_at FROM documents;

# View saved chat history
SELECT id, question, answer, created_at FROM chat_messages;

# Exit psql shell
\q
```

#### Backup & Restore Database:
```bash
# Export database dump
docker exec ragflow-ai-document-assistant-db-1 pg_dump -U raguser ragdb > backup.sql

# Restore database dump
cat backup.sql | docker exec -i ragflow-ai-document-assistant-db-1 psql -U raguser -d ragdb
```


## 🔄 How It Works

1. **Upload & Ingest** — Upload any supported file in the sidebar. The backend parses text, splits it into chunks, embeds each chunk locally using FastEmbed, and stores vector representations in Qdrant.
2. **Chat & Retrieve** — Type a query. The backend retrieves the top matching vector chunks from Qdrant, synthesizes the context, and generates a grounded response with source citations.
3. **PostgreSQL Chat Persistence** — Every question and response pair is saved to PostgreSQL, allowing you to reload or clear chat history seamlessly.
4. **Document Filter** — Scope queries to a specific document or search across all uploaded files.

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload and ingest a document |
| `GET` | `/api/documents` | List all uploaded documents |
| `DELETE` | `/api/documents/{id}` | Delete a document and its vectors |
| `POST` | `/api/chat` | Ask a RAG question & save to database |
| `GET` | `/api/chat/history` | Fetch persistent chat history |
| `DELETE` | `/api/chat/history` | Clear stored chat history |

## 📁 Project Structure

```
ragflow-ai-document-assistant/
├── frontend/           # React + Vite UI
│   ├── src/
│   │   ├── components/ # Upload, Chat, Message, Source
│   │   ├── services/   # Axios API client
│   │   ├── App.jsx     # Root layout & state
│   │   └── main.jsx    # Entry point
│   └── Dockerfile
├── backend/            # FastAPI + LangChain RAG
│   ├── app/
│   │   ├── api/        # REST routes (documents.py, chat.py)
│   │   ├── rag/        # RAG modules (embeddings, chain, vectorstore, retriever)
│   │   ├── main.py     # FastAPI app entry & lifecycle
│   │   ├── database.py # SQLAlchemy engine & Session
│   │   ├── models.py   # PostgreSQL models (Document, ChatMessage)
│   │   └── schemas.py  # Pydantic validation schemas
│   ├── uploads/        # Stored uploaded files
│   ├── .env            # Provider & database environment config
│   └── Dockerfile
└── docker-compose.yml  # Docker Compose orchestration
```

## 📜 License

MIT

