# 🤖 RAG Assistant — Enterprise Document Intelligence & RAG Platform

A production-ready **Retrieval-Augmented Generation (RAG)** application designed with **Category & Document-Type Taxonomy**, **Strict Document-Locked Retrieval**, **Multi-Field Query Decomposition**, and an **Enterprise Dark-Themed Dashboard**.

Upload documents under structured categories and interact through high-precision AI question-answering with exact source citations, powered by **100% free offline CPU execution** or cloud LLM providers.

---

## 🌟 Key Features

- **Categorized Taxonomy Navigation**: 17 pre-seeded domain categories (Company, Education, Business, Marketing, Projects, Research, Students, Courses, etc.) with nested sub-types.
- **Strict Sidebar Isolation**: The left sidebar functions strictly as a categorical navigation tree. Uploaded files remain internal data assets and never clutter the sidebar navigation.
- **Document-Locked RAG Retrieval**: Queries are isolated strictly to the active document (`metadata.document_id`). Information from unrelated documents or categories is never leaked.
- **Multi-Field Query Decomposition**: Decomposes multi-intent questions (e.g. *"Give me skills, education, projects, email, phone, and GitHub"*) into sub-queries, retrieving and answering each field for **100% required-field coverage**.
- **Voice & Typing Input**: Native browser Web Speech API voice input with real-time speech-to-text and pulsing audio recording indicators.
- **Active Document Context Header**: Compact, dynamic header displays `Category: <Name> | Type: <Type> | File: <Filename>` with tooltip and truncation.
- **Document Text Cleaning & Smart Chunking**: Normalizes whitespace, cleans OCR punctuation noise, and chunks along document-type boundaries (headings, tables, lists).
- **Anti-Hallucination & Fallback**: If an answer is not contained in the selected document, the system explicitly returns: `"Information not found in the selected document."` or `"Not available in the selected document."`
- **Expandable Page-Level Citations**: Transparent responses with expandable source drawer showing document name, chunk text, and page references.
- **100% Free & Offline Execution**: Runs locally on CPU via FastEmbed (`BAAI/bge-small-en-v1.5`) and Local Grounded Extractor. No paid API keys required by default.
- **Multi-Provider LLM & Embedding Support**: Switch effortlessly between Local, OpenAI, OpenRouter, and Ollama with `.env` configurations.
- **Multi-Format Ingestion**: Supports `.pdf`, `.docx`, `.doc`, `.txt`, `.md`, `.csv`, `.xlsx`, `.xls`, `.html`, `.json`, and `.log`.

---

## 🏗️ System Architecture

```
                                  USER
                                    │
                                    ▼
                     React 18 + Vite Frontend (:3000)
                     (Modern Dark UI / Voice Input / Context Header)
                                    │
                                    │ HTTP REST API
                                    ▼
                           FastAPI Backend (:8000)
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  PostgreSQL 16                 LangChain                 Qdrant Vector DB
(Metadata & Chat)                   │                        (:6333)
                                    │                  (Document-Locked Chunks)
                      ┌─────────────┴─────────────┐
                      ▼                           ▼
               FastEmbed ONNX                LLM Engine
          (BAAI/bge-small-en-v1.5)      (Local / OpenAI / Ollama)
                      │                           │
                      └─────────────┬─────────────┘
                                    ▼
                         Answer + Source Citations
```

---

## 🔄 Document Ingestion & RAG Flow

The application follows a structured 6-step lifecycle:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 1. Select Cat   │  ──▶  │ 2. Select Type  │  ──▶  │ 3. Upload Doc   │
│ Choose main     │       │ Pick sub-type   │       │ Drag & drop or  │
│ domain category │       │ under category  │       │ Browse Files    │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
                                                             ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 6. Get Answers  │  ◀──  │ 5. Ask Question │  ◀──  │ 4. Process & Idx│
│ Exact answer &  │       │ Typing / Voice  │       │ Clean, chunk,   │
│ source citation │       │ natural query   │       │ embed & index   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

1. **Select Category**: Choose domain (e.g., *Company*, *Education*, *Research*).
2. **Select Type**: Choose relevant document type (e.g., *HR Policies*, *Study Materials*).
3. **Upload Document**: Select a file via the native file browser or drag-and-drop.
4. **Process & Index**: The file text is cleaned of OCR noise, smart-chunked, embedded, and indexed into Qdrant with metadata payload (`document_id`, `category_id`, `type_id`).
5. **Ask Questions**: Submit natural language queries via typing or voice scoped strictly to the uploaded document.
6. **Get Answers**: Receive precise, hallucination-free answers with expandable source citations and latency performance metrics.

---

## 🗂️ Pre-Seeded Taxonomy (17 Categories)

