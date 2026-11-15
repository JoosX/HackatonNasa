"""Compara las 20 series del explorador con el CSV original incluido en la rama."""
import csv
import json


def test_todas_las_series_coinciden_con_el_csv(raiz):
    datos = json.loads((raiz / "data/nasa_osd575.json").read_text(encoding="utf-8"))
    with (raiz / "data/fuentes/OSD-575_CMP_TRANSFORMED.csv").open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    analitos = {"glucosa": "glucose", "calcio": "calcium", "sodio": "sodium", "potasio": "potassium", "creatinina": "creatinine"}
    for persona, series in datos["tripulantes"].items():
        for nombre, prefijo in analitos.items():
            for momento, valor in series[nombre]["valores"].items():
                fila = next((f for f in filas if f["Sample Name"] == f"{persona}_serum_{momento}"), None)
                if fila is None:
                    assert valor is None
                    continue
                columna = next(c for c in fila if c.startswith(prefijo + "_value"))
                original = fila[columna].strip()
                assert valor == (float(original) if original else None), (persona, nombre, momento)
