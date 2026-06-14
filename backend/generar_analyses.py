#!/usr/bin/env python3
"""
generar_analyses.py
─────────────────────────────────────────────────────────────────────────────
Regenera los análisis precalculados (backend/analyses/<slug>.json) grounded
ESTRICTAMENTE en los fragmentos recuperados del índice (HybridSearch) + Groq.

No usa conocimiento externo: solo lo que devuelve la búsqueda sobre
backend/documents/. La sección 4 (viabilidad) contrasta las propuestas de cada
candidato contra los documentos institucionales neutrales (CARF, MFMP, DANE,
OCDE, PND, Misión de Sabios) que estén entre los fragmentos recuperados.

NO aplica el markup {{término::explicación}} — eso lo hace anotar_analyses.py
después. Tras correr este script, ejecuta:  python backend/anotar_analyses.py

Uso:
    python backend/generar_analyses.py economia          # una dimensión
    python backend/generar_analyses.py economia justicia # varias
    python backend/generar_analyses.py                   # las 12
─────────────────────────────────────────────────────────────────────────────
"""
import os, sys, json, pathlib
from datetime import date

from dotenv import load_dotenv
from groq import Groq
from search import HybridSearch

BASE_DIR = pathlib.Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
VERSION    = "3.0"

# slug → (nombre visible, términos de búsqueda)
DIMS = {
    "economia":        ("Economía", "crecimiento económico política fiscal deuda pública impuestos energía Ecopetrol inversión"),
    "educacion":       ("Educación", "educación colegios universidades cobertura calidad educativa docentes"),
    "salud":           ("Salud", "salud EPS hospitales reforma a la salud aseguramiento atención médica"),
    "paz_y_seguridad": ("Paz y seguridad", "seguridad paz total grupos armados narcotráfico fuerza pública orden público conflicto"),
    "medio_ambiente":  ("Medio ambiente", "medio ambiente cambio climático transición energética petróleo deforestación regalías"),
    "empleo":          ("Empleo", "empleo informalidad laboral desempleo salario mínimo mercado laboral"),
    "vivienda":        ("Vivienda", "vivienda déficit habitacional subsidios vivienda de interés social"),
    "innovacion":      ("Innovación", "ciencia tecnología innovación digitalización investigación desarrollo I+D"),
    "agricultura":     ("Agricultura", "reforma agraria campo campesinos tierras producción agrícola ruralidad"),
    "justicia":        ("Justicia", "justicia corrupción impunidad sistema judicial anticorrupción JEP"),
    "cultura":         ("Cultura", "cultura industrias creativas patrimonio economía naranja arte"),
    "infraestructura": ("Infraestructura", "infraestructura vías carreteras transporte conectividad obras públicas"),
}

# Título crudo del índice → etiqueta legible para que el LLM cite bien la fuente.
SOURCE_LABELS = {
    "Marco Fiscal Mediano Plazo 2025":                  "MFMP 2025 (Min. Hacienda)",
    "Recuadro 1":                                       "MFMP 2025 — Anexo (Recuadro 1)",
    "Recuadro 2":                                       "MFMP 2025 — Anexo (Recuadro 2)",
    "Informe Del Carf Al Congreso De La Republica":     "CARF — Informe al Congreso (sept 2025)",
    "Informe Al Congreso Abril 2026":                   "CARF — Informe al Congreso (abril 2026)",
    "Bol Geih Nov2025":                                 "DANE — GEIH empleo (nov 2025)",
    "Bol Pmultidimensional 2025":                       "DANE — Pobreza multidimensional 2025",
    "2023 02 23 Bases Plan Nacional De Desarrollo Web":  "PND 2022-2026 (referencia de Estado)",
    "A1A22Cd6 En":                                      "OECD Economic Survey Colombia 2024",
    "Libro Mision De Sabios Digital 1 2 0":             "Misión de Sabios 2019",
}

# Reglas institucionales (mismas que SYSTEM_CHAT en main.py).
SYSTEM = """Eres un analista político neutral para "Pregúntale a los Candidatos", plataforma ciudadana de transparencia electoral en Colombia 2026.

CANDIDATOS: Iván Cepeda Castro (Pacto Histórico) y Abelardo de la Espriella "El Tigre" (Colombia Renaciente).

REGLAS OBLIGATORIAS:
1. Usa ÚNICAMENTE la información de los FRAGMENTOS proporcionados. NUNCA uses conocimiento previo. NUNCA inventes cifras, fechas, metas ni compromisos.
2. Si un candidato no tiene propuesta documentada sobre algún aspecto, dilo explícitamente: "No encontré propuesta específica de [candidato] sobre este aspecto en los documentos disponibles."
3. NUNCA uses el PND ni los documentos institucionales como sustituto de las propuestas de un candidato. El PND, CARF, MFMP, DANE, OCDE y Misión de Sabios son CONTEXTO DE REALIDAD, no propuestas de campaña.
4. Tono neutral y objetivo. No favorezcas a ningún candidato.
5. SESGO DE FORMATO: el programa de Iván Cepeda tiene 400+ páginas con narrativa integrada; el de Abelardo de la Espriella ~15 páginas en bullet points. Eso hace que Abelardo PAREZCA "más específico". Cada vez que compares nivel de detalle o especificidad, DEBES aclarar que la diferencia refleja el FORMATO del documento (bullets vs narrativa), no la calidad ni la ambición de la propuesta.
6. DOCUMENTOS INSTITUCIONALES DE VIABILIDAD (CARF, MFMP 2025, DANE, OCDE): son fuentes técnicas neutrales, no del gobierno ni de ningún candidato. Úsalas para evaluar qué tan viable es cada propuesta contra la realidad fiscal y social. Cita la fuente institucional cuando uses un dato (ej. "según el CARF...", "el MFMP 2025 proyecta...", "el DANE registró...").
7. Responde SIEMPRE en español.
8. NO uses el markup {{término::explicación}}: la anotación de tooltips se hace en un paso posterior."""