| Category | Example Document Types |
|---|---|
| **Company** | HR & Employee Details, Company Policies, Projects, Internal Documents, Deployment & Technical, Benefits, Finance |
| **Education** | Study Materials, Research Papers, Courses, Subjects, Lecture Notes, Assignments, Syllabus, Textbooks |
| **Business** | Business Plans, Business Reports, Business Strategy, Financial Documents, Sales Documents, Market Analysis |
| **Marketing** | Marketing Strategy, Campaigns, Market Research, Advertising, Social Media Marketing, SEO, Email Marketing |
| **Projects** | Project Documentation, Requirements (PRD), Plans, Technical Docs, Architecture, API Documentation |
| **Research** | Research Papers, Research Reports, Literature Reviews, Research Notes, Datasets, Experiments, Case Studies |
| **Study** | Study Materials, Study Notes, Lecture Notes, Exam Preparation, Question Papers |
| **Students** | Student Profile, Education Details, Marks / Grades, Attendance, Assignments, Projects, Resume |
| **Courses** | Python, C/C++, Java, JavaScript, SQL, Data Science, Machine Learning, Deep Learning, Cloud Computing, DevOps |
| **Subjects** | Mathematics, Physics, Chemistry, Computer Science, Data Structures, Operating Systems, Computer Networks |
| **Assessments**| Exams, Tests, Quizzes, Technical Assessments, Interview Assessments, Performance Assessments |
| **Notes** | Study Notes, Lecture Notes, Technical Notes, Meeting Notes, Project Notes, Research Notes |
| **Resume / CV** | Student Resume, Professional Resume, Developer Resume, Technical Resume, Executive Resume |
| **News** | Technology News, Business News, Education News, Financial News, AI News, Science News |
| **Articles** | Technical Articles, Business Articles, Research Articles, Blog Articles, Opinion Pieces |
| **Social Media**| LinkedIn, Instagram, X / Twitter, YouTube, Social Media Posts, Campaign Analytics |
| **Other** | General Documents, Custom Types, Miscellaneous Files |

---

## 🛠️ Tech Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | React 18 + Vite | Modern dark theme, dynamic categories, voice input & locked workspace |
| **Styling** | Vanilla CSS Design System | Custom CSS variables, responsive layout, fluid micro-interactions |
| **Backend** | FastAPI (Python 3.11) | Async REST API, query decomposition, background ingestion |
| **Embeddings** | FastEmbed (Default) / OpenAI | FastEmbed `BAAI/bge-small-en-v1.5` (ONNX on CPU) or `text-embedding-3-small` |
| **Vector DB** | Qdrant | High-performance vector database with metadata filtering |
| **Relational DB** | PostgreSQL 16 | Stores category taxonomy, document metadata & chat message history |
| **RAG & NLP** | LangChain Core | Recursive chunking, Jaccard deduplication, retrieval chaining |
| **Containerization** | Docker & Docker Compose | Multi-service orchestration (`frontend`, `backend`, `db`, `qdrant`) |

---

## 📄 Supported Formats

| Format | Extension | Processing Engine |
|---|---|---|
| **PDF** | `.pdf` | `pypdf` with page-level tracking |
| **Word** | `.docx`, `.doc` | `python-docx` paragraph extractor |
| **Text** | `.txt`, `.log` | UTF-8 plain text loader |
| **Markdown** | `.md` | Markdown text splitter |
| **Spreadsheets** | `.csv`, `.xlsx`, `.xls` | Delimited row & table parser |
| **Web & Data** | `.html`, `.htm`, `.json` | Unstructured text & JSON cleaner |

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose installed.

### 1. Clone & Start Containers

```bash
git clone https://github.com/durgaprasad-mokara/RAG-Assistant.git
cd RAG-Assistant

# Start all 4 containers (Postgres, Qdrant, FastAPI backend, React frontend)
docker compose up -d --build
```

### 2. Access the Application

- **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qdrant Vector Console**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## ⚙️ Configuration (`backend/.env`)

Configure providers in `backend/.env`:

### Option A: Local & Free Execution (Default)
Runs completely offline on CPU with zero external API dependencies:

```env
DATABASE_URL=postgresql://raguser:ragpass@db:5432/ragdb
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=rag_documents

EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

LLM_PROVIDER=local
LLM_MODEL=local-grounded
```

### Option B: OpenAI Models
```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-proj-your-openai-key
```

### Option C: OpenRouter
```env
LLM_PROVIDER=openrouter
LLM_MODEL=meta-llama/llama-3.2-1b-instruct:free
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key
```

