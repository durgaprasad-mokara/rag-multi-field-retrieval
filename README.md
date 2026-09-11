# RAG Assistant — Enterprise Multi-Modal Intelligence & Voice RAG Platform

An advanced, production-ready Retrieval-Augmented Generation (RAG) system with an embedded AI/ML Intelligence Layer. It is designed to handle complex multi-field retrieval, diverse document formats, and voice-based interactions while ensuring high accuracy and observability.

---

## 🌟 Key Features

- **AI/ML Intelligence Layer**: Zero-dependency (no heavy ML frameworks) query classification, intent detection, and relevance scoring powered by embeddings and deterministic logic.
- **LangGraph Orchestration**: A resilient, state-machine-driven RAG workflow supporting dynamic query expansion, conditional retries for missing fields, and parallel execution.
- **Observability & Tracing**: Fully integrated LangSmith tracing for step-by-step debugging, prompt evaluation, and RAG pipeline diagnostics.
- **Multi-Modal Retrieval**: Intelligently routes queries using targeted, field-level, or broad summary strategies based on user intent.
- **Extensive Document Processing**: Supports parsing, chunking, and embedding for PDF, DOCX, TXT, CSV, XLSX, JSON, and Video/Audio (via built-in STT/TTS).
- **Safe Fallbacks**: Guaranteed "Do No Harm" architecture that gracefully falls back to a deterministic RAG pipeline if the AI/ML layer encounters an issue.

---

## 🏗️ Architecture

The system is built on a modern, scalable tech stack:

- **Frontend**: React (Vite) providing a rich, interactive chat and document management interface.
- **Backend**: FastAPI (Python) serving robust async APIs for processing and chat.
- **Vector Database**: Qdrant (`rag-multi-field-retrieval` collection) for high-performance vector search.
- **Relational Database**: PostgreSQL (via Supabase) for tracking chat sessions, document metadata, and categories.
- **Embeddings**: `BAAI/bge-small-en-v1.5` (via FastEmbed) for fast, local embedding generation.
- **LLM Engine**: Configurable (defaults to local-grounded models).
- **Orchestration**: LangChain & LangGraph for complex tool use and conversational state.

```mermaid
graph TD
    A["React Frontend / Voice"] --> B["FastAPI /api/chat"]
    B --> C["LangGraph Workflow"]
    
    subgraph "AI/ML Intelligence Layer (NEW)"
        D["🤖 Classify Query"]
        E["🤖 Detect Intent"]
        F["🤖 Route Query"]
        G["🤖 Score Relevance"]
        H["🤖 Estimate Confidence"]
        I["🤖 Expand Query"]
    end
    
    subgraph "LangChain RAG Pipeline"
        J["Field Detection"]
        K["Qdrant Retrieval"]
        L["Deduplication"]
        M["Extraction (LLM)"]
        N["Answer Generation"]
    end
    
    C --> D
    D --> E
    E --> F
    F --> J
    J --> K
    K --> G
    G -->|"Low Confidence"| I
    I -.->|"Retry"| K
    G -->|"OK"| L
    L --> M
    M --> N
    N -->|"Validation"| H
```

---

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Supabase (PostgreSQL) Database URL
- (Optional) LangSmith API Key for tracing

### 1. Environment Setup

Clone the repository and navigate to the project directory.

In the `backend` folder, copy the example environment file:
```bash
cp backend/.env.example backend/.env
```

Update `backend/.env` with your actual Supabase database URL and your LangSmith API key (if you want tracing enabled).

### 2. Run the Application

The entire application is containerized for seamless deployment. Start it using Docker Compose from the root directory:

```bash
docker-compose up -d --build
```

### 3. Access the Services

Once the containers are running, you can access the different components:
- **Web App**: [http://localhost:3000](http://localhost:3000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## 📁 Project Structure

```
rag-multi-field-retrieval/
├── docker-compose.yml       # Multi-container deployment config
├── backend/
│   ├── .env                 # Environment configurations
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Backend container definition
│   └── app/
│       ├── main.py          # FastAPI application entry point
│       ├── database.py      # SQLAlchemy & Supabase connection
│       ├── models.py        # Database models (Documents, Sessions)
│       ├── schemas.py       # Pydantic API validation schemas
│       ├── api/             # API route handlers
│       │   ├── chat.py      # Chat and LLM interaction endpoints
│       │   ├── documents.py # Document upload and indexing endpoints
│       │   ├── debug.py     # Qdrant inspection tools
│       │   └── ...
│       └── rag/             # Core RAG logic
│           ├── chain.py            # LangChain LCEL implementation
│           ├── graph_state.py      # LangGraph state typed dict
│           ├── graph_workflow.py   # LangGraph state machine orchestrator
│           ├── intelligence.py     # AI/ML intelligence layer (Intent, Routing)
│           ├── loader.py           # Multi-format document loading
│           ├── chunker.py          # Recursive text chunking
│           ├── vectorstore.py      # Qdrant integration
│           ├── deduplicator.py     # Context compression and semantic deduplication
│           ├── embeddings.py       # FastEmbed embedding initialization
│           ├── multi_field.py      # Structured field extraction logic
│           └── video_processor.py  # Audio/Video STT (Whisper) processing
└── frontend/
    ├── package.json         # React dependencies
    ├── Dockerfile           # Frontend container definition
    └── src/                 
        ├── App.jsx          # Main React component
        ├── components/      # UI Components (Chat, Upload, Sidebar)
        └── services/        # Axios API client integrations
```

---

## 📡 Key API Endpoints

The backend provides several RESTful endpoints. View the full interactive documentation at `/docs`.

- `POST /api/chat` - Submits a query to the LangGraph RAG pipeline.
- `POST /api/documents/upload` - Uploads, parses, chunks, and indexes a new document into Qdrant.
- `GET /api/documents` - Lists all processed documents and their status.
- `GET /api/categories` - Retrieves the document taxonomy hierarchy.

---

## 📊 Observability with LangSmith

To enable deep insights into how the RAG pipeline is performing, provide your LangSmith API key in `backend/.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=RAG-Multi-Field-Retrieval
```

When enabled, all query classifications, intent detections, vector retrievals, LLM prompts, and final answers are automatically logged to your LangSmith dashboard under the specified project name. This is crucial for debugging complex multi-field extractions and monitoring prompt performance.
