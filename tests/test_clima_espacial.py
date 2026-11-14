"""Pruebas del clima espacial con NASA DONKI. Escrito con asistencia de IA (Claude); revisado por el equipo."""

import datetime as dt
import json

import clima_espacial as ce

AHORA = dt.datetime(2026, 11, 14, 22, 0, tzinfo=dt.timezone.utc)


def datos(*eventos, sincronizado="2026-11-14T21:00Z"):
    return {"sincronizado": sincronizado, "desde": "2026-10-15", "hasta": "2026-11-14", "eventos": list(eventos)}


def test_sin_eventos_recientes_es_verde():
    r = ce.evaluar(datos({"tipo": "llamarada", "clase": "M1.7", "pico": "2026-11-11T21:21Z"}), AHORA)
    assert r["color"] == "verde" and r["valor"].startswith("M1.7")


def test_particulas_solares_es_rojo_y_manda_al_area_protegida():
    r = ce.evaluar(datos({"tipo": "particulas", "clase": "SEP", "pico": "2026-11-14T10:00Z"}), AHORA)
    assert r["color"] == "rojo" and "área protegida" in r["accion"]


def test_llamarada_fuerte_reciente_es_precaucion():
    assert ce.evaluar(datos({"tipo": "llamarada", "clase": "X1.2", "pico": "2026-11-13T00:00Z"}), AHORA)["color"] == "amarillo"
    assert ce.evaluar(datos({"tipo": "llamarada", "clase": "M2.0", "pico": "2026-11-14T12:00Z"}), AHORA)["color"] == "amarillo"
    assert ce.evaluar(datos({"tipo": "tormenta_geomagnetica", "clase": "Kp 8", "kp": 8, "pico": "2026-11-13T00:00Z"}), AHORA)["color"] == "amarillo"


def test_datos_viejos_avisan_su_antiguedad():
    r = ce.evaluar(datos(sincronizado="2026-11-08T00:00Z"), AHORA)
    assert "sin sincronizar" in r["motivo"]


def test_sin_archivo_no_rompe():
    assert ce.evaluar(None, AHORA)["color"] == "sin dato"


def test_archivo_real_de_donki(raiz):
    d = json.loads((raiz / "data" / "nasa_donki.json").read_text(encoding="utf-8"))
    assert d["eventos"] and d["sincronizado"] and "DONKI" in d["fuente"]
    assert {"tipo", "clase", "pico"} <= set(d["eventos"][0])
