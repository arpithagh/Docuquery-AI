# 📚 DocuQuery AI

A production-grade document intelligence system. Upload PDFs and have a grounded conversation with them — powered by Retrieval-Augmented Generation (RAG) with semantic search, multi-document retrieval, conversation memory, and source citations.

**Live demo:** [your-render-url-here]
**Backend API:** [your-render-backend-url-here]

---

## What Makes This Different

Most RAG tutorials stop at single-document Q&A with naive top-k retrieval. This project goes further:

- **Per-document retrieval guarantee** — when multiple PDFs are uploaded, a naive global similarity search tends to favor whichever document scores highest for a given query, silently ignoring the others. This system queries each document individually and merges results, so every uploaded document is represented in the answer — verified by testing cross-document comparison questions.
- **Grounded, no-hallucination answers** — the system explicitly says "I couldn't find that in the uploaded documents" when context is insufficient, rather than guessing. Verified by asking out-of-scope questions (e.g. general knowledge) and confirming refusal.
- **Context-aware response formatting** — the LLM is prompted to detect "why/how/explain" style questions and respond with bullet points plus a short explanation per point, instead of a bare list, while simple factual questions get direct 1-3 sentence answers.

---

## Architecture

```
Upload Flow:
PDF → Text Extraction → Chunking (sliding window + overlap) → Embedding → ChromaDB

Query Flow:
Question → Embed Query → Per-Document Similarity Search → Merge & Re-rank
    → Inject Context into Prompt → Groq (Llama 3.3 70B) → Grounded Answer + Citations
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | FastAPI |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector DB | ChromaDB (persistent) |
| LLM | Groq API (Llama 3.3 70B) |
| PDF Parsing | pdfplumber |
| Frontend | Streamlit |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/arpithagh/docuquery-ai
cd docuquery-ai
pip install -r requirements.txt
```

### 2. Get a free Groq API key

Sign up at [console.groq.com](https://console.groq.com), create a key, then:

```bash
cp .env.example .env
# paste your key into .env
```

### 3. Run

```bash
# Terminal 1
cd backend
python main.py

# Terminal 2
cd frontend
streamlit run app.py
```

Visit `http://localhost:8501`

---

## Features

- Multi-document upload and indexing
- Semantic search via sentence embeddings + cosine similarity
- Per-document retrieval guarantee (see "What Makes This Different")
- Conversation memory across a session
- Source citations with chunk counts shown per answer
- Adjustable retrieval depth (chunks-to-context slider)
- Document management (upload, list, delete)
- Grounded refusal on out-of-scope questions

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload and index a PDF |
| `/ask` | POST | Ask a question, returns answer + sources |
| `/documents` | GET | List indexed documents with chunk counts |
| `/documents` | DELETE | Remove a document and its chunks |
| `/clear-history` | POST | Clear conversation memory for a session |

## Known Limitations

- ChromaDB runs as a local persistent store, not a managed cloud vector DB — fine for a portfolio/demo scale, would need migration (e.g. Pinecone, Weaviate) for production traffic
- No authentication — single shared knowledge base, not multi-tenant
- PDF only — no DOCX/TXT/HTML ingestion yet

## What I'd Build Next

- Re-ranking retrieved chunks with a cross-encoder before sending to the LLM
- Streaming responses token-by-token instead of waiting for the full answer
- Page-number citations, not just filename