ESTRUCTURA = """Genera el análisis en Markdown con EXACTAMENTE estas secciones y encabezados:

## 1. ¿Qué necesita Colombia en {tema}? — La realidad según datos oficiales
[Basado en los fragmentos institucionales (CARF, MFMP, DANE, OCDE, PND, Misión de Sabios) que aparezcan abajo. Datos concretos: cifras, déficits, brechas reales. 2-3 párrafos. Cita la fuente de cada dato.]

## 2. ¿Qué propone Iván Cepeda?
[Propuestas concretas SOLO de sus fragmentos. Si no hay info suficiente sobre este tema, dilo explícitamente.]

## 3. ¿Qué propone Abelardo de la Espriella?
[Propuestas concretas SOLO de sus fragmentos. Mismo criterio.]

## 4. ¿Qué tan viable es cada propuesta? — Contraste con datos reales
[La sección MÁS IMPORTANTE. Contrasta cada propuesta contra lo que dicen CARF, MFMP y DANE entre los fragmentos. Cita la fuente institucional en cada juicio de viabilidad. Si falta el dato institucional para juzgar algo, dilo en vez de inventarlo.]

## 5. Contraste objetivo entre candidatos
[Comparación directa y neutral. Aplica la regla de sesgo de formato cuando compares especificidad.]

## 📚 Metodología y fuentes
[Lista los documentos específicos usados en este análisis, incluyendo cuáles documentos institucionales se consultaron.]

No agregues secciones extra ni texto antes de la sección 1."""


def label(title: str) -> str:
    return SOURCE_LABELS.get(title, title)


def fragmentos(results, limite=900) -> str:
    if not results:
        return "[Sin fragmentos]"
    out = []
    for i, r in enumerate(results):
        txt = r["text"].strip().replace("\n", " ")[:limite]
        out.append(f'[{i+1}] Fuente: "{label(r["title"])}"\n{txt}')
    return "\n\n".join(out)


def dedup(results):
    seen, out = set(), []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            out.append(r)
    return out


def generar(slug, engine, client):
    nombre, kw = DIMS[slug]
    query = f"{nombre} {kw}"

    cepeda   = engine.search(query, top_k=7, candidato="ivan-cepeda")
    abelardo = engine.search(query, top_k=7, candidato="abelardo")

    realidad = dedup(
        engine.search(f"{nombre} {kw}", top_k=6, tipo="referencia")
        + engine.search(
            f"sostenibilidad fiscal déficit regla fiscal deuda pobreza informalidad cifras {kw}",
            top_k=6, tipo="referencia",
        )
    )

    user_prompt = f"""DIMENSIÓN: {nombre.upper()}

=== FRAGMENTOS INSTITUCIONALES / DE REFERENCIA (realidad y viabilidad) ===
{fragmentos(realidad)}

=== FRAGMENTOS — PROPUESTAS DE IVÁN CEPEDA ({len(cepeda)} encontrados) ===
{fragmentos(cepeda)}

=== FRAGMENTOS — PROPUESTAS DE ABELARDO DE LA ESPRIELLA ({len(abelardo)} encontrados) ===
{fragmentos(abelardo)}

{ESTRUCTURA.replace("{tema}", nombre.lower())}"""

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": user_prompt}],
        temperature=0.2, max_tokens=4000,
    )
    content = resp.choices[0].message.content.strip()

    # Preservar el valor "dimension" del archivo previo si existe.
    path = BASE_DIR / "analyses" / f"{slug}.json"
    dim_val = nombre
    if path.exists():
        try:
            dim_val = json.loads(path.read_text(encoding="utf-8")).get("dimension", nombre)
        except Exception:
            pass

    path.write_text(json.dumps({
        "dimension":    dim_val,
        "generated_at": date.today().isoformat(),
        "version":      VERSION,
        "content":      content,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return content, len(cepeda), len(abelardo), len(realidad)


def main():
    targets = sys.argv[1:] or list(DIMS)
    bad = [t for t in targets if t not in DIMS]
    if bad:
        print(f"❌ Dimensión(es) desconocida(s): {bad}\n   Válidas: {list(DIMS)}")
        sys.exit(1)

    if not os.getenv("GROQ_API_KEY"):
        print("❌ Falta GROQ_API_KEY en backend/.env")
        sys.exit(1)

    print("🔍 Cargando motor de búsqueda...")
    engine = HybridSearch()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    for slug in targets:
        print(f"\n{'━'*60}\n⚙️  Generando {slug}.json ...")
        content, nc, na, nr = generar(slug, engine, client)
        print(f"   ✅ {len(content)} chars | Cepeda:{nc} Abelardo:{na} institucional:{nr} fragmentos")

    # Anotar tooltips automáticamente: la generación produce texto SIN markup,
    # y dejarlo así rompe los tooltips del frontend. Encadenamos la anotación
    # para que analyses/*.json nunca quede sin anotar. (anotar es idempotente y
    # respalda en analyses_backup/.)
    print(f"\n{'━'*60}\n🏷️  Anotando tooltips ({{término::explicación}})...")
    import subprocess
    subprocess.run([sys.executable, str(BASE_DIR / "anotar_analyses.py")], check=False)
    print(f"\n✅ Listo. Reinicia el backend para servir los análisis nuevos.\n")


if __name__ == "__main__":
    main()
