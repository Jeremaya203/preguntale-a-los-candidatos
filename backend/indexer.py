#!/usr/bin/env python3
"""
indexer.py — Indexación AGRESIVA para RAG de alta calidad
Chunks de 200 palabras con 50% de overlap + batch optimizado para CPU multi-núcleo

Uso:
  cd ~/preguntale-a-los-candidatos
  source venv/bin/activate
  python backend/indexer.py
"""

import re
import pickle
import pathlib
from typing import List, Dict

import fitz  # PyMuPDF
from docx import Document as DocxDocument
import chromadb
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from utils import tokenize

# ─── Configuración agresiva ─────────────────────────────────────────────────
BASE_DIR    = pathlib.Path(__file__).parent
DOCS_DIR    = BASE_DIR / "documents"
CHROMA_DIR  = str(BASE_DIR / "chroma_db")
BM25_PATH   = str(BASE_DIR / "bm25_index.pkl")
COLLECTION  = "candidatos_docs"
MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"

CHUNK_WORDS = 200   # Chunks pequeños = búsqueda precisa
OVERLAP     = 100   # 50% overlap = nada se pierde entre chunks
BATCH_SIZE  = 64    # Aprovecha los 6 núcleos del Ryzen 5 5600G
MIN_WORDS   = 40    # Descarta chunks demasiado cortos

CANDIDATOS = {
    "ivan-cepeda": "Iván Cepeda Castro",
    "abelardo":    "Abelardo de la Espriella",
}

# ─── Extracción de texto mejorada ───────────────────────────────────────────

