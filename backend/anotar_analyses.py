#!/usr/bin/env python3
"""
anotar_analyses.py
─────────────────────────────────────────────────────────────────────────────
Anota los análisis precalculados (backend/analyses/*.json) con el markup
{{término::explicación}} para los tooltips jurídicos del frontend.

Funciona 100% local, sin llamadas a ninguna API.

Uso:
    python backend/anotar_analyses.py              # anota todos los JSONs
    python backend/anotar_analyses.py --dry-run    # muestra cambios sin guardar
    python backend/anotar_analyses.py --archivo mi_analisis.json  # uno solo
    python backend/anotar_analyses.py --stats      # cuántos términos hay por archivo

Cómo funciona:
    1. Lee el diccionario de terminos_juridicos.py
    2. Para cada JSON en analyses/, busca los campos de texto
    3. Reemplaza ocurrencias de términos con {{término::explicación}}
    4. Guarda el JSON modificado (backup automático del original)
─────────────────────────────────────────────────────────────────────────────
"""

import re
import sys
import json
import shutil
import argparse
from pathlib import Path

# Importar diccionario (debe estar en el mismo directorio)
sys.path.insert(0, str(Path(__file__).parent))
from terminos_juridicos import TERMINOS

# ─── Rutas ───────────────────────────────────────────────────────────────────
ANALYSES_DIR = Path(__file__).parent / "analyses"
BACKUP_DIR   = Path(__file__).parent / "analyses_backup"

# ─── Configuración de anotación ──────────────────────────────────────────────

# Campos de texto dentro del JSON que se deben anotar.
# Ajusta según la estructura real de tus JSONs de análisis.
CAMPOS_TEXTO = [
    "texto",
    "resumen",
    "analisis",
    "cepeda",
    "espriella",
    "comparacion",
    "conclusion",
    "propuesta_cepeda",
    "propuesta_espriella",
    "descripcion",
    "contenido",
    "sintesis",
    "dimension",
    "evaluacion",
    # Añade aquí otros campos si tus JSONs tienen una estructura diferente
]

# Términos a NO marcar aunque aparezcan (muy comunes, se verían como ruido)
EXCLUIR = {
    "la", "el", "un", "una", "en", "de", "del", "los", "las",
    "paz",   # demasiado común y ambiguo
    "ley",   # ídem
    "aval",  # puede sonar natural en contexto
}

# ─── Motor de anotación ──────────────────────────────────────────────────────

def construir_patron(terminos: dict) -> re.Pattern:
    """
    Construye un regex que busca todos los términos del diccionario.
    Ordena de mayor a menor longitud para que "acción de tutela"
    gane sobre "tutela" cuando ambos están presentes.
    """
    terminos_ordenados = sorted(
        [t for t in terminos if t not in EXCLUIR],
        key=len,
        reverse=True
    )
    # Escapar términos y construir alternancia
    alternancia = "|".join(re.escape(t) for t in terminos_ordenados)
    # \b para boundaries de palabra, case-insensitive
    return re.compile(r'\b(' + alternancia + r')\b', re.IGNORECASE)


def anotar_texto(texto: str, patron: re.Pattern, terminos: dict) -> tuple[str, list]:
    """
    Anota un texto reemplazando términos con {{término::explicación}}.
    Evita anotar dos veces el mismo término en el mismo bloque de texto.
    Retorna (texto_anotado, lista_de_terminos_encontrados).
    """
    ya_anotados = set()
    encontrados = []

    def reemplazar(match):
        original = match.group(0)
        clave    = original.lower()

        # No repetir el mismo término en el mismo texto
        if clave in ya_anotados:
            return original

        # No anotar si ya está dentro de un {{...}}
        inicio = match.start()
        contexto_prev = texto[max(0, inicio - 2):inicio]
        if contexto_prev.endswith("{{") or contexto_prev.endswith("::"):
            return original

        ya_anotados.add(clave)
        explicacion = terminos[clave]
        encontrados.append(clave)
        return f"{{{{{original}::{explicacion}}}}}"

    resultado = patron.sub(reemplazar, texto)
    return resultado, encontrados


def anotar_valor(valor, patron: re.Pattern, terminos: dict) -> tuple:
    """
    Anota recursivamente un valor JSON (str, dict, list).
    Retorna (valor_anotado, conteo_de_anotaciones).
    """
    total = 0

    if isinstance(valor, str):
        anotado, encontrados = anotar_texto(valor, patron, terminos)
        return anotado, len(encontrados)

    elif isinstance(valor, dict):
        nuevo = {}
        for k, v in valor.items():
            # Anotar TODOS los campos string (estructura real: content, dimension, etc.)
            # Excepto campos de metadatos que no son texto narrativo
            SKIP_FIELDS = {"generated_at", "version", "id", "timestamp", "fecha"}
            if isinstance(v, str) and k.lower() not in SKIP_FIELDS:
                anotado, n = anotar_valor(v, patron, terminos)
                nuevo[k] = anotado
                total += n
            elif isinstance(v, (dict, list)):
                anotado, n = anotar_valor(v, patron, terminos)
                nuevo[k] = anotado
                total += n
            else:
                nuevo[k] = v
        return nuevo, total

    elif isinstance(valor, list):
        nuevo = []
        for item in valor:
            anotado, n = anotar_valor(item, patron, terminos)
            nuevo.append(anotado)
            total += n
        return nuevo, total

    return valor, 0


# ─── Procesamiento de archivos ───────────────────────────────────────────────

