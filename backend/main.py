"""
main.py — Pregúntale a los Candidatos
Análisis precalculados + RAG híbrido + Groq streaming
"""
import os, json, pathlib
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
from search import HybridSearch

load_dotenv(pathlib.Path(__file__).parent / ".env")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "meta-llama/llama-4-scout-17b-16e-instruct"
BASE_DIR     = pathlib.Path(__file__).parent

# ─── Mapa dimensión → archivo ─────────────────────────────────────────────
DIM_MAP = {
    "educación":"educacion","salud":"salud","economía":"economia",
    "paz y seguridad":"paz_y_seguridad","medio ambiente":"medio_ambiente",
    "empleo":"empleo","vivienda":"vivienda","innovación":"innovacion",
    "agricultura":"agricultura","justicia":"justicia",
    "cultura":"cultura","infraestructura":"infraestructura",
}

# Keywords para detectar dimensión en preguntas de chat
DIM_KEYWORDS = {
    "salud":           ["salud","hospital","eps","médic","enfermedad","atención médica","upa","upc","adres"],
    "educacion":       ["educaci","escuela","colegio","universidad","docente","maestro","estudiante","bachillerato"],
    "economia":        ["econom","pib","impuesto","fiscal","crecimiento","tributar","deuda","inflaci","inversión","empresa"],
    "paz_y_seguridad": ["paz","seguridad","violencia","conflicto","narcotr","grupos armados","coca","guerrill","acuerdo de paz"],
    "medio_ambiente":  ["ambiente","clima","biodiversidad","deforest","carbono","renovable","páramo","escazú"],
    "empleo":          ["empleo","trabajo","desempleo","informal","laboral","salario","contrat"],
    "vivienda":        ["vivienda","hogar","habitacional","propiedad","arrend","casa propia"],
    "innovacion":      ["tecnolog","innovaci","digital","inteligencia artificial"," ia ","ciencia","i+d","startup"],
    "agricultura":     ["campo","rural","agro","campesino","tierra","alimentar","cosecha","hectárea"],
    "justicia":        ["justicia","judicial","corrupci","impunidad","jep","carcel","delito"],
    "cultura":         ["cultura","arte","música","patrimonio","audiovisual","cine","turismo"],
    "infraestructura": ["infraestructura","vía","carretera","transporte","conectividad","energía eléctrica"],
}

SYSTEM_CHAT = """Eres un asistente de análisis político para "Pregúntale a los Candidatos", plataforma ciudadana de transparencia electoral en Colombia 2026.

CANDIDATOS: Iván Cepeda Castro (Pacto Histórico) y Abelardo de la Espriella "El Tigre" (Colombia Renaciente).

REGLAS OBLIGATORIAS:
1. Usa ÚNICAMENTE la información del CONTEXTO proporcionado. NUNCA uses conocimiento previo.
2. Si hay un ANÁLISIS PRECALCULADO, úsalo como base principal de tu respuesta.
3. Complementa con los FRAGMENTOS DEL RAG cuando añadan información específica nueva.
4. Si un candidato no tiene propuesta sobre el tema en el contexto: escribe exactamente "Hasta la fecha, [candidato] no ha pronunciado una propuesta específica sobre este tema en sus documentos oficiales disponibles."
5. NUNCA inventes cifras, fechas ni compromisos.
6. NUNCA uses el PND como sustituto de las propuestas de ningún candidato.
7. Responde SIEMPRE en español con tono neutral y objetivo.
8. SESGO DE FORMATO — MUY IMPORTANTE: El programa de Iván Cepeda Castro tiene más de 400 páginas con enfoque discursivo e integrador (sus propuestas están entretejidas en una visión más amplia). El de Abelardo de la Espriella tiene ~15 páginas en formato de bullet points por tema. Esta diferencia de extensión y formato hace que Abelardo parezca "más específico" o "más estructurado" en casi todas las dimensiones. Esto NO significa que sus propuestas sean mejores. NUNCA uses "más específico" o "más estructurado" como sinónimo de "mejor propuesta". REGLA OBLIGATORIA: cada vez que compares el nivel de detalle, especificidad o cantidad de propuestas concretas entre los dos candidatos, DEBES incluir una frase explicando que esta diferencia refleja el formato del documento (bullet points vs narrativa integrada), no la calidad ni la ambición de la propuesta."""

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    candidato: Optional[str] = None

class AnalyzeRequest(BaseModel):
    dimension: str
    candidatos: List[str] = ["ivan-cepeda", "abelardo"]

search_engine: Optional[HybridSearch] = None
groq_client:   Optional[Groq]         = None

