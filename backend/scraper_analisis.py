#!/usr/bin/env python3
"""
scraper_analisis.py
─────────────────────────────────────────────────────────────────────────────
Descarga artículos de análisis independiente de las propuestas de ambos
candidatos para enriquecer el RAG con cobertura equilibrada.

Uso:
    python backend/scraper_analisis.py              # descarga todo
    python backend/scraper_analisis.py --dry-run    # solo muestra el plan
─────────────────────────────────────────────────────────────────────────────
"""

import re
import sys
import time
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).parent / "documents" / "analisis-independientes"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}
DELAY   = 2.0
TIMEOUT = 20

# ─── Artículos a descargar ───────────────────────────────────────────────────
#
# Organizados en carpetas por fuente. Incluye análisis de propuestas
# de AMBOS candidatos en proporciones iguales por fuente.
#
ARTICULOS = {

    # ── La Silla Vacía — análisis de propuestas ──────────────────────────────
    "la_silla_vacia": [
        {
            "candidato": "Ivan Cepeda",
            "titulo": "Las propuestas bomba del programa de Iván Cepeda",
            "url": "https://www.lasillavacia.com/silla-nacional/las-propuestas-bomba-del-programa-de-ivan-cepeda/",
        },
        {
            "candidato": "Abelardo Espriella",
            "titulo": "Las propuestas bomba del programa de Abelardo de la Espriella",
            "url": "https://www.lasillavacia.com/silla-nacional/las-propuestas-bomba-de-abelardo-de-la-espriella/",
        },
        {
            "candidato": "Ambos",
            "titulo": "1.384 propuestas de candidatos evaluadas por expertos independientes",
            "url": "https://www.lasillavacia.com/silla-nacional/evaluacion-de-expertos-a-las-propuestas-de-los-candidatos-presidenciales/",
        },
        {
            "candidato": "Ambos",
            "titulo": "Colombia va a segunda vuelta entre dos proyectos excluyentes",
            "url": "https://www.lasillavacia.com/silla-nacional/colombia-va-a-una-segunda-vuelta-entre-dos-proyectos-excluyentes/",
        },
        {
            "candidato": "Abelardo Espriella",
            "titulo": "La estrategia judicial de Espriella contra periodistas",
            "url": "https://www.lasillavacia.com/silla-nacional/asi-funciona-la-estrategia-judicial-de-de-la-espriella-contra-periodistas/",
        },
        {
            "candidato": "Ivan Cepeda",
            "titulo": "Cepeda en Caracol: Ecopetrol, fracking y el espejo del gobierno Petro",
            "url": "https://www.lasillavacia.com/en-vivo/cepeda-en-caracol-ecopetrol-corrupcion-y-el-gobierno-petro/",
        },
    ],

    # ── Cambio Colombia — viabilidad de programas ────────────────────────────
    "cambio_colombia": [
        {
            "candidato": "Ivan Cepeda",
            "titulo": "El programa de Iván Cepeda en 2026: qué propone y qué tan viable es",
            "url": "https://cambiocolombia.com/elecciones-2026-programa-ivan-cepeda-viabilidad",
        },
        {
            "candidato": "Abelardo Espriella",
            "titulo": "Plan de gobierno de Abelardo de la Espriella: qué propone y qué tan viable es",
            "url": "https://cambiocolombia.com/analisis-programa-gobierno-abelardo-espriella-propuestas-viabilidad-elecciones",
        },
    ],

    # ── El Espectador — cobertura de propuestas ──────────────────────────────
    "el_espectador": [
        {
            "candidato": "Ivan Cepeda",
            "titulo": "Propuestas de Iván Cepeda: su plan de gobierno completo",
            "url": "https://www.elespectador.com/politica/elecciones-colombia-2026/propuestas-de-ivan-cepeda-este-es-su-plan-de-gobierno/",
        },
    ],

    # ── El Tiempo — propuestas segunda vuelta ────────────────────────────────
    "el_tiempo": [
        {
            "candidato": "Abelardo Espriella",
            "titulo": "Los 10 pilares del gobierno de Espriella: Plan Colombia II, reducción Estado y 7 megacárceles",
            "url": "https://www.eltiempo.com/politica/elecciones-colombia-2026/abelardo-de-la-espriella-anuncio-los-10-pilares-de-su-gobierno-plan-colombia-ii-reduccion-del-estado-en-40-7-megacarceles-y-otras-medidas-3561778",
        },
        {
            "candidato": "Ambos",
            "titulo": "Análisis: propuestas de candidatos atienden los problemas centrales del país",
            "url": "https://www.elcolombiano.com/colombia/politica/elecciones-2026-economia-social-seguridad-temas-pesan-propuestas-candidatos-OK36968053",
        },
    ],

    # ── ColombiaElecciones.co — comparador neutral ───────────────────────────
    "colombia_elecciones": [
        {
            "candidato": "Ambos",
            "titulo": "Segunda vuelta Cepeda vs Espriella: propuestas, hoja de vida y comparador",
            "url": "https://www.colombiaelecciones.co/",
        },
    ],

    # ── Candidateados — propuestas verificadas ───────────────────────────────
    "candidateados": [
        {
            "candidato": "Ivan Cepeda",
            "titulo": "Propuestas verificadas de Iván Cepeda Castro — Candidateados 2026",
            "url": "https://www.candidateados.com/programa-de-gobierno-de/ivan-cepeda-castro",
        },
        {
            "candidato": "Abelardo Espriella",
            "titulo": "Propuestas verificadas de Abelardo de la Espriella — Candidateados 2026",
            "url": "https://www.candidateados.com/candidatos/abelardo-de-la-espriella",
        },
    ],
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower()
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
        text = text.replace(a, b)
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text[:70]


def fetch_text(url: str) -> tuple[str, bool]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script","style","nav","header","footer",
                          "aside","iframe","noscript","form"]):
            tag.decompose()

        for selector in ["article","[class*='article-body']","[class*='story-body']",
                          "[class*='nota-contenido']","main",".content","body"]:
            el = soup.select_one(selector)
            if el:
                lines = [l.strip() for l in el.get_text("\n").split("\n") if l.strip()]
                return "\n".join(lines), True

        return "[ERROR: no se pudo extraer contenido]", False

    except requests.exceptions.ConnectionError:
        return "[ERROR: sin conexión]", False
    except requests.exceptions.HTTPError as e:
        return f"[ERROR HTTP {e.response.status_code}]", False
    except Exception as e:
        return f"[ERROR: {e}]", False


