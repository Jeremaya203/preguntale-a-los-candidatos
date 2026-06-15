"""
main.py — Pregúntale a los Candidatos
Análisis precalculados + RAG híbrido + Groq streaming
"""
import os, re, json, pathlib, time, logging, asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from groq import Groq
from search import HybridSearch
from terminos_juridicos import TERMINOS

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
8. SESGO DE FORMATO — MUY IMPORTANTE: El programa de Iván Cepeda Castro tiene más de 400 páginas con enfoque discursivo e integrador (sus propuestas están entretejidas en una visión más amplia). El de Abelardo de la Espriella tiene ~15 páginas en formato de bullet points por tema. Esta diferencia de extensión y formato hace que Abelardo parezca "más específico" o "más estructurado" en casi todas las dimensiones. Esto NO significa que sus propuestas sean mejores. NUNCA uses "más específico" o "más estructurado" como sinónimo de "mejor propuesta". REGLA OBLIGATORIA: cada vez que compares el nivel de detalle, especificidad o cantidad de propuestas concretas entre los dos candidatos, DEBES incluir una frase explicando que esta diferencia refleja el formato del documento (bullet points vs narrativa integrada), no la calidad ni la ambición de la propuesta.

DOCUMENTOS INSTITUCIONALES DE VIABILIDAD:
Tienes acceso a documentos oficiales completamente neutrales:
- CARF (Comité Autónomo de la Regla Fiscal): evalúa la sostenibilidad fiscal de Colombia de forma independiente al gobierno.
- MFMP 2025 (Marco Fiscal de Mediano Plazo): proyecciones fiscales del Ministerio de Hacienda para 2025-2036.
- DANE (empleo y pobreza 2025): cifras reales del mercado laboral y pobreza multidimensional.

REGLA: Cuando respondas sobre propuestas económicas, fiscales, sociales o de cualquier dimensión, USA estos documentos como contexto de realidad. No evalúes viabilidad basándote solo en lo que dice el candidato — contrástalo siempre con los datos institucionales disponibles. Cita la fuente institucional cuando la uses (CARF, MFMP, DANE).

Estos documentos NO son del gobierno actual ni de ningún candidato. Son fuentes técnicas independientes."""

# ─── Tooltips jurídicos (post-procesado determinístico) ────────────────────
# En vez de pedirle al LLM que marque términos (inconsistente), anotamos toda
# respuesta del LLM en el backend usando el diccionario local. Mismo motor que
# anotar_analyses.py para los precalculados → comportamiento idéntico.
_EXCLUIR_TOOLTIPS = {"paz", "ley", "aval"}  # genéricos: generan ruido visual

def _build_tooltip_pattern() -> re.Pattern:
    # Más largo primero: "acción de tutela" gana sobre "tutela".
    terms = sorted(
        (t for t in TERMINOS if t not in _EXCLUIR_TOOLTIPS),
        key=len, reverse=True,
    )
    alt = "|".join(re.escape(t) for t in terms)
    return re.compile(r"\b(" + alt + r")\b", re.IGNORECASE)

TOOLTIP_PATTERN = _build_tooltip_pattern()

# Caracteres de corte seguro para el streaming: un término jurídico es una
# secuencia de palabras (letras + espacios), nunca contiene puntuación ni
# saltos de línea. Cortar el buffer en uno de estos caracteres garantiza que
# jamás partimos un término (ni siquiera uno multi-palabra) entre dos chunks.
_FLUSH_CHARS = ".,;:!?…\n)"

def aplicar_tooltips(texto: str, ya_anotados: Optional[set] = None) -> str:
    """
    Anota términos técnico-jurídicos con {{término::explicación}}.
    Cada término se anota máximo UNA vez (usa `ya_anotados`, que puede
    compartirse entre los chunks de un mismo stream). Ignora ocurrencias
    que ya estén dentro de un {{...}}.
    """
    if ya_anotados is None:
        ya_anotados = set()

    def _reemplazar(match):
        original = match.group(0)
        clave    = original.lower()
        if clave in ya_anotados:
            return original
        inicio = match.start()
        prev   = texto[max(0, inicio - 2):inicio]
        if prev.endswith("{{") or prev.endswith("::"):
            return original
        ya_anotados.add(clave)
        return f"{{{{{original}::{TERMINOS[clave]}}}}}"

    return TOOLTIP_PATTERN.sub(_reemplazar, texto)

def annotate_token_stream(token_iter):
    """
    Envuelve un iterable de tokens del LLM y va emitiendo el texto anotado a
    nivel de cláusula: cada vez que el buffer contiene un carácter de corte
    seguro (`_FLUSH_CHARS`), emite hasta ahí ya anotado. Como esos caracteres
    nunca aparecen dentro de un término, ningún término se parte entre chunks,
    y el resultado es idéntico a anotar la respuesta completa de una vez.
    El conjunto `ya` se comparte entre chunks → cada término se anota 1 sola vez.
    """
    buffer = ""
    ya: set = set()
    for c in token_iter:
        if not c:
            continue
        buffer += c
        cut = max(buffer.rfind(ch) for ch in _FLUSH_CHARS)
        if cut >= 0:
            yield aplicar_tooltips(buffer[:cut + 1], ya)
            buffer = buffer[cut + 1:]
    if buffer:
        yield aplicar_tooltips(buffer, ya)

# Reglas de fact-checking — solo se añaden cuando la pregunta es sobre desinformación.
FC_RULES = """

