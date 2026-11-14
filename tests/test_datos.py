"""Pruebas del contenido de P6: guías, reglas, fichas, datos NASA y modelo 3D.
Escrito con asistencia de IA (Claude); revisado por el equipo."""

import json
import struct

import pytest

from conftest import ORGANOS_CONTRATO, clasificar, estado_demo_frontend
from guias import cargar_fragmentos, leer_guia

CAMPOS_FICHA = ["como_medir", "por_que", "efecto_espacio", "a_quien_avisar", "prevencion"]


def test_guias_tienen_encabezado_y_secciones(raiz):
    guias = sorted((raiz / "data" / "guias").glob("*.md"))
    assert len(guias) >= 10
    for ruta in guias:
        meta, cuerpo = leer_guia(ruta)
        for campo in ("titulo", "fuente", "url", "version", "estado"):
            assert meta.get(campo), f"{ruta.name}: falta '{campo}' en el encabezado"
        assert meta["url"].startswith("https://"), ruta.name
        assert cuerpo.count("## ") >= 4, f"{ruta.name}: muy pocas secciones"
        assert "Cuándo avisar" in cuerpo, f"{ruta.name}: falta la sección 'Cuándo avisar'"


def test_fragmentos_citables():
    frags = cargar_fragmentos()
    assert len(frags) >= 40
    assert all(f["guia"] and f["seccion"] and f["fuente"] for f in frags)


def test_reglas_coherentes(raiz, reglas):
    for r in reglas["indicadores"]:
        nombre = r["indicador"]
        assert r["organo"] in ORGANOS_CONTRATO, nombre
        assert (raiz / "data" / "guias" / r["guia"]).exists(), f"{nombre}: guía inexistente"
        assert r["fuente"] and r["accion"]["amarillo"] and r["accion"]["rojo"], nombre
        rangos = [r] if "verde" in r else list(r.get("componentes", {}).values())
        for c in rangos:
            v, a, p = c["verde"], c["amarillo"], c["posible"]
            assert a[0] <= v[0] <= v[1] <= a[1], f"{nombre}: verde debe estar dentro de amarillo"
            assert p[0] <= a[0] and a[1] <= p[1], f"{nombre}: amarillo debe estar dentro de posible"


@pytest.mark.parametrize("indicador,valor,esperado", [
    ("pulso", 72, "verde"), ("pulso", 110, "amarillo"), ("pulso", 150, "rojo"),
    ("presion_arterial", "118/76", "verde"), ("presion_arterial", "142/92", "amarillo"), ("presion_arterial", "170/105", "rojo"),
    ("oxigeno", 97, "verde"), ("oxigeno", 92, "amarillo"), ("oxigeno", 85, "rojo"),
    ("glucosa", 85, "verde"), ("glucosa", 103, "amarillo"), ("glucosa", 40, "rojo"),
    ("sueno", 7, "verde"), ("sueno", 4.5, "amarillo"), ("sueno", 3, "rojo"),
    ("animo", 4, "verde"), ("animo", 2, "amarillo"), ("animo", 1, "rojo"),
    ("vision", "sin cambios", "verde"), ("vision", "perdida brusca", "rojo"),
])
def test_semaforo(reglas, indicador, valor, esperado):
    regla = next(r for r in reglas["indicadores"] if r["indicador"] == indicador)
    assert clasificar(regla, valor) == esperado


def test_estado_demo_del_frontend_respeta_las_reglas(reglas):
    """Los colores de demostración del visor deben coincidir con reglas.json."""
    por_nombre = {r["indicador"]: r for r in reglas["indicadores"]}
    demo = estado_demo_frontend()
    assert len(demo) >= 8
    for d in demo:
        assert clasificar(por_nombre[d["indicador"]], d["valor"]) == d["color"], d


def test_estado_ejemplo_respeta_las_reglas(raiz, reglas):
    por_nombre = {r["indicador"]: r for r in reglas["indicadores"]}
    estado = json.loads((raiz / "data" / "estado_ejemplo.json").read_text(encoding="utf-8"))
    for i in estado["indicadores"]:
        if i["indicador"] in por_nombre:
            assert clasificar(por_nombre[i["indicador"]], i["valor"]) == i["color"], i


def test_fichas_completas(raiz, fichas, reglas):
    nombres = {r["indicador"] for r in reglas["indicadores"]}
    assert set(fichas["fichas"]) == ORGANOS_CONTRATO
    for organo, f in fichas["fichas"].items():
        for campo in CAMPOS_FICHA:
            assert f.get(campo), f"{organo}: falta '{campo}' (pregunta del reto)"
        assert set(f["indicadores"]) <= nombres, organo
        assert (raiz / "data" / "guias" / f["guia"]).exists(), organo


def test_datos_nasa_osd575(raiz):
    d = json.loads((raiz / "data" / "nasa_osd575.json").read_text(encoding="utf-8"))
    assert set(d["tripulantes"]) == {"C001", "C002", "C003", "C004"}
    glucosa = d["tripulantes"]["C003"]["glucosa"]
    assert glucosa["rango"] == [65.0, 99.0]
    assert list(glucosa["valores"]) == d["momentos"]
    assert glucosa["valores"]["R+1"] == 103.0   # valor real publicado por NASA OSDR


def test_modelo_3d_respeta_el_contrato(raiz):
    """El .glb debe traer un objeto por órgano con los nombres del contrato."""
    datos = (raiz / "frontend" / "modelos" / "cuerpo.glb").read_bytes()
    assert datos[:4] == b"glTF"
    largo, _tipo = struct.unpack_from("<II", datos, 12)
    gltf = json.loads(datos[20:20 + largo])
    nombres = {n.get("name") for n in gltf.get("nodes", [])}
    assert ORGANOS_CONTRATO <= nombres, f"faltan: {ORGANOS_CONTRATO - nombres}"
    assert len(datos) < 8_000_000, "el modelo debe pesar menos de 8 MB para la web"