def format_doc(fuente: str, meta: dict, content: str) -> str:
    return f"""FUENTE: {fuente}
FECHA_DESCARGA: {datetime.now().strftime('%Y-%m-%d')}
URL: {meta['url']}
TIPO: analisis-propuestas
CANDIDATO: {meta['candidato']}
TITULAR: {meta['titulo']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{content}
"""


def balance_check(articulos: dict) -> dict:
    cepeda   = sum(1 for arts in articulos.values()
                   for a in arts if "Cepeda" in a["candidato"])
    espriella = sum(1 for arts in articulos.values()
                    for a in arts if "Espriella" in a["candidato"])
    ambos    = sum(1 for arts in articulos.values()
                   for a in arts if a["candidato"] == "Ambos")
    return {"cepeda": cepeda, "espriella": espriella, "ambos": ambos,
            "diff": abs(cepeda - espriella)}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    bal = balance_check(ARTICULOS)
    total = sum(len(v) for v in ARTICULOS.values())

    print(f"\n📊 PLAN DE DESCARGA")
    print(f"   Cepeda:    {bal['cepeda']} artículos")
    print(f"   Espriella: {bal['espriella']} artículos")
    print(f"   Ambos:     {bal['ambos']} artículos")
    print(f"   Total:     {total}")
    if bal['diff'] > 1:
        print(f"   ⚠️  Desbalance de {bal['diff']} — revisar antes de indexar")
    else:
        print(f"   ✅ Balance OK")

    if args.dry_run:
        print(f"\n🔍 DRY RUN\n")
        for fuente, arts in ARTICULOS.items():
            print(f"  [{fuente}]")
            for a in arts:
                print(f"    [{a['candidato']:20}] {a['titulo'][:55]}")
        return

    print(f"\n🚀 Descargando {total} artículos...\n")
    done = ok = 0
    errores = []

    for fuente, arts in ARTICULOS.items():
        print(f"\n{'━'*55}")
        print(f"  📁 {fuente.upper()} ({len(arts)} artículos)")
        print(f"{'━'*55}")

        for meta in arts:
            done += 1
            print(f"\n  [{done}/{total}] {meta['titulo'][:60]}")
            print(f"          → {meta['candidato']}")

            content, success = fetch_text(meta["url"])

            if not success:
                print(f"          ✗ {content}")
                errores.append(meta)
                time.sleep(DELAY)
                continue

            folder = OUTPUT_DIR / fuente
            folder.mkdir(parents=True, exist_ok=True)
            fname = slugify(meta["titulo"]) + ".txt"
            (folder / fname).write_text(
                format_doc(fuente, meta, content), encoding="utf-8"
            )
            words = len(content.split())
            print(f"          ✅ {words} palabras → {fuente}/{fname}")
            ok += 1
            time.sleep(DELAY)

    print(f"\n{'━'*55}")
    print(f"  Descargados: {ok}/{total}")

    if errores:
        print(f"\n  ⚠️  FALLARON ({len(errores)}) — cópialos manualmente:")
        for e in errores:
            print(f"     [{e['candidato']}] {e['url']}")

    print(f"\n  📌 Siguiente paso:")
    print(f"     python backend/indexer.py")
    print()


if __name__ == "__main__":
    main()
