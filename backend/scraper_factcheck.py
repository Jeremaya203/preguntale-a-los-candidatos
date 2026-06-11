#!/usr/bin/env python3
"""
scraper_factcheck.py
────────────────────────────────────────────────────────────────────────────────
Descarga artículos de verificación de fuentes independientes para el RAG
de Pregúntale a los Candidatos 2026.

Uso:
    python scraper_factcheck.py              # descarga todo
    python scraper_factcheck.py --dry-run    # solo muestra el plan
    python scraper_factcheck.py --balance    # verifica simetría y sale

Fuentes priorizadas por neutralidad:
    ✅ EFE Verifica      — agencia internacional, sin agenda local
    ✅ AFP Factual        — ídem
    ✅ La Liga c/ Silencio — investigativo, especializado en desinformación
    ✅ Cazadores Fake News — fact-checking latinoamericano
    ⚠️  ColombiaCheck     — independiente pero con sesgos editoriales documentados
    ⚠️  La Silla Vacía    — investigativo confiable, algunas columnas tienen posición
    ❌ Semana / Caracol / RCN — NO incluir, sesgo alto

Salida:
    backend/documents/fact-checking/
    ├── contra_cepeda/         ← fake news sobre Cepeda, debunkeadas por fuentes neutrales
    │   ├── efe_verifica/
    │   ├── afp_factual/
    │   ├── colombia_check/
    │   └── la_liga/
    ├── contra_espriella/      ← ídem para Espriella
    │   └── ...
    └── general/               ← encuestas falsas, montajes que afectan a ambos
        └── ...
────────────────────────────────────────────────────────────────────────────────
"""

import os
import re
import sys
import time
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

# ─── Configuración ───────────────────────────────────────────────────────────

# Ajusta esta ruta si corres el script desde otro lugar
OUTPUT_DIR = Path(__file__).parent.parent / "backend" / "documents" / "fact-checking"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}

DELAY_BETWEEN_REQUESTS = 2.0   # segundos — no spamear los servidores
REQUEST_TIMEOUT        = 20    # segundos

# ─── Artículos conocidos por categoría ───────────────────────────────────────
#
# REGLA DE ORO: por cada artículo que se agrega a contra_cepeda,
# debe existir un equivalente en contra_espriella, y viceversa.
# El script verifica esto automáticamente.
#
# Para agregar más: copiar el bloque {"url": ..., "source": ..., "title": ...}
# en la categoría correspondiente.