def clean_text(text: str) -> str:
    """Limpieza agresiva de artefactos de PDF"""
    # Eliminar números de página solos (ej: "| 42 |", "42\n", "- 42 -")
    text = re.sub(r'\|\s*\d+\s*\|', ' ', text)
    text = re.sub(r'^\s*[-–]\s*\d+\s*[-–]\s*$', ' ', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\s*$', ' ', text, flags=re.MULTILINE)
    # Eliminar guiones de corte de palabra (hyphenation)
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    # Normalizar espacios y saltos de línea
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Eliminar caracteres no imprimibles
    text = re.sub(r'[^\x20-\x7E\xA0-\xFF\n]', ' ', text)
    return text.strip()

def extract_pdf(path: pathlib.Path) -> str:
    doc = fitz.open(str(path))
    pages = []
    for page in doc:
        # Extraer texto con mejor manejo de columnas
        txt = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        pages.append(txt)
    doc.close()
    return clean_text("\n".join(pages))

def extract_docx(path: pathlib.Path) -> str:
    doc = DocxDocument(str(path))
    return clean_text("\n".join(p.text for p in doc.paragraphs))

def extract_txt(path: pathlib.Path) -> str:
    return clean_text(path.read_text(encoding="utf-8", errors="ignore"))

def extract_text(path: pathlib.Path) -> str | None:
    ext = path.suffix.lower()
    if ext == ".pdf":           return extract_pdf(path)
    if ext == ".docx":          return extract_docx(path)
    if ext in (".txt", ".md"):  return extract_txt(path)
    return None

# ─── Chunking agresivo con 50% overlap ─────────────────────────────────────

def chunk_text(text: str) -> List[str]:
    """
    Divide el texto en chunks de CHUNK_WORDS palabras
    con OVERLAP palabras de solapamiento (50%).
    
    Con 200 palabras y 100 de overlap:
    - Chunk 1: palabras 0-199
    - Chunk 2: palabras 100-299
    - Chunk 3: palabras 200-399
    → Cada palabra aparece en ~2 chunks = cobertura total garantizada
    """
    words = text.split()
    chunks = []
    step   = CHUNK_WORDS - OVERLAP  # = 100 palabras por paso

    start = 0
    while start < len(words):
        end   = min(start + CHUNK_WORDS, len(words))
        chunk = " ".join(words[start:end]).strip()

        # Solo incluir chunks con contenido suficiente
        if len(chunk.split()) >= MIN_WORDS:
            chunks.append(chunk)

        if end == len(words):
            break
        start += step

    return chunks

# ─── Detección de metadatos ─────────────────────────────────────────────────

def detect_metadata(path: pathlib.Path) -> Dict[str, str]:
    try:
        relative = path.relative_to(DOCS_DIR)
    except ValueError:
        relative = path

    parts        = relative.parts
    tipo         = "referencia"
    candidato    = ""
    lang         = "es"
    categoria_fc = ""

    if parts and parts[0] == "candidatos":
        tipo = "candidato"
        if len(parts) > 1 and parts[1] in CANDIDATOS:
            candidato = parts[1]
    elif parts and parts[0] == "fact-checking":
        tipo = "fact-checking"
        # parts[1] = contra_cepeda | contra_espriella | general
        if len(parts) > 1:
            categoria_fc = parts[1]
    elif parts and parts[0] == "referencia":
        tipo = "referencia"
        if len(parts) > 1 and parts[1] == "en":
            lang = "en"

    return {"tipo": tipo, "candidato": candidato, "lang": lang,
            "categoria_fc": categoria_fc}


# Campos del header que extraemos de los .txt de fact-checking
FC_HEADER_KEYS = ("FUENTE", "CANDIDATO_AFECTADO", "TITULAR",
                  "ACUSACION_FALSA", "VEREDICTO")

def parse_fc_header(text: str) -> Dict[str, str]:
    """
    Extrae los campos del header de un artículo de fact-checking.
    El header termina en la línea de separación (━━━).
    """
    fields: Dict[str, str] = {}
    for line in text.splitlines():
        if line.strip().startswith("━"):
            break  # fin del header
        for key in FC_HEADER_KEYS:
            if line.startswith(key + ":"):
                fields[key] = line.split(":", 1)[1].strip()
    return fields

# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("🚀 Indexación AGRESIVA — Pregúntale a los Candidatos")
    print(f"   Chunk: {CHUNK_WORDS} palabras | Overlap: {OVERLAP} (50%) | Batch: {BATCH_SIZE}\n")

    if not DOCS_DIR.exists():
        print(f"❌ No existe {DOCS_DIR}"); return

    docs = [p for p in DOCS_DIR.rglob("*")
            if p.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}]

    if not docs:
        print("❌ No hay documentos en backend/documents/"); return

    print(f"📄 {len(docs)} documentos encontrados\n")

    # Cargar modelo embeddings
    print(f"🤖 Cargando modelo: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("   ✅ Modelo listo\n")

    # Inicializar ChromaDB
    print("📦 Preparando ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION)
        print("   ↺  Colección anterior eliminada")
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )
    print("   ✅ Colección lista\n")

    # Procesar documentos
    all_texts     = []   # textos para embeddings (todos juntos → 1 encode call)
    all_tokenized = []   # para BM25
    all_metadata  = []   # para reconstruir resultados
    chroma_ids, chroma_metas = [], []

    for doc_path in sorted(docs):
        meta      = detect_metadata(doc_path)
        title     = doc_path.stem.replace("-"," ").replace("_"," ").title()

        raw = extract_text(doc_path)
        if not raw or len(raw.strip()) < 100:
            print(f"📖  {doc_path.name}")
            print("     ⚠️  vacío, omitido\n"); continue

        # ── Metadatos extra para fact-checking ─────────────────────────────
        fc_extra: Dict[str, str] = {}
        if meta["tipo"] == "fact-checking":
            header = parse_fc_header(raw)
            # El TITULAR del header es más legible que el nombre de archivo
            if header.get("TITULAR"):
                title = header["TITULAR"]
            fc_extra = {
                "categoria_fc":       meta["categoria_fc"],
                "candidato_afectado": header.get("CANDIDATO_AFECTADO", ""),
                "fuente":             header.get("FUENTE", ""),
                "acusacion_falsa":    header.get("ACUSACION_FALSA", ""),
                "veredicto":          header.get("VEREDICTO", ""),
            }
            label = f"fact-checking:{meta['categoria_fc']} ← {fc_extra['fuente'] or '?'}"
        elif meta["tipo"] == "candidato":
            label = f"candidato:{CANDIDATOS.get(meta['candidato'], '?')}"
        else:
            label = f"referencia ({'EN' if meta['lang']=='en' else 'ES'})"

        print(f"📖  {doc_path.name}")
        print(f"     └─ {label}")

        # Normalizar espacios
        clean = " ".join(raw.split())
        chunks = chunk_text(clean)

        if not chunks:
            print("     ⚠️  sin fragmentos\n"); continue

        for i, chunk in enumerate(chunks):
            cid   = f"{doc_path.stem}_{i}"
            cmeta = {
                "title":     title,
                "source":    str(doc_path.relative_to(DOCS_DIR)),
                "tipo":      meta["tipo"],
                "candidato": meta["candidato"],
                "lang":      meta["lang"],
                **fc_extra,
            }
            all_texts.append(chunk)
            all_tokenized.append(tokenize(chunk))
            all_metadata.append({**cmeta, "id": cid, "text": chunk})
            chroma_ids.append(cid)
            chroma_metas.append(cmeta)

        print(f"     ✅ {len(chunks)} fragmentos\n")

    if not all_texts:
        print("❌ No se procesó ningún documento."); return

    print(f"📊 Total fragmentos a indexar: {len(all_texts)}")
    print(f"   (Iván: {sum(1 for m in all_metadata if m.get('candidato')=='ivan-cepeda')} | "
          f"Abelardo: {sum(1 for m in all_metadata if m.get('candidato')=='abelardo')} | "
          f"Referencia: {sum(1 for m in all_metadata if m.get('tipo')=='referencia')} | "
          f"Fact-checking: {sum(1 for m in all_metadata if m.get('tipo')=='fact-checking')})\n")

    # Generar embeddings en UN SOLO BATCH grande (más eficiente en CPU)
    print(f"🔢 Generando embeddings (batch={BATCH_SIZE}, CPU multi-núcleo)...")
    print("   Esto puede tardar 3-8 minutos en tu Ryzen 5 5600G...")

    embeddings = model.encode(
        all_texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # Cosine similarity optimizado
        convert_to_numpy=True,
    )
    print("   ✅ Embeddings generados\n")

    # Subir a ChromaDB en lotes
    print("☁️  Guardando en ChromaDB...")
    BATCH = 500
    for i in range(0, len(chroma_ids), BATCH):
        collection.add(
            ids        = chroma_ids[i:i+BATCH],
            documents  = all_texts[i:i+BATCH],
            embeddings = embeddings[i:i+BATCH].tolist(),
            metadatas  = chroma_metas[i:i+BATCH],
        )
        print(f"   Subidos: {min(i+BATCH, len(chroma_ids))}/{len(chroma_ids)}")
    print("   ✅ ChromaDB guardado\n")

    # Construir índice BM25
    print("📊 Construyendo índice BM25...")
    bm25 = BM25Okapi(all_tokenized)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "metadata": all_metadata}, f)
    print(f"   ✅ BM25 guardado\n")

    # Resumen
    cands = sum(1 for m in all_metadata if m["tipo"] == "candidato")
    refs  = sum(1 for m in all_metadata if m["tipo"] == "referencia")
    fc    = sum(1 for m in all_metadata if m["tipo"] == "fact-checking")
    print("=" * 55)
    print("🎉 ¡Indexación agresiva completada!")
    print(f"   Total fragmentos : {len(all_metadata)}")
    print(f"   De candidatos    : {cands}")
    print(f"   De referencia    : {refs}")
    print(f"   De fact-checking : {fc}")
    print(f"\n▶  Siguiente paso: cd backend && uvicorn main:app --reload")

if __name__ == "__main__":
    main()