REGLAS PARA FACT-CHECKING:
- Los fragmentos con CATEGORIA "fact-checking" son verificaciones de desinformación. Son evidencia de que algo fue DESMENTIDO, no de que un candidato lo hizo.
- Nunca uses un artículo de fact-checking como evidencia de una acción real del candidato. Solo úsalos para responder preguntas sobre desinformación.
- Si presentas fake news de un candidato, SIEMPRE presenta también el equivalente del otro candidato. Nunca de un solo lado.
- Si no hay verificaciones de un candidato sobre ese tema específico, dilo explícitamente: "No encontré verificaciones equivalentes para [candidato] sobre este tema."""

# Los tooltips ya no se piden al LLM: se aplican en el backend con
# aplicar_tooltips(). SYSTEM_CHAT_FULL se mantiene como punto único de prompt.
SYSTEM_CHAT_FULL = SYSTEM_CHAT

# Palabras que indican que la pregunta es sobre desinformación / fake news.
FC_KEYWORDS = [
    "fake news", "mentira", "falso", "falsa", "inventaron", "inventó", "invento",
    "acusación", "acusacion", "dijeron que", "es verdad que", "desmentir",
    "verificar", "cierto que", "bulo", "montaje", "desinformación", "desinformacion",
    "rumor", "circula", "viral",
]

def is_disinfo_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in FC_KEYWORDS)

MAX_MSG_LEN  = 4000   # caracteres por mensaje
MAX_MESSAGES = 40     # mensajes por petición

class Message(BaseModel):
    role: str
    content: str = Field(max_length=MAX_MSG_LEN)

class ChatRequest(BaseModel):
    messages: List[Message] = Field(min_length=1, max_length=MAX_MESSAGES)
    candidato: Optional[str] = None

class AnalyzeRequest(BaseModel):
    dimension: str = Field(max_length=80)
    candidatos: List[str] = Field(default=["ivan-cepeda", "abelardo"], max_length=5)

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

# Orígenes permitidos por CORS. Por defecto "*" para facilitar el self-hosting;
# en producción define ALLOWED_ORIGINS=https://tu-frontend.vercel.app (coma-separado).
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])

