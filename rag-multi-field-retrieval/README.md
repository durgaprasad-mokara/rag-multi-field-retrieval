# 🤖 RAG Assistant — Enterprise Multi-Modal Intelligence & Voice RAG Platform

A production-ready **Retrieval-Augmented Generation (RAG)** application designed with **Category & Document-Type Taxonomy**, **Strict Document-Locked Retrieval**, **Video & Audio Understanding**, **Multi-Field Query Decomposition**, and an **Enterprise Dark-Themed Dashboard with Voice Agent Synchronization**.

Upload documents and video files under structured categories and interact through high-precision AI question-answering with exact source citations and timestamped video references, powered by **100% free offline CPU execution** or cloud LLM providers.

---

## 🌟 Key Features

- **Categorized Taxonomy Navigation**: 17 pre-seeded domain categories (Company, Education, Business, Marketing, Projects, Research, Students, Courses, etc.) with nested sub-types.
- **Strict Sidebar Isolation**: The left sidebar functions strictly as a categorical navigation tree. Uploaded files remain internal data assets and never clutter the sidebar navigation.
- **Video & Audio Ingestion Pipeline**: Full support for `.mp4`, `.webm`, `.mov`, `.mkv`, `.avi`, `.m4a`, `.wav`, and `.mp3` with FFmpeg audio extraction and offline Whisper transcription.
- **Timestamp-Preserved Smart Chunking**: Automatic speech-to-text with segment-level timestamps (`04:21–05:10`), transcript stutter cleaning, topic detection, and semantic chunking.
- **Video-Grounded Question Answering**:
  - **Video Summaries**: Generates structured topic timelines (*"Summarize the video"* / *"What is this video about?"*).
  - **Topic Discovery**: Identifies all concepts and sections (*"What topics are covered in this video?"*).
  - **Timestamp Queries**: Answers questions tied to specific times (*"What is discussed around 5 minutes?"*).
  - **Semantic Video Search**: Retrieves exact spoken explanations without requiring keyword matches (*"What does the video explain about functions?"*).
- **Document-Locked RAG Retrieval**: Queries are isolated strictly to the active document/video (`metadata.document_id`). Information from unrelated documents or categories is never leaked.
- **Multi-Field Query Decomposition**: Decomposes multi-intent questions (e.g. *"Give me skills, education, projects, email, phone, and GitHub"*) into sub-queries, retrieving and answering each field for **100% required-field coverage**.
- **Synchronized Chat & Voice Agent**:
  - **Single Answer Pipeline**: Both typing and voice questions share the exact same grounded RAG pipeline.
  - **Voice Response Control**: Toggle `🔊 Voice: ON / OFF` directly from the dashboard header (default: ON).
  - **English Speech Synthesis (TTS)**: Automatically speaks the validated answer in English using browser Web Speech TTS.
  - **Instant Speech Interruption**: New questions immediately halt ongoing speech playback.
- **Standardized Anti-Hallucination Fallback**: If requested information is absent from the selected document or video, the system strictly returns and speaks:
  > `"This answer is not available in the selected document. Please ask a question related to the available content."`
- **Expandable Page-Level & Timestamp Citations**: Transparent responses with expandable source drawer showing document name, page numbers, video timestamps (`⏱ 04:21–05:10`), and topic pills.
- **100% Free & Offline Execution**: Runs locally on CPU via FastEmbed (`BAAI/bge-small-en-v1.5`), Faster-Whisper, and Local Grounded Extractor. No paid API keys required by default.
- **Multi-Provider LLM & Embedding Support**: Switch effortlessly between Local, OpenAI, OpenRouter, and Ollama with `.env` configurations.

---

## 🏗️ System Architecture

```
                    USER
                     │
             ┌───────┴───────┐
             │               │
          TYPING         VOICE (🎤)
             │               │
             │        Speech-to-Text
             │               │
             └───────┬───────┘
                     ▼
               USER QUESTION
                     │
                     ▼
           FastAPI Backend (:8000)
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
   PostgreSQL 16  LangChain  Qdrant Vector DB
 (Metadata/Chat)     │          (:6333)
                     │   (Document-Locked Chunks)
        ┌────────────┴────────────┐
        ▼                         ▼
 FastEmbed ONNX              LLM Engine
(BAAI/bge-small-en-v1.5)  (Local / OpenAI / Ollama)
        │                         │
        └────────────┬────────────┘
                     ▼
             ANSWER VALIDATION
                     │
              ┌──────┴──────┐
              ▼             ▼
         CHAT DISPLAY    ENGLISH TTS
         (Always Shown) (When Voice: ON)
```

---