def procesar_archivo(ruta: Path, patron: re.Pattern, terminos: dict,
                     dry_run: bool = False) -> dict:
    """
    Lee un JSON, lo anota y (si no es dry_run) lo guarda.
    Retorna un dict con estadísticas.
    """
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"archivo": ruta.name, "error": str(e), "anotaciones": 0}

    datos_anotados, total = anotar_valor(datos, patron, terminos)

    if not dry_run and total > 0:
        # Backup del original
        BACKUP_DIR.mkdir(exist_ok=True)
        shutil.copy2(ruta, BACKUP_DIR / ruta.name)

        # Guardar versión anotada
        ruta.write_text(
            json.dumps(datos_anotados, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    return {
        "archivo":     ruta.name,
        "anotaciones": total,
        "guardado":    not dry_run and total > 0,
        "error":       None,
    }


def preview_cambios(ruta: Path, patron: re.Pattern, terminos: dict):
    """Muestra un preview de qué términos se anotarían en un archivo."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    _, n = anotar_valor(datos, patron, terminos)

    # Buscar todos los términos en el texto plano del JSON
    texto_plano = json.dumps(datos, ensure_ascii=False)
    encontrados_unicos = set()
    for match in patron.finditer(texto_plano):
        clave = match.group(0).lower()
        if clave not in EXCLUIR:
            encontrados_unicos.add(clave)

    return encontrados_unicos, n


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Anota análisis precalculados con tooltips jurídicos"
    )
    parser.add_argument("--dry-run",  action="store_true",
                        help="Muestra cambios sin guardar nada")
    parser.add_argument("--stats",    action="store_true",
                        help="Muestra estadísticas de términos por archivo y sale")
    parser.add_argument("--archivo",  type=str, default=None,
                        help="Procesar solo este archivo (nombre, no ruta completa)")
    args = parser.parse_args()

    if not ANALYSES_DIR.exists():
        print(f"❌ No se encontró la carpeta: {ANALYSES_DIR}")
        print("   Asegúrate de correr el script desde la raíz del proyecto.")
        sys.exit(1)

    # Construir regex una sola vez
    patron = construir_patron(TERMINOS)
    print(f"\n📚 Diccionario cargado: {len(TERMINOS)} términos")
    print(f"   Regex construido con {len([t for t in TERMINOS if t not in EXCLUIR])} términos activos\n")

    # Seleccionar archivos
    if args.archivo:
        archivos = [ANALYSES_DIR / args.archivo]
        if not archivos[0].exists():
            print(f"❌ Archivo no encontrado: {archivos[0]}")
            sys.exit(1)
    else:
        archivos = sorted(ANALYSES_DIR.glob("*.json"))

    if not archivos:
        print(f"⚠️  No se encontraron archivos JSON en {ANALYSES_DIR}")
        sys.exit(0)

    print(f"📁 Archivos a procesar: {len(archivos)}")

    # ── Modo estadísticas ────────────────────────────────────────────────────
    if args.stats:
        print("\n📊 TÉRMINOS DETECTADOS POR ARCHIVO")
        print("─" * 60)
        total_global = 0
        for ruta in archivos:
            terminos_encontrados, n = preview_cambios(ruta, patron, TERMINOS)
            total_global += n
            print(f"\n  📄 {ruta.name} ({n} anotaciones)")
            if terminos_encontrados:
                for t in sorted(terminos_encontrados):
                    print(f"      → {t}")
            else:
                print("      (ningún término del diccionario encontrado)")
        print(f"\n{'─'*60}")
        print(f"  Total de anotaciones posibles: {total_global}")
        return

    # ── Modo dry-run o real ──────────────────────────────────────────────────
    modo = "DRY RUN — sin guardar cambios" if args.dry_run else "ANOTACIÓN REAL"
    print(f"\n{'━'*60}")
    print(f"  MODO: {modo}")
    if not args.dry_run:
        print(f"  Backups en: {BACKUP_DIR}/")
    print(f"{'━'*60}\n")

    resultados  = []
    total_anot  = 0
    total_err   = 0

    for ruta in archivos:
        resultado = procesar_archivo(ruta, patron, TERMINOS, dry_run=args.dry_run)
        resultados.append(resultado)
        n = resultado["anotaciones"]
        total_anot += n

        if resultado["error"]:
            total_err += 1
            print(f"  ✗ {ruta.name} — ERROR: {resultado['error']}")
        elif n == 0:
            print(f"  ○ {ruta.name} — sin términos detectados")
        else:
            accion = "simulado" if args.dry_run else "guardado"
            print(f"  ✅ {ruta.name} — {n} anotaciones ({accion})")

    # ── Resumen ──────────────────────────────────────────────────────────────
    print(f"\n{'━'*60}")
    print(f"  Archivos procesados : {len(archivos)}")
    print(f"  Total anotaciones   : {total_anot}")
    if total_err:
        print(f"  Errores             : {total_err}")
    if not args.dry_run and total_anot > 0:
        print(f"  Backups guardados en: {BACKUP_DIR}/")
    print(f"{'━'*60}")

    if args.dry_run and total_anot > 0:
        print("\n  Para aplicar los cambios, corre sin --dry-run:")
        print("  python backend/anotar_analyses.py")
    elif not args.dry_run and total_anot > 0:
        print("\n  ✅ Listo. Re-inicia el backend para que tome los cambios.")
        print("     (Los análisis precalculados se sirven directamente desde el JSON)")

    print()


if __name__ == "__main__":
    main()