# ─── Protección del backend público (secreto compartido + rate-limiting) ───
# El código es open source, así que la seguridad NO puede depender de la oscuridad.
# Para que nadie pueda agotar la GROQ_API_KEY llamando directamente al backend:
#  - BACKEND_SHARED_SECRET: si está definido, exige el header X-Internal-Secret
#    (lo envía el proxy de Vercel). El valor vive SOLO en env vars, nunca en el repo.
#    Si NO está definido, no se exige (permite self-hosting y no rompe el deploy actual).
#  - Rate-limit por IP en memoria (respeta X-Forwarded-For tras el proxy de Railway).
BACKEND_SHARED_SECRET = os.getenv("BACKEND_SHARED_SECRET", "")
RATE_LIMIT_PER_MIN    = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
_RATE_WINDOW          = 60.0
_rate_hits: dict      = defaultdict(deque)
logger = logging.getLogger("uvicorn.error")

def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def guard(request: Request):
    """Dependencia compartida por /chat y /analyze: secreto + rate-limit."""
    if BACKEND_SHARED_SECRET and request.headers.get("x-internal-secret") != BACKEND_SHARED_SECRET:
        raise HTTPException(401, "No autorizado.")
    ip  = _client_ip(request)
    now = time.time()
    dq  = _rate_hits[ip]
    while dq and dq[0] < now - _RATE_WINDOW:
        dq.popleft()
    if len(dq) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Demasiadas solicitudes. Espera un minuto e intenta de nuevo.")
    dq.append(now)
    if len(_rate_hits) > 10000:   # limpieza ocasional de IPs inactivas
        for k in [k for k, v in _rate_hits.items() if not v]:
            _rate_hits.pop(k, None)

async def _aiter_blocking(sync_gen_factory):
    """
    Ejecuta un generador SÍNCRONO (la iteración del stream de Groq, que es
    bloqueante) en un hilo aparte y entrega sus piezas SIN bloquear el event
    loop, vía una cola. Así varias peticiones /chat concurrentes no se
    serializan esperando los tokens de Groq.

    NO cambia la llamada a Groq, ni el nº de tokens, ni el prompt: solo cómo se
    bombean los tokens ya generados hacia el cliente.
    """
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    _DONE = object()

    def _producer():
        try:
            for item in sync_gen_factory():
                loop.call_soon_threadsafe(queue.put_nowait, item)
        except Exception:
            logger.exception("Error generando respuesta del LLM")
            loop.call_soon_threadsafe(
                queue.put_nowait,
                "\n\n[Error interno del servidor. Intenta de nuevo en un momento.]")
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _DONE)

    loop.run_in_executor(None, _producer)
    while True:
        item = await queue.get()
        if item is _DONE:
            break
        yield item

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
    fc    = sum(1 for m in search_engine.metadata if m["tipo"] == "fact-checking")
    return {"status": "ok", "total": total, "candidatos": cands,
            "referencia": refs, "fact_checking": fc}