## 🔄 Document & Video Ingestion Flow

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 1. Select Cat   │  ──▶  │ 2. Select Type  │  ──▶  │ 3. Upload File  │
│ Choose domain   │       │ Pick sub-type   │       │ Docs or Videos  │
│ category        │       │ under category  │       │ (.pdf, .mp4...) │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
                                                             ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 6. Text + Voice │  ◀──  │ 5. Ask Question │  ◀──  │ 4. Process & Idx│
│ Validated Ans & │       │ Typing / Voice  │       │ FFmpeg, Whisper,│
│ Source Citation │       │ natural query   │       │ Chunker, Qdrant │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

1. **Select Category**: Choose domain (e.g., *Company*, *Education*, *Courses*, *Research*).
2. **Select Type**: Choose relevant document type (e.g., *HR Policies*, *Python*, *Study Materials*).
3. **Upload File**: Select documents (`.pdf`, `.docx`, `.txt`...) or video files (`.mp4`, `.webm`, `.mov`, `.mkv`...).
4. **Process & Index**:
   - **Documents**: Cleaned of OCR noise, structured into semantic chunks, and embedded.
   - **Videos**: Audio extracted with FFmpeg, transcribed with Faster-Whisper, cleaned of stutter, topic-detected, timestamp-chunked, and embedded into Qdrant.
5. **Ask Questions**: Submit natural language queries via typing or voice scoped strictly to the uploaded document or video.
6. **Get Synchronized Answers**: Receive precise, hallucination-free answers in chat and spoken in English via the Voice Agent with expandable source citations.

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
| **Frontend** | React 18 + Vite | Modern dark theme, voice input (STT), voice output (TTS), voice controls |
| **Styling** | Vanilla CSS Design System | Custom CSS variables, responsive layout, fluid micro-interactions |
| **Backend** | FastAPI (Python 3.11) | Async REST API, query decomposition, background ingestion |
| **Video & Audio** | FFmpeg + Faster-Whisper | Audio extraction, speech-to-text with timestamps on CPU (`int8`) |
| **Embeddings** | FastEmbed (Default) / OpenAI | FastEmbed `BAAI/bge-small-en-v1.5` (ONNX on CPU) or `text-embedding-3-small` |
| **Vector DB** | Qdrant | High-performance vector database with metadata filtering |
| **Relational DB** | PostgreSQL 16 | Stores category taxonomy, document metadata & chat message history |
| **RAG & NLP** | LangChain Core | Recursive chunking, Jaccard deduplication, retrieval chaining |
| **Containerization** | Docker & Docker Compose | Multi-service orchestration (`frontend`, `backend`, `db`, `qdrant`) |

---

## 📄 Supported Formats

| Format | Extensions | Processing Engine |
|---|---|---|
| **Video** | `.mp4`, `.webm`, `.mov`, `.mkv`, `.avi`, `.m4v`, `.flv` | FFmpeg audio extraction + Faster-Whisper timestamp transcription |
| **Audio** | `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac` | Faster-Whisper STT with topic detection & semantic chunking |
| **PDF** | `.pdf` | `pypdf` with page-level tracking |
| **Word** | `.docx`, `.doc` | `python-docx` paragraph extractor |
| **Text** | `.txt`, `.log` | UTF-8 plain text loader |
| **Markdown** | `.md` | Markdown text splitter |
| **Spreadsheets** | `.csv`, `.xlsx`, `.xls` | Delimited row & table parser |
| **Web & Data** | `.html`, `.htm`, `.json` | Unstructured text & JSON cleaner |

---

## 🚀 How to Run the Project

### Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) & Docker Compose (Recommended)
- *OR* for Local Setup without Docker:
  - Python 3.11 or 3.12 + [FFmpeg](https://ffmpeg.org/download.html)
  - Node.js 18+ & npm
  - PostgreSQL 16 & Qdrant vector database running locally

---

### 🐳 Method 1: Run with Docker Compose (Recommended)

This is the easiest and fastest way to start the entire full-stack system (`frontend`, `backend`, `db`, `qdrant`) in a single command.

#### 1. Clone & Navigate to Project Directory

```bash
git clone https://github.com/durgaprasad-mokara/rag-multi-field-retrieval.git
cd rag-multi-field-retrieval
```

#### 2. Start All Containers

```bash
docker compose up -d --build
```

#### 3. Access the Running Services

| Service | URL / Port | Description |
|---|---|---|
| 🖥️ **Web Dashboard (Frontend)** | **[http://localhost:3000](http://localhost:3000)** | React 18 + Vite UI with Voice Agent |
| ⚡ **Backend API Docs (Swagger)** | **[http://localhost:8000/docs](http://localhost:8000/docs)** | Interactive FastAPI OpenAPI documentation |
| 🔍 **Qdrant Vector Dashboard** | **[http://localhost:6333/dashboard](http://localhost:6333/dashboard)** | Vector database collection manager |
| 🗄️ **PostgreSQL Database** | `localhost:5433` | Relational metadata (`raguser` / `ragpass` / `ragdb`) |

#### 4. Useful Docker Commands

```bash
# View real-time logs for all services
docker compose logs -f

# View logs for backend only
docker compose logs -f backend

# Stop all running containers
docker compose down

# Rebuild containers after code changes
docker compose up -d --build
```

---

### 💻 Method 2: Run Locally (Without Docker)

If you prefer running services directly on your host machine:

#### 1. Start Prerequisites (PostgreSQL & Qdrant)

Make sure PostgreSQL is running on port `5432` (or `5433`) and Qdrant is running on port `6333`:

```bash
# Run Qdrant standalone
docker run -p 6333:6333 qdrant/qdrant
```

#### 2. Start Backend (FastAPI)

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Start Frontend (React + Vite)

In a separate terminal:

```bash
cd frontend

# Install Node modules
npm install

# Start Vite dev server
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

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

### Documents & Videos
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload document or video bound to `category_id` & `type_id` |
| `GET` | `/api/documents` | List documents (supports category/type filter query params) |
| `GET` | `/api/documents/{id}` | Get document metadata |
| `DELETE` | `/api/documents/{id}` | Delete document/video from PostgreSQL & Qdrant vectors |

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
# Test Video Understanding, Audio Transcription & Timestamp-Grounded QA
docker compose exec backend python -m app.test_video_rag

# Test End-to-End Video Ingestion & API Chat Verification
docker compose exec backend python -m app.test_video_e2e

# Test Multi-Field Query Decomposition & 100% Required-Field Coverage
docker compose exec backend python -m app.test_multi_field_rag

# Test Section-Aware Parsing & Extraction Precision
docker compose exec backend python -m app.test_rag_output_fix

# Test Document Cleaning, Smart Chunking & Latency Targets
docker compose exec backend python -m app.test_rag_optimizations

# Test Complete Hierarchical Workflow (Category -> Type -> Document -> Chat)
docker compose exec backend python -m app.test_hierarchical_flow

# Run Universal Full Integration Test Suite
docker compose exec backend python -m app.test_full_suite
```

---

## 📁 Repository Structure

```
RAG-Assistant/
├── frontend/                     # React 18 + Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── SidebarHierarchy.jsx     # Categorical taxonomy navigation & dropzone
│   │   │   ├── CategoryGrid.jsx         # Domain categories grid
│   │   │   ├── Chat.jsx                 # Chat workspace, Web Speech STT/TTS & Voice toggle
│   │   │   ├── Message.jsx              # Message bubbles with latency metric badge
│   │   │   ├── Source.jsx               # Expandable citation drawer with timestamps & topics
│   │   │   └── Upload.jsx               # Document & Video upload modal/component
│   │   ├── services/
│   │   │   └── api.js                   # Axios client for all API routes
│   │   ├── App.jsx                      # State orchestration (Nav vs Doc isolation)
│   │   ├── App.css                      # Production dark design system & CSS variables
│   │   └── main.jsx                     # Entry point
│   ├── package.json
│   ├── vite.config.js                   # Vite config with Docker watch polling
│   └── Dockerfile
├── backend/                      # FastAPI Python Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── categories.py            # Category & DocumentType endpoints
│   │   │   ├── documents.py             # Document/Video upload & management
│   │   │   └── chat.py                  # Document-locked RAG, sessions & metrics
│   │   ├── rag/
│   │   │   ├── video_processor.py       # FFmpeg extraction, Whisper STT & semantic chunker
│   │   │   ├── cleaner.py               # Text cleaning, OCR noise removal & deduplication
│   │   │   ├── chunker.py               # Document-type aware smart chunker with metadata
│   │   │   ├── multi_field.py           # Multi-field query decomposition & coverage check
│   │   │   ├── chain.py                 # Grounded RAG chain & local extractor
│   │   │   ├── deduplicator.py          # Jaccard chunk & sentence deduplication
│   │   │   ├── embeddings.py            # FastEmbed / OpenAI embeddings
│   │   │   ├── loader.py                # Multi-format document & video parser
│   │   │   ├── prompts.py               # Strict QA system prompts
│   │   │   ├── retriever.py             # Qdrant document-id filtered retriever
│   │   │   └── vectorstore.py           # Qdrant collection initialization & indexing
│   │   ├── database.py                  # SQLAlchemy engine & session maker
│   │   ├── models.py                    # PostgreSQL ORM models
│   │   ├── schemas.py                   # Pydantic v2 schemas
│   │   ├── main.py                      # FastAPI app & taxonomy seeder
│   │   ├── test_video_rag.py            # Video understanding unit tests
│   │   ├── test_video_e2e.py            # Video end-to-end API integration tests
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
