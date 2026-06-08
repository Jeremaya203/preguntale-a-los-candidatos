# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Pregúntale a los Candidatos" is a citizen-facing electoral transparency platform for Colombia's 2026 elections. It lets voters query and compare policy proposals from two presidential candidates (Iván Cepeda Castro and Abelardo de la Espriella) against reference documents via an AI-powered chat interface with a retro pixel-art aesthetic.

## Commands

### Frontend (Next.js)
```bash
cd frontend
npm run dev       # Dev server on port 3000
npm run build     # Production build
npm run lint      # ESLint (Next.js core-web-vitals + TypeScript)
```

### Backend (FastAPI + Python)
```bash
# Run from project root with venv activated
source venv/bin/activate
python backend/indexer.py   # Index documents into ChromaDB + BM25 (run after adding documents)
python backend/main.py      # Dev server with uvicorn reload on port 8000
```

### Deployment
- **Backend → Railway**: push to GitHub, connect repo in Railway dashboard. Set `GROQ_API_KEY` as env var. Uses `railway.toml` + `Procfile`.
- **Frontend → Vercel**: connect repo, set root directory to `frontend/`, add env var `BACKEND_URL` pointing to the Railway backend URL.

### Environment Variables
- `backend/.env`: `GROQ_API_KEY=...` (required for LLM inference)
- `frontend/.env.local`: `BACKEND_URL=http://localhost:8000` (defaults to this if unset)

## Architecture

### Stack
- **Frontend**: Next.js 16 + React 19, TypeScript, Tailwind CSS 4
- **Backend**: FastAPI + Uvicorn, Groq API (`meta-llama/llama-4-scout-17b-16e-instruct`), ChromaDB, Sentence Transformers
- **Search**: 4-stage hybrid retrieval — BM25 → vector embeddings → RRF fusion → cross-encoder reranking
- **Deploy**: Railway via `railway.toml` (backend only); Vercel for frontend

### Request Flow

1. User types in the chat → `frontend/app/page.tsx` (monolithic component)
2. Frontend POSTs to `/api/chat` → Next.js route proxy in `frontend/app/api/chat/route.ts`
3. Proxy forwards to FastAPI `POST /chat` in `backend/main.py`
4. Backend detects policy dimension (keyword matching against 12 hardcoded dimensions)
5. Runs 4-stage hybrid search (`backend/search.py` — `HybridSearch` class)
6. Loads pre-calculated JSON analysis from `backend/analyses/<dimension>.json` if dimension matched
7. Constructs prompt with analysis + RAG fragments → streams Groq response back
8. Source metadata returned as an HTML comment appended to the stream

The `/analyze` endpoint follows the same dimension detection → pre-calc lookup → Groq fallback pattern, but returns multi-section structured analysis rather than conversational chat.

### Key Files

| File | Role |
|---|---|
| `backend/main.py` | FastAPI app, `/chat`, `/analyze`, `/health` endpoints |
| `backend/search.py` | `HybridSearch` class — 4-stage retrieval logic |
| `backend/indexer.py` | Document ingestion pipeline (PDF/DOCX/TXT → ChromaDB + BM25) |
| `backend/utils.py` | Shared `tokenize()` function + Spanish stopwords (used by both indexer and search) |
| `backend/analyses/*.json` | Pre-calculated analyses for 12 policy dimensions |
| `frontend/app/page.tsx` | Entire UI: chat tabs, candidate filter, streaming display |
| `frontend/app/api/*/route.ts` | Next.js proxy routes to backend |

### Search Pipeline (backend/search.py)

The `HybridSearch` class performs:
1. **BM25** — keyword retrieval (`rank_bm25.BM25Okapi`)
2. **Vector** — semantic similarity via ChromaDB + `paraphrase-multilingual-MiniLM-L12-v2`
3. **RRF fusion** — merges rankings using `1/(60 + rank)` to avoid bias toward either method
4. **Cross-encoder reranking** — `mmarco-mMiniLMv2-L12-H384-v1` for final precision scoring on top 40 candidates

### Indexing Pipeline (backend/indexer.py)

Documents go through: extraction (PyMuPDF/python-docx) → aggressive text cleaning (regex strips page numbers, hyphenation artifacts) → 200-word chunks with 100-word (50%) overlap → embedding → ChromaDB + BM25 index + metadata pickle.

Each stored chunk carries metadata: `title`, `source`, `tipo` (`candidato`/`referencia`), `candidato`, `lang`.

Document folder structure under `backend/documents/`:
- `candidatos/ivan-cepeda/` → tipo=candidato, candidato=ivan-cepeda
- `candidatos/abelardo/` → tipo=candidato, candidato=abelardo
- `referencia/` → tipo=referencia (optionally `referencia/en/` for English docs)

After adding any documents to `backend/documents/`, re-run `python backend/indexer.py` to rebuild `chroma_db/` and `bm25_index.pkl`.

### Policy Dimensions

12 dimensions detected via keyword matching in `backend/main.py` (`DIM_KEYWORDS`) and mapped to JSON files via `DIM_MAP`:

| Slug (file name) | Display name |
|---|---|
| `economia` | Economía |
| `educacion` | Educación |
| `salud` | Salud |
| `paz_y_seguridad` | Paz y seguridad |
| `medio_ambiente` | Medio ambiente |
| `empleo` | Empleo |
| `vivienda` | Vivienda |
| `innovacion` | Innovación |
| `agricultura` | Agricultura |
| `justicia` | Justicia |
| `cultura` | Cultura |
| `infraestructura` | Infraestructura |

Pre-calculated analyses live in `backend/analyses/<slug>.json` with a `"content"` key.

### UI Notes

- `frontend/app/page.tsx` is a single monolithic component — no sub-component files yet
- Retro pixel-art aesthetic: Press Start 2P font, scanlines, animated video characters (jaguar/tigre per candidate)
- Candidate filter toggles which candidate's documents are included in RAG context
- Streaming responses decoded with `TextDecoder` and rendered incrementally via `useState`
- Sources are embedded in the stream as an HTML comment: `<!--SOURCES:[...]-->` and parsed client-side
