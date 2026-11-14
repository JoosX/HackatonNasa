"""Convierte el panel metabólico de NASA OSDR OSD-575 (Inspiration4) a data/nasa_osd575.json.

    python scripts/convertir_osd575.py [ruta_csv]

Sin argumento, descarga el CSV oficial desde OSDR (necesita internet una sola vez).
Fuente: https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
Archivo: LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv

Momentos: L-92, L-44, L-3 = días antes del lanzamiento; R+1, R+45, R+82, R+194 = días después del regreso.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "nasa_osd575.json"
URL = ("https://osdr.nasa.gov/geode-py/ws/studies/OSD-575/download?source=datamanager"
       "&file=LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv")

# Analitos que mostramos (nombre en el CSV -> nombre y unidad en la app).
ANALITOS = {
    "glucose": ("glucosa", "mg/dL"),
    "calcium": ("calcio", "mg/dL"),
    "sodium": ("sodio", "mmol/L"),
    "potassium": ("potasio", "mmol/L"),
    "creatinine": ("creatinina", "mg/dL"),
}
ORDEN = ["L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"]


def numero(x: str):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main() -> None:
    if len(sys.argv) > 1:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8-sig")   # el CSV trae BOM
    else:
        with urllib.request.urlopen(URL, timeout=60) as r:
            texto = r.read().decode("utf-8-sig")
    filas = list(csv.DictReader(io.StringIO(texto)))
    tripulantes: dict = {}
    for fila in filas:
        muestra = fila["Sample Name"]                 # p. ej. C001_serum_L-3
        tripulante, _, momento = muestra.split("_", 2)
        for clave_csv, (nombre, unidad) in ANALITOS.items():
            col = next((c for c in fila if c.startswith(f"{clave_csv}_value")), None)
            cmin = next((c for c in fila if c.startswith(f"{clave_csv}_range_min")), None)
            cmax = next((c for c in fila if c.startswith(f"{clave_csv}_range_max") or c.startswith(f"{clave_csv}_max")), None)
            if not col:
                continue
            serie = tripulantes.setdefault(tripulante, {}).setdefault(nombre, {
                "unidad": unidad, "rango": [numero(fila.get(cmin)), numero(fila.get(cmax))], "valores": {}})
            serie["valores"][momento] = numero(fila[col])

    salida = {
        "fuente": "NASA OSDR OSD-575 – SpaceX Inspiration4, Comprehensive Metabolic Panel",
        "url": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-575",
        "momentos": ORDEN,
        "nota": "L = días antes del lanzamiento; R = días después del regreso. Misión de 3 días; muestras antes y después del vuelo, no durante.",
        "tripulantes": {t: {a: {**s, "valores": {m: s["valores"].get(m) for m in ORDEN}} for a, s in d.items()}
                        for t, d in sorted(tripulantes.items())},
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(salida['tripulantes'])} tripulantes · {len(ANALITOS)} analitos -> {SALIDA}")


if __name__ == "__main__":
    main()
