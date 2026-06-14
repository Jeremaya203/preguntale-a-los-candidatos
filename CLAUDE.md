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
  - `railway.toml` `buildCommand` pre-downloads both sentence transformer models at build time so cold starts don't incur download delays.
  - `backend/nixpacks.toml` installs CPU-only PyTorch (`--index-url https://download.pytorch.org/whl/cpu`) to keep the Railway image size manageable.
- **Frontend → Vercel**: connect repo, set root directory to `frontend/`, add env var `BACKEND_URL` pointing to the Railway backend URL.
  - Both proxy routes (`/api/chat`, `/api/analyze`) declare `export const maxDuration = 60` — required for Vercel to hold open streaming responses long enough.

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
7. Constructs prompt with analysis + RAG fragments → streams Groq response back (tokens are tooltip-annotated in flight)
8. Source metadata returned as an HTML comment appended to the stream

**Editorial guardrail (do not weaken without intent):** `SYSTEM_CHAT` in `main.py` carries a mandatory "format-bias" rule. Cepeda's program is ~400 pages of integrated narrative while Espriella's is ~15 pages of bullet points, which makes Espriella *look* "more specific." The prompt requires that any comparison of specificity/detail explicitly attributes the difference to document format, not proposal quality. Several recent commits exist solely to harden this — preserve it.

The `/analyze` endpoint follows the same dimension detection → pre-calc lookup → Groq fallback pattern, but returns multi-section structured analysis rather than conversational chat.

`/chat` additionally runs a **disinfo branch**: if the query matches `FC_KEYWORDS` (`is_disinfo_query`), it does a *balanced* fact-checking search across `contra_cepeda` + `contra_espriella` + `general` categories (independent of the candidate filter), appends `FC_RULES` to the system prompt, and injects the verifications into the user prompt. This enforces the editorial rule that disinformation about one candidate is never shown without the other side.

### Key Files

| File | Role |
|---|---|
| `backend/main.py` | FastAPI app, `/chat`, `/analyze`, `/health` endpoints; live tooltip annotation; disinfo/fact-checking routing |
| `backend/search.py` | `HybridSearch` class — 4-stage retrieval logic; filters by `candidato`, `tipo`, `categoria` |
| `backend/indexer.py` | Document ingestion pipeline (PDF/DOCX/TXT → ChromaDB + BM25) |
| `backend/utils.py` | Shared `tokenize()` function + Spanish stopwords (used by both indexer and search) |
| `backend/terminos_juridicos.py` | `TERMINOS` dict (legal/political term → plain-Spanish explanation). **Runtime dependency** imported by `main.py` for tooltip annotation |
| `backend/generar_analyses.py` | Batch regenerator for `analyses/<slug>.json` — retrieves real fragments via `HybridSearch` (candidate proposals + institutional viability docs) and synthesizes the mandatory 6-section structure via Groq. Grounded only on retrieved fragments (no external knowledge). Run `python backend/generar_analyses.py [slug ...]` (no args = all 12). It generates un-annotated text and then **auto-chains `anotar_analyses.py`** so the JSONs are never left without `{{term::explanation}}` markup (which would break frontend tooltips) |
| `backend/anotar_analyses.py` | One-shot CLI that pre-annotates `analyses/*.json` with `{{term::explanation}}` markup (backs up originals to `analyses_backup/`) |
| `backend/scraper_factcheck.py` | Downloads fact-checking articles → `documents/fact-checking/` (neutral sources only; `--balance` checks symmetry) |
| `backend/scraper_analisis.py` | Downloads independent analysis articles → `documents/analisis-independientes/` |
| `backend/analyses/*.json` | Pre-calculated analyses for 12 policy dimensions (already tooltip-annotated) |
| `frontend/app/page.tsx` | Entire UI: chat tabs, candidate filter, streaming display |
| `frontend/lib/parseTooltips.tsx` | Parses `{{term::explanation}}` markup in streamed text into `<LegalTooltip>` JSX (streaming-tolerant) |
| `frontend/components/LegalTooltip.tsx` | Click-to-open glossary popover for an annotated term |
| `frontend/app/api/*/route.ts` | Next.js proxy routes to backend |

**Scratch files & dirs — ignore / do not extend.** `backend/indexer_patch.py`, `backend/main_tooltips_patch.py` (already-applied patch notes), `backend/_dump_fragments.py` (one-off debug dump), and the stray `dfdsfsdfsd}` file are throwaway artifacts, not part of the running system. Likewise these directories are not live code: `cepeda-rag/` (empty), `backend/proyecto-cepeda/` (stray nested `venv`), and the analysis backups `backend/analyses_backup/` (originals from `anotar_analyses.py`) and `backend/analyses_snapshot_pre_regen_20260611/` (pre-regeneration snapshot — see memory note on the 2026-06-11 candidate-attribution fixes). Edit only `backend/analyses/*.json`.

### Search Pipeline (backend/search.py)