ARTICULOS = {

    # ── Fake news CONTRA CEPEDA (publicadas por simpatizantes de Espriella) ──
    "contra_cepeda": [
        {
            "source": "EFE Verifica",
            "title": "El ELN no declaró apoyo a Cepeda ni amenazó con violencia si pierde",
            "url": "https://www.infobae.com/america/agencias/2026/06/10/"
                   "el-eln-no-declaro-su-apoyo-a-cepeda-ni-amenazo-con-causar-"
                   "violencia-si-pierde-los-comicios/",
            "candidato_afectado": "Iván Cepeda",
            "acusacion_falsa": "El ELN declaró apoyo a Cepeda y amenazó con represalias armadas si pierde",
        },
        {
            "source": "ColombiaCheck Investigaciones",
            "title": "340 anuncios pagados en Meta para asociar a Cepeda con las FARC",
            "url": "https://colombiacheck.com/investigaciones/"
                   "340-anuncios-pagados-en-meta-amplificaron-narrativas-para-"
                   "asociar-ivan-cepeda-con",
            "candidato_afectado": "Iván Cepeda",
            "acusacion_falsa": "Campaña coordinada y pagada asociando a Cepeda con las FARC",
        },
        {
            "source": "El Filtro (AFP + El Tiempo)",
            "title": "Video viral: Cepeda pedía respeto por organizaciones campesinas, no por las FARC",
            "url": "https://www.eltiempo.com/amp/politica/elecciones-colombia-2026/"
                   "elfiltro-candidato-presidencial-ivan-cepeda-pide-respeto-por-dos-"
                   "organizaciones-campesinas-en-un-video-viral-no-por-las-farc-3546117",
            "candidato_afectado": "Iván Cepeda",
            "acusacion_falsa": "Video manipulado: Cepeda pidiendo 'respeto para las FARC'",
        },
        {
            "source": "La Liga Contra el Silencio",
            "title": "Mención de Cepeda en computadores de Raúl Reyes: contexto completo",
            "url": "https://ligacontraelsilencio.com/2026/02/22/"
                   "mencion-de-ivan-cepeda-en-computador-de-las-farc-no-fue-un-montaje/",
            "candidato_afectado": "Iván Cepeda",
            "acusacion_falsa": "Los archivos de Raúl Reyes prueban que Cepeda era aliado de las FARC",
        },
        {
            "source": "ColombiaCheck",
            "title": "Falso: Cepeda prometió subir el salario mínimo a $5 millones",
            "url": "https://colombiacheck.com/chequeos/"
                   "ivan-cepeda-no-prometio-aumentar-el-salario-minimo-5-millones-"
                   "como-afirma-un-montaje",
            "candidato_afectado": "Iván Cepeda",
            "acusacion_falsa": "Montaje: Cepeda prometió salario mínimo de $5.000.000",
        },
        {
            "source": "ColombiaCheck",
            "title": "El 70.24% atribuido a Cepeda es de sondeo sin metodología, no encuesta real",
            "url": "https://colombiacheck.com/chequeos/"
                   "el-7024-atribuido-ivan-cepeda-proviene-de-un-sondeo-sin-"
                   "metodologia-y-no-de-una-encuesta",
            "candidato_afectado": "Iván Cepeda",
            "acusacion_falsa": "Encuesta muestra a Cepeda con 70.24% de intención de voto",
        },
    ],

    # ── Fake news CONTRA ESPRIELLA (publicadas por simpatizantes de Cepeda) ──
    "contra_espriella": [
        {
            "source": "ColombiaCheck",
            "title": "Falso: imágenes atribuyen a Espriella promesa de bajar salario mínimo",
            "url": "https://colombiacheck.com/chequeos/"
                   "imagenes-falsas-atribuyen-de-la-espriella-la-promesa-de-bajar-"
                   "el-salario-minimo",
            "candidato_afectado": "Abelardo de la Espriella",
            "acusacion_falsa": "Espriella prometió bajar salario mínimo a $1.25M o $1.45M",
        },
        {
            "source": "ColombiaCheck",
            "title": "Falso: Espriella prometió bajar salario a $800,000 como 'Bukele colombiano'",
            "url": "https://colombiacheck.com/chequeos/"
                   "promesa-de-reducir-el-salario-minimo-es-falsa-atribucion-de-la-"
                   "espriella-como-bukele",
            "candidato_afectado": "Abelardo de la Espriella",
            "acusacion_falsa": "Espriella prometió bajar salario mínimo a $800.000",
        },
        {
            "source": "ColombiaCheck",
            "title": "Falsa cita: Espriella nunca prometió irse del país si no gana",
            "url": "https://colombiacheck.com/chequeos/"
                   "falsa-atribucion-de-cita-de-la-espriella-dice-que-prometio-irse-"
                   "del-pais-si-no-gana-las",
            "candidato_afectado": "Abelardo de la Espriella",
            "acusacion_falsa": "Espriella prometió abandonar Colombia si pierde las elecciones",
        },
        {
            "source": "ColombiaCheck",
            "title": "Falsa encuesta muestra a Espriella con 55.8% y a Cepeda con 8.5%",
            "url": "https://colombiacheck.com/chequeos/"
                   "falsa-encuesta-muestra-de-la-espriella-con-558-contra-85-de-cepeda",
            "candidato_afectado": "Abelardo de la Espriella",
            "acusacion_falsa": "Encuesta Invamer muestra a Espriella con 55.8% vs 8.5% de Cepeda",
        },
        {
            "source": "ColombiaCheck",
            "title": "Sondeo en redes infla a Espriella con 80% y circula como encuesta oficial",
            "url": "https://colombiacheck.com/chequeos/"
                   "sondeo-en-redes-infla-abelardo-de-la-espriella-y-circula-como-"
                   "si-fuera-una-encuesta",
            "candidato_afectado": "Abelardo de la Espriella",
            "acusacion_falsa": "Encuesta oficial muestra a Espriella con 80% de intención de voto",
        },
        {
            "source": "Cazadores de Fake News / Rutas del Conflicto",
            "title": "Acusaciones infundadas de campaña Espriella contra periodistas independientes",
            "url": "https://rutasdelconflicto.com/notas/"
                   "asi-opera-la-red-ataques-los-periodistas-critican-abelardo-la-espriella",
            "candidato_afectado": "Abelardo de la Espriella (generado por su campaña)",
            "acusacion_falsa": "La Silla Vacía, Coronell y Cambio operan 'bodegas' coordinadas contra Espriella",
        },
    ],

    # ── Fake news GENERALES (afectan a ambos o al proceso electoral) ─────────
    "general": [
        {
            "source": "El Tiempo / AFP (El Filtro)",
            "title": "Las fake news crecen como principal amenaza en la segunda vuelta",
            "url": "https://www.eltiempo.com/politica/elecciones-colombia-2026/"
                   "las-fake-news-crecen-como-la-principal-amenaza-en-la-antesala-"
                   "de-la-segunda-vuelta-3562646",
            "candidato_afectado": "Ambos",
            "acusacion_falsa": "Múltiples — resumen de 190 incidencias entre mayo 5-30",
        },
        {
            "source": "La Silla Vacía - Detector de Mentiras",
            "title": "Las mentiras más virales sobre Cepeda, De la Espriella y Valencia",
            "url": "https://www.lasillavacia.com/detector-de-mentiras/"
                   "detector-las-mentiras-mas-virales-sobre-cepeda-de-la-espriella-y-valencia/",
            "candidato_afectado": "Ambos",
            "acusacion_falsa": "Múltiples — resumen de desinformación durante la campaña",
        },
        {
            "source": "Infobae / MOE",
            "title": "Cómo detectar noticias falsas sobre Cepeda y Espriella",
            "url": "https://www.infobae.com/tecno/2026/05/30/"
                   "elecciones-presidenciales-2026-asi-puede-detectar-noticias-"
                   "falsas-y-desinformacion-sobre-cepeda-paloma-y-abelardo/",
            "candidato_afectado": "Ambos",
            "acusacion_falsa": "Guía general de desinformación electoral 2026",
        },
    ],
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[áàä]', 'a', text)
    text = re.sub(r'[éèë]', 'e', text)
    text = re.sub(r'[íìï]', 'i', text)
    text = re.sub(r'[óòö]', 'o', text)
    text = re.sub(r'[úùü]', 'u', text)
    text = re.sub(r'ñ', 'n', text)
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text[:70]


def source_to_folder(source: str) -> str:
    """Convierte nombre de fuente a nombre de carpeta"""
    mapping = {
        "EFE Verifica":                   "efe_verifica",
        "AFP Factual":                    "afp_factual",
        "El Filtro (AFP + El Tiempo)":    "el_filtro_afp",
        "ColombiaCheck Investigaciones":  "colombia_check",
        "ColombiaCheck":                  "colombia_check",
        "La Liga Contra el Silencio":     "la_liga",
        "Cazadores de Fake News / Rutas del Conflicto": "cazadores_fakenews",
        "Rutas del Conflicto":            "rutas_conflicto",
        "La Silla Vacía - Detector de Mentiras": "la_silla_vacia",
        "La Silla Vacía":                 "la_silla_vacia",
        "El Tiempo / AFP (El Filtro)":    "el_filtro_afp",
        "Infobae / MOE":                  "moe_infobae",
    }
    for key, val in mapping.items():
        if key in source:
            return val
    return slugify(source)


def fetch_text(url: str) -> tuple[str, bool]:
    """Descarga una URL y extrae el texto limpio. Retorna (texto, éxito)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remover elementos no-contenido
        for tag in soup(["script", "style", "nav", "header",
                         "footer", "aside", "iframe", "figure",
                         "noscript", "form"]):
            tag.decompose()

        # Selectores de contenido principal (orden de preferencia)
        for selector in [
            "article",
            "[class*='article-body']",
            "[class*='story-body']",
            "[class*='article-content']",
            "[class*='nota-contenido']",
            "main",
            ".content",
            "#content",
            "body",
        ]:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n", strip=True)
                break
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Limpiar líneas vacías consecutivas
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines), True

    except requests.exceptions.ConnectionError:
        return "[ERROR: no se pudo conectar — ¿acceso a internet?]", False
    except requests.exceptions.Timeout:
        return "[ERROR: timeout después de {} segundos]".format(REQUEST_TIMEOUT), False
    except requests.exceptions.HTTPError as e:
        return "[ERROR HTTP: {}]".format(e), False
    except Exception as e:
        return "[ERROR inesperado: {}]".format(e), False


def format_document(meta: dict, category: str, content: str) -> str:
    """Formatea el documento en el template que espera el RAG."""
    return f"""FUENTE: {meta['source']}
FECHA_DESCARGA: {datetime.now().strftime('%Y-%m-%d')}
URL: {meta['url']}
CATEGORIA: fact-checking / {category}
CANDIDATO_AFECTADO: {meta['candidato_afectado']}
TITULAR: {meta['title']}
ACUSACION_FALSA: {meta['acusacion_falsa']}
VEREDICTO: FALSO / DESMENTIDO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{content}
"""


def check_balance() -> dict:
    """Verifica que haya simetría entre categorías."""
    counts = {cat: len(arts) for cat, arts in ARTICULOS.items()}
    diff = abs(counts.get("contra_cepeda", 0) - counts.get("contra_espriella", 0))
    return {"counts": counts, "diferencia": diff, "balanceado": diff <= 2}

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper de fact-checking simétrico")
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra el plan sin descargar nada")
    parser.add_argument("--balance", action="store_true",
                        help="Solo verifica simetría y sale")
    args = parser.parse_args()

    # ── Verificar balance ────────────────────────────────────────────────────
    balance = check_balance()
    print("\n📊 VERIFICACIÓN DE SIMETRÍA")
    print("─" * 40)
    for cat, count in balance["counts"].items():
        emoji = "✅" if "cepeda" not in cat and "espriella" not in cat else "📌"
        print(f"  {emoji} {cat}: {count} artículos")
    if balance["balanceado"]:
        print("\n  ✅ Balance OK (diferencia ≤ 2 artículos)")
    else:
        print(f"\n  ⚠️  DESBALANCE: diferencia de {balance['diferencia']} artículos")
        print("     Agrega más artículos a la categoría menor antes de indexar.")
    print()

    if args.balance:
        return

    # ── Dry run ─────────────────────────────────────────────────────────────
    if args.dry_run:
        print("🔍 MODO DRY RUN — no se descarga nada\n")
        for cat, arts in ARTICULOS.items():
            print(f"  [{cat}]")
            for a in arts:
                folder = source_to_folder(a["source"])
                print(f"    → {a['source'][:30]:<30} | {a['title'][:50]}")
            print()
        return

    # ── Descarga real ────────────────────────────────────────────────────────
    total   = sum(len(v) for v in ARTICULOS.values())
    done    = 0
    ok      = 0
    errores = []

    print(f"🚀 Iniciando descarga de {total} artículos...\n")

    for category, article_list in ARTICULOS.items():
        print(f"\n{'━'*60}")
        print(f"  📁 {category.upper()} ({len(article_list)} artículos)")
        print(f"{'━'*60}")

        for meta in article_list:
            done += 1
            print(f"\n  [{done}/{total}] {meta['title'][:65]}")
            print(f"          Fuente: {meta['source']}")

            content, success = fetch_text(meta["url"])

            if not success:
                print(f"          ✗ {content}")
                errores.append({"url": meta["url"], "error": content})
                time.sleep(DELAY_BETWEEN_REQUESTS)
                continue

            # Guardar
            folder_name = source_to_folder(meta["source"])
            out_folder  = OUTPUT_DIR / category / folder_name
            out_folder.mkdir(parents=True, exist_ok=True)

            filename = slugify(meta["title"]) + ".txt"
            filepath = out_folder / filename
            filepath.write_text(
                format_document(meta, category, content),
                encoding="utf-8"
            )

            word_count = len(content.split())
            print(f"          ✅ Guardado ({word_count} palabras) → {filepath.relative_to(OUTPUT_DIR.parent.parent)}")
            ok += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # ── Resumen ──────────────────────────────────────────────────────────────
    print(f"\n{'━'*60}")
    print(f"  COMPLETADO: {ok}/{total} artículos descargados")

    if errores:
        print(f"\n  ⚠️  ERRORES ({len(errores)}):")
        for e in errores:
            print(f"     - {e['url']}")
            print(f"       {e['error']}")
        print("\n  → Abre esas URLs manualmente, copia el texto y guárdalo")
        print("    en el formato indicado en backend/documents/fact-checking/")

    print(f"{'━'*60}")

    # Guardar índice JSON
    index = {
        "generado":    datetime.now().isoformat(),
        "total":       total,
        "descargados": ok,
        "errores":     len(errores),
        "balance":     balance,
        "articulos":   {
            cat: [{"title": a["title"], "source": a["source"]} for a in arts]
            for cat, arts in ARTICULOS.items()
        },
    }
    index_path = OUTPUT_DIR / "indice.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"\n  📋 Índice guardado en {index_path}")

    # Recordatorio de simetría
    if not balance["balanceado"]:
        print("\n  ⚠️  Recuerda: hay desbalance. Antes de re-indexar,")
        print("     agrega artículos a la categoría menor.")

    print("\n  📌 Próximo paso:")
    print("     cd ~/preguntale-a-los-candidatos")
    print("     source venv/bin/activate")
    print("     python backend/indexer.py")
    print()


if __name__ == "__main__":
    main()