def _load_search_engine():
    global search_engine
    try:
        search_engine = HybridSearch()
    except Exception as e:
        print(f"⚠️  Motor de búsqueda no disponible: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global groq_client
    import threading
    threading.Thread(target=_load_search_engine, daemon=True).start()
    if GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
    yield

app = FastAPI(title="Pregúntale a los Candidatos", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def detect_dimension(query: str) -> Optional[str]:
    """Detecta si la pregunta toca alguna de las 12 dimensiones."""
    q = query.lower()
    best, best_score = None, 0
    for dim, keywords in DIM_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > best_score:
            best, best_score = dim, score
    return best if best_score >= 1 else None

def load_analysis(slug: str) -> Optional[str]:
    """Carga el análisis precalculado si existe."""
    f = BASE_DIR / "analyses" / f"{slug}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))["content"]
    return None

def build_context(results, label=""):
    if not results:
        return f"[Sin fragmentos para: {label}]", 0
    blocks = [f"[{i+1}] \"{r['title']}\"\n{r['text']}" for i, r in enumerate(results)]
    return "\n\n---\n\n".join(blocks), len(results)

@app.get("/health")
def health():
    if not search_engine:
        return {"status": "no_index"}
    total = search_engine.collection.count()
    cands = sum(1 for m in search_engine.metadata if m["tipo"] == "candidato")
    refs  = sum(1 for m in search_engine.metadata if m["tipo"] == "referencia")
    return {"status": "ok", "total": total, "candidatos": cands, "referencia": refs}

@app.post("/chat")
async def chat(req: ChatRequest):
    if not groq_client:
        raise HTTPException(500, "GROQ_API_KEY no configurada")
    if not search_engine:
        raise HTTPException(503, "Ejecuta indexer.py primero.")
    if not req.messages:
        raise HTTPException(400, "Sin mensajes")

    query = req.messages[-1].content.strip()

    # ── Detectar dimensión y cargar análisis precalculado ─────────────────
    detected_dim   = detect_dimension(query)
    base_analysis  = load_analysis(detected_dim) if detected_dim else None

    # ── Búsqueda RAG ──────────────────────────────────────────────────────
    results = search_engine.search(query, top_k=6, candidato=req.candidato)
    context, n = build_context(results, req.candidato or "todos")
    sources = [{"title":r["title"],"tipo":r["tipo"],"candidato":r["candidato"],"lang":r["lang"]} for r in results]

    # ── Construir prompt híbrido ───────────────────────────────────────────
    if base_analysis:
        # Pregunta temática: análisis precalculado + fragmentos RAG
        user_prompt = f"""ANÁLISIS COMPLETO SOBRE {detected_dim.upper().replace("_"," ")} (ÚSALO COMO BASE PRINCIPAL):
{base_analysis[:6000]}

---
FRAGMENTOS ADICIONALES DEL RAG ({n} encontrados — usa solo si añaden información nueva no cubierta arriba):
{context[:4000]}

---
PREGUNTA DEL USUARIO: {query}

Responde de forma completa basándote principalmente en el ANÁLISIS COMPLETO. Complementa con los fragmentos RAG solo cuando aporten detalles específicos adicionales."""
    else:
        # Pregunta específica: solo RAG
        aviso = f"\n⚠️ Solo {n} fragmento(s) encontrado(s)." if n < 2 else ""
        user_prompt = f"CONTEXTO ({n} fragmentos):{aviso}\n{context}\n\nPREGUNTA: {query}"

    if n == 0 and not base_analysis:
        async def no_results():
            yield "No encontré documentos relevantes para tu pregunta en los documentos disponibles."
        return StreamingResponse(no_results(), media_type="text/plain; charset=utf-8")

    async def stream():
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role":"system","content":SYSTEM_CHAT},
                          {"role":"user","content":user_prompt}],
                stream=True, max_tokens=1200, temperature=0.2)
            for chunk in response:
                c = chunk.choices[0].delta.content
                if c:
                    yield c
            yield f"\n\n<!--SOURCES:{json.dumps(sources, ensure_ascii=False)}-->"
        except Exception as e:
            yield f"\n\nError: {str(e)}"

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    dim  = req.dimension.strip()
    slug = DIM_MAP.get(dim.lower(), dim.lower().replace(" ","_"))
    analysis_file = BASE_DIR / "analyses" / f"{slug}.json"

    if analysis_file.exists():
        content = json.loads(analysis_file.read_text(encoding="utf-8"))["content"]
        return StreamingResponse(iter([content]), media_type="text/plain; charset=utf-8")

    # Fallback Groq si no hay precalculado
    if not groq_client:
        raise HTTPException(500, "GROQ_API_KEY no configurada")
    if not search_engine:
        raise HTTPException(503, "Base de documentos no indexada.")
    ref_results        = search_engine.search(dim, top_k=6, tipo="referencia")
    ref_context, ref_n = build_context(ref_results, f"referencia sobre {dim}")
    CANDS = {"ivan-cepeda":"Iván Cepeda Castro (Pacto Histórico)",
             "abelardo":"Abelardo de la Espriella 'El Tigre'"}
    secciones = []
    for cand in req.candidatos:
        nombre  = CANDS.get(cand, cand)
        results = search_engine.search(dim, top_k=4, candidato=cand)
        ctx, n  = build_context(results, nombre)
        aviso   = f"⛔ SIN fragmentos de {nombre}." if n == 0 else f"✅ {n} fragmentos."
        secciones.append(f"PROPUESTAS DE {nombre.upper()} ({aviso})\n{ctx}")
    user_prompt = f"DIMENSIÓN: {dim.upper()}\nREFERENCIA:\n{ref_context}\n{'='*40}\n{''.join(secciones)}\nGenera análisis con secciones: 1.Contexto 2.Propuesta Iván 3.Propuesta Abelardo 4.Contraste 5.Fuentes"
    async def stream_groq():
        try:
            r = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role":"system","content":SYSTEM_CHAT},{"role":"user","content":user_prompt}],
                stream=True, max_tokens=3000, temperature=0.2)
            for chunk in r:
                c = chunk.choices[0].delta.content
                if c: yield c
        except Exception as e:
            yield f"\n\nError: {str(e)}"
    return StreamingResponse(stream_groq(), media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