### Option D: Local Ollama
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
OLLAMA_HOST=http://host.docker.internal:11434
```

---

## 📡 REST API Reference

### Categories & Document Types
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/categories` | List all categories with nested document types |
| `POST` | `/api/categories` | Create a new custom category |
| `GET` | `/api/categories/{id}` | Get specific category and its types |
| `PUT` | `/api/categories/{id}` | Update category details |
| `DELETE` | `/api/categories/{id}` | Delete a category |
| `POST` | `/api/categories/{id}/types` | Add a document type to a category |
| `DELETE` | `/api/categories/types/{type_id}` | Remove a document type |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload file bound to `category_id` & `type_id` |
| `GET` | `/api/documents` | List documents (supports category/type filter query params) |
| `GET` | `/api/documents/{id}` | Get document metadata |
| `DELETE` | `/api/documents/{id}` | Delete document from PostgreSQL & Qdrant vectors |

### Chat & Sessions
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/sessions` | Create a locked chat session for a `document_id` |
| `POST` | `/api/chat` | Send question and receive document-locked answer with sources & timing |
| `GET` | `/api/chat/history` | Retrieve persistent chat message history |
| `DELETE` | `/api/chat/history` | Clear chat messages for session/document |

---

## 🧪 Testing & Verification

Run automated test suites inside the backend container:

```bash
# Test Multi-Field Query Decomposition & 100% Required-Field Coverage
docker compose exec backend python -m app.test_multi_field_rag

# Test Section-Aware Parsing & Extraction Precision
docker compose exec backend python -m app.test_rag_output_fix

# Test Document Cleaning, Smart Chunking & Latency Targets
docker compose exec backend python -m app.test_rag_optimizations

# Test Complete Hierarchical Workflow (Category -> Type -> Document -> Chat)
docker compose exec backend python -m app.test_hierarchical_flow

# Run Universal Integration Test Suite
docker compose exec backend python -m app.test_full_suite
```

---

## 📁 Repository Structure

```
RAG-Assistant/
├── frontend/                     # React 18 + Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx              # Categorical taxonomy navigation tree
│   │   │   ├── CategoryGrid.jsx         # Main screen domain categories grid
│   │   │   ├── TypeDetailView.jsx       # Document type selection & upload area
│   │   │   ├── Chat.jsx                 # Chat workspace, context bar & Web Speech voice input
│   │   │   ├── Message.jsx              # Message bubbles with latency metric badge
│   │   │   └── Source.jsx               # Expandable citation drawer
│   │   ├── services/
│   │   │   └── api.js                   # Axios client for all API routes
│   │   ├── App.jsx                      # State orchestration (Nav vs Doc isolation)
│   │   ├── App.css                      # Production design system & CSS variables
│   │   └── main.jsx                     # Entry point
│   ├── package.json
│   ├── vite.config.js                   # Vite config with Docker watch polling
│   └── Dockerfile
├── backend/                      # FastAPI Python Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── categories.py            # Category & DocumentType endpoints
│   │   │   ├── documents.py             # Document upload & management
│   │   │   └── chat.py                  # Document-locked RAG, sessions & metrics
│   │   ├── rag/
│   │   │   ├── cleaner.py               # Text cleaning, OCR noise removal & deduplication
│   │   │   ├── chunker.py               # Document-type aware smart chunker with metadata
│   │   │   ├── multi_field.py           # Multi-field query decomposition & coverage check
│   │   │   ├── chain.py                 # Grounded RAG chain & local extractor
│   │   │   ├── deduplicator.py          # Jaccard chunk & sentence deduplication
│   │   │   ├── embeddings.py            # FastEmbed / OpenAI embeddings
│   │   │   ├── loader.py                # Multi-format document parser
│   │   │   ├── prompts.py               # Strict QA system prompts
│   │   │   ├── retriever.py             # Qdrant document-id filtered retriever
│   │   │   └── vectorstore.py           # Qdrant collection initialization & indexing
│   │   ├── database.py                  # SQLAlchemy engine & session maker
│   │   ├── models.py                    # PostgreSQL ORM models
│   │   ├── schemas.py                   # Pydantic v2 schemas
│   │   ├── main.py                      # FastAPI app & taxonomy seeder
│   │   ├── test_multi_field_rag.py      # Multi-field decomposition test suite
│   │   ├── test_rag_output_fix.py       # Section parsing test suite
│   │   ├── test_rag_optimizations.py    # Document cleaning & chunking test suite
│   │   ├── test_hierarchical_flow.py    # Hierarchical workflow test suite
│   │   └── test_full_suite.py           # Universal RAG integration test suite
│   ├── requirements.txt
│   ├── .env
│   └── Dockerfile
└── docker-compose.yml            # Multi-container Compose configuration
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
