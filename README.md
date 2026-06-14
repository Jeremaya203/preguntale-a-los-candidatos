# ⚡ Pregúntale a los Candidatos — Colombia 2026

Plataforma ciudadana de **transparencia electoral** para la segunda vuelta presidencial
de Colombia 2026. Permite consultar y comparar las propuestas de los dos candidatos
(**Iván Cepeda Castro** y **Abelardo de la Espriella**) contra documentos oficiales,
mediante un chat con IA y una estética retro pixel-art.

> Herramienta **imparcial** por diseño: no le dice a nadie por quién votar. Contrasta
> cada propuesta contra datos institucionales neutrales (CARF, MFMP, DANE, OCDE) y
> muestra siempre las fuentes.

## ✨ Características

- **Chat RAG** con búsqueda híbrida de 4 etapas (BM25 → vectorial → RRF → cross-encoder).
- **Análisis por 12 dimensiones** de política pública, precalculados y anclados en datos oficiales.
- **Fact-checking balanceado**: la desinformación de un candidato nunca se muestra sin la del otro.
- **Tooltips educativos**: 185 términos técnicos/jurídicos explicados en lenguaje ciudadano.
- **Guardrails editoriales** que obligan a la neutralidad (p. ej. la regla de sesgo de formato).

## 🏗️ Stack

- **Frontend:** Next.js 16 + React 19 (TypeScript) → Vercel
- **Backend:** FastAPI + Groq (`llama-4-scout`) + ChromaDB + Sentence Transformers → Railway

## 🚀 Self-hosting

### Backend
```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # edita con tu GROQ_API_KEY
python backend/indexer.py              # construye el índice desde documents/
python backend/main.py                 # http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
echo "BACKEND_URL=http://localhost:8000" > .env.local
npm run dev                            # http://localhost:3000
```

### Variables de entorno
| Variable | Dónde | Descripción |
|---|---|---|
| `GROQ_API_KEY` | backend | **Requerida.** Clave de Groq (gratis en console.groq.com). |
| `BACKEND_SHARED_SECRET` | backend **y** frontend | Recomendada en prod. Si se define, el backend solo acepta peticiones del proxy. Mismo valor en ambos lados. `openssl rand -hex 32`. |
| `ALLOWED_ORIGINS` | backend | Orígenes CORS permitidos (coma-separado). En prod: la URL de tu frontend. |
| `RATE_LIMIT_PER_MIN` | backend | Peticiones por IP por minuto (default 30). |
| `BACKEND_URL` | frontend | URL del backend (default `http://localhost:8000`). |

> ⚠️ El backend es público. **Define `BACKEND_SHARED_SECRET`** (igual en Railway y Vercel)
> para que nadie pueda llamar tu backend directamente y consumir tu cuota de Groq.

## 📚 Fuentes y créditos

El crédito de los documentos oficiales, las verificaciones de fact-checking y el
análisis periodístico pertenece a sus autores y entidades. Ver [`NOTICE`](NOTICE)
para la lista completa de atribuciones.

## 🔐 Seguridad

Ver [`SECURITY.md`](SECURITY.md) para reportar vulnerabilidades.

## 📄 Licencia

[Apache License 2.0](LICENSE) © 2026 Fabián López / Gazzzeta