@app.post("/chat", dependencies=[Depends(guard)])
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
    # La búsqueda (BM25 + vectorial + cross-encoder) es CPU-bound y bloqueante;
    # la corremos en un threadpool para no bloquear el event loop (varios usuarios
    # en paralelo aprovechan los vCPU; PyTorch libera el GIL en la inferencia).
    results = await run_in_threadpool(
        search_engine.search, query, top_k=6, candidato=req.candidato)
    context, n = build_context(results, req.candidato or "todos")
    sources = [{"title":r["title"],"tipo":r["tipo"],"candidato":r["candidato"],"lang":r["lang"]} for r in results]

    # ── Fact-checking (si la pregunta es sobre desinformación) ────────────
    # Buscamos de forma BALANCEADA: ambos candidatos + general, sin importar
    # el filtro de candidato, para cumplir la regla de no presentar un solo lado.
    disinfo  = is_disinfo_query(query)
    fc_block = ""
    if disinfo:
        fc_results = []
        for cat in ("contra_cepeda", "contra_espriella", "general"):
            fc_results.extend(
                await run_in_threadpool(
                    search_engine.search, query, top_k=2,
                    tipo="fact-checking", categoria=cat)
            )
        if fc_results:
            fc_ctx, _ = build_context(fc_results, "fact-checking")
            fc_block = (
                "\n\nVERIFICACIONES DE DESINFORMACIÓN (fact-checking — son DESMENTIDOS "
                "de afirmaciones falsas, NO pruebas de que el candidato lo hizo):\n"
                f"{fc_ctx[:4000]}"
            )
            sources += [
                {"title": r["title"], "tipo": "fact-checking",
                 "candidato": r.get("candidato", ""), "lang": r["lang"]}
                for r in fc_results
            ]

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

    # Añadir verificaciones de fact-checking al prompt si las hay
    if fc_block:
        user_prompt += fc_block + ("\n\nResponde la PREGUNTA aplicando las REGLAS PARA "
                                   "FACT-CHECKING de forma balanceada para ambos candidatos.")

    if n == 0 and not base_analysis and not fc_block:
        async def no_results():
            yield "No encontré documentos relevantes para tu pregunta en los documentos disponibles."
        return StreamingResponse(no_results(), media_type="text/plain; charset=utf-8")

    system_content = SYSTEM_CHAT_FULL + (FC_RULES if disinfo else "")

    def _groq_tokens():
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role":"system","content":system_content},
                      {"role":"user","content":user_prompt}],
            stream=True, max_tokens=1200, temperature=0.2)
        for chunk in response:
            c = chunk.choices[0].delta.content
            if c:
                yield c

    async def stream():
        # La iteración del stream de Groq es bloqueante; la corremos en un hilo
        # (vía _aiter_blocking) para no congelar el event loop con cada usuario.
        # La anotación de tooltips (determinística) se mantiene igual.
        async for piece in _aiter_blocking(lambda: annotate_token_stream(_groq_tokens())):
            yield piece
        yield f"\n\n<!--SOURCES:{json.dumps(sources, ensure_ascii=False)}-->"

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")

@app.post("/analyze", dependencies=[Depends(guard)])
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
    ref_results        = await run_in_threadpool(
        search_engine.search, dim, top_k=6, tipo="referencia")
    ref_context, ref_n = build_context(ref_results, f"referencia sobre {dim}")
    CANDS = {"ivan-cepeda":"Iván Cepeda Castro (Pacto Histórico)",
             "abelardo":"Abelardo de la Espriella 'El Tigre'"}
    secciones = []
    for cand in req.candidatos:
        nombre  = CANDS.get(cand, cand)
        results = await run_in_threadpool(
            search_engine.search, dim, top_k=4, candidato=cand)
        ctx, n  = build_context(results, nombre)
        aviso   = f"⛔ SIN fragmentos de {nombre}." if n == 0 else f"✅ {n} fragmentos."
        secciones.append(f"PROPUESTAS DE {nombre.upper()} ({aviso})\n{ctx}")
    user_prompt = f"DIMENSIÓN: {dim.upper()}\nREFERENCIA:\n{ref_context}\n{'='*40}\n{''.join(secciones)}\nGenera análisis con secciones: 1.Contexto 2.Propuesta Iván 3.Propuesta Abelardo 4.Contraste 5.Fuentes"
    def _groq_tokens():
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role":"system","content":SYSTEM_CHAT_FULL},{"role":"user","content":user_prompt}],
            stream=True, max_tokens=3000, temperature=0.2)
        for chunk in r:
            c = chunk.choices[0].delta.content
            if c: yield c
    async def stream_groq():
        # El precalculado ya viene anotado por anotar_analyses.py; este fallback
        # genera texto nuevo, anotado en vivo. Iteración bloqueante en hilo aparte.
        async for piece in _aiter_blocking(lambda: annotate_token_stream(_groq_tokens())):
            yield piece
    return StreamingResponse(stream_groq(), media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