The `HybridSearch` class performs:
1. **BM25** — keyword retrieval (`rank_bm25.BM25Okapi`)
2. **Vector** — semantic similarity via ChromaDB + `paraphrase-multilingual-MiniLM-L12-v2`
3. **RRF fusion** — merges rankings using `1/(60 + rank)` to avoid bias toward either method
4. **Cross-encoder reranking** — `mmarco-mMiniLMv2-L12-H384-v1` for final precision scoring on top 15 candidates (`N_CANDIDATES` in `search.py` — reduced from 40 to cut ~3× latency on CPU)

`search()` accepts optional `candidato`, `tipo`, and `categoria` filters; these are applied to **both** the BM25 ranking and the ChromaDB `where` clause so the two halves of the hybrid stay consistent.

### Indexing Pipeline (backend/indexer.py)

Documents go through: extraction (PyMuPDF/python-docx) → aggressive text cleaning (regex strips page numbers, hyphenation artifacts) → 200-word chunks with 100-word (50%) overlap → embedding → ChromaDB + BM25 index + metadata pickle.

Each stored chunk carries metadata: `title`, `source`, `tipo` (`candidato`/`referencia`/`fact-checking`), `candidato`, `lang`. Fact-checking chunks additionally carry `categoria_fc`, `candidato_afectado`, `fuente`, `acusacion_falsa`, `veredicto`.

`tipo` is inferred purely from the **first path segment** under `documents/` (`detect_metadata`):
- `candidatos/ivan-cepeda/` → tipo=candidato, candidato=ivan-cepeda
- `candidatos/abelardo/` → tipo=candidato, candidato=abelardo
- `referencia/` → tipo=referencia (optionally `referencia/en/` for English docs)
- `fact-checking/<categoria>/` → tipo=fact-checking, categoria_fc = `contra_cepeda` | `contra_espriella` | `general`
- `analisis-independientes/` → tipo=referencia (independent press coverage, treated as reference)

**Fact-checking `.txt` format**: each file starts with a key:value header (`FUENTE`, `CANDIDATO_AFECTADO`, `TITULAR`, `ACUSACION_FALSA`, `VEREDICTO`, …) terminated by a `━━━` separator line. `parse_fc_header` lifts these into chunk metadata, and `TITULAR` overrides the auto-generated title.

After adding any documents to `backend/documents/`, re-run `python backend/indexer.py` to rebuild `chroma_db/` and `bm25_index.pkl`.

### Legal Tooltips

Technical/legal terms in responses are wrapped in `{{término::explicación}}` markup so the frontend can render click-to-open glossary popovers. Annotation is **deterministic and backend-side** (not asked of the LLM, which was inconsistent):

- The dictionary lives in `backend/terminos_juridicos.py` (`TERMINOS`). Keys are lowercase; matching is case-insensitive and longest-match-first (so "acción de tutela" wins over "tutela"). A few generic terms (`paz`, `ley`, `aval`) are excluded as visual noise.
- **Streamed `/chat`/`/analyze` responses**: `annotate_token_stream` in `main.py` buffers tokens and only flushes at safe cut chars (`.,;:!?…\n)`) — terms never contain those, so a multi-word term is never split across chunks. Each term is annotated **at most once per response** via a shared `ya_anotados` set.
- **Pre-calculated `analyses/*.json`**: annotated ahead of time by `python backend/anotar_analyses.py` (same engine → identical behavior). Re-run it whenever `TERMINOS` or an analysis file changes.
- **Frontend**: `parseTooltips.tsx` turns the markup into `<LegalTooltip>` JSX and is tolerant of partial markup mid-stream (an unclosed `{{tutela::expli` renders as plain text until the closing braces arrive).

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

The `/analyze` endpoint accepts `dimension` as either a Spanish display name (DIM_MAP key, e.g. `"educación"`) or a slug directly (e.g. `"educacion"`). It always falls back to Groq if no pre-calculated file exists for the resolved slug.

### UI Notes

- **Next.js version warning**: `frontend/AGENTS.md` (loaded by `frontend/CLAUDE.md`) explicitly warns that this Next.js version has breaking changes from standard Next.js — read `node_modules/next/dist/docs/` before writing any Next.js-specific code.
- `frontend/app/page.tsx` is the main monolithic UI component; the only extracted pieces are `components/LegalTooltip.tsx` and `lib/parseTooltips.tsx` (the tooltip system)
- **Styling is inline, not Tailwind**: Tailwind utility classes are NOT generated in this setup — use inline `style={{...}}` objects (see `LegalTooltip.tsx`), not className utilities
- Retro pixel-art aesthetic: Press Start 2P font, scanlines, animated video characters (jaguar/tigre per candidate)
- Candidate filter toggles which candidate's documents are included in RAG context
- Streaming responses decoded with `TextDecoder` and rendered incrementally via `useState`
- Sources are embedded in the stream as an HTML comment: `<!--SOURCES:[...]-->` and parsed client-side
