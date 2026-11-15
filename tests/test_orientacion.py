"""Orientación por indicador y recorrido urgente.

Basado en las pruebas de Romario (rama romario/orientacion-fundamentada), adaptado a esta versión:
aquí ORI responde a las urgencias con sus protocolos de emergencia (backend/emergencia.py).
"""
import json

import pytest
from fastapi.testclient import TestClient

import ollama_cliente
import rag
from backend.main import app
from guias import CARPETA_GUIAS, RAIZ, cargar_fragmentos, fragmentar, leer_guia
from orientacion import CATALOGO, biblioteca


@pytest.mark.parametrize("nombre", list(CATALOGO))
def test_todos_los_indicadores_tienen_medicion_fuente_y_revision(nombre):
    g = biblioteca()["indicadores"][nombre]
    for campo in ("equipo", "como_medir", "por_que", "cuando_avisar", "archivo", "version", "fuente", "estado_revision"):
        assert g[campo]
    assert "ilustrativo" in g["estado_revision"]
    assert g["url"].startswith("https://")
    assert "no es un protocolo oficial NASA" in g["autor_contenido"]


@pytest.mark.parametrize("nombre", list(CATALOGO))
def test_medicion_y_limites_trazables(nombre):
    g = biblioteca()["indicadores"][nombre]
    m = g["medicion"]
    assert all(m[c] for c in ("preparacion", "errores", "sin_equipo", "alcance"))
    assert len(m["pasos"]) >= 3
    assert m["fuente"]["url"].startswith("https://")
    assert not g["regla"]["validacion"]["aprobado_para_uso_clinico"]
    assert g["regla"]["validacion"]["estado"] == "pendiente_revision_medica"


def test_api_orientacion_no_necesita_ollama(monkeypatch):
    def no_llamar(*a, **k):
        raise AssertionError("La biblioteca no debe invocar la IA")
    monkeypatch.setattr(ollama_cliente, "chatear", no_llamar)
    monkeypatch.setattr(ollama_cliente, "embeber", no_llamar)
    r = TestClient(app).get("/api/orientacion")
    assert r.status_code == 200
    assert set(r.json()["indicadores"]) == set(CATALOGO)


def test_pasos_y_aviso_conservan_el_texto_de_las_guias():
    for g in biblioteca()["indicadores"].values():
        meta, cuerpo = leer_guia(CARPETA_GUIAS / g["archivo"])
        secciones = {f["seccion"]: f["texto"] for f in fragmentar(meta, cuerpo)}
        assert all(p in secciones["Qué hacer"] for p in g["pasos_guia"])
        assert g["cuando_avisar"] == secciones["Cuándo avisar"]


@pytest.mark.parametrize("pregunta", ["Me duele el pecho", "Mi compañero no responde y solo jadea",
                                      "Me cuesta respirar", "Se desplomó", "Tuvo un desmayo"])
def test_sintomas_priorizan_ayuda_sin_ia_ni_busqueda(monkeypatch, pregunta):
    def prohibido(*a, **k):
        raise AssertionError("No debe esperar a búsqueda o IA")
    monkeypatch.setattr(rag, "buscar", prohibido)
    monkeypatch.setattr(ollama_cliente, "chatear", prohibido)
    r = rag.responder(pregunta, {"indicadores": [{"indicador": "pulso", "valor": 80, "color": "verde"}]})
    assert r["modo"] in ("emergencia", "emergencia_companero")
    assert r["alerta_roja"]
    assert "Emergencia médica" in r["respuesta"]


def test_un_indice_antiguo_no_devuelve_consejos_retirados(tmp_path, monkeypatch):
    actual = cargar_fragmentos()
    anterior = [dict(f, vector=[1]) for f in actual]
    anterior[0]["texto"] = "Consejo antiguo no vigente"
    ruta = tmp_path / "indice.json"
    ruta.write_text(json.dumps({"fragmentos": anterior}), encoding="utf-8")
    monkeypatch.setattr(rag, "INDICE", ruta)
    rag.recargar()
    try:
        assert rag._fragmentos() == actual
        assert all("vector" not in f for f in rag._fragmentos())
    finally:
        rag.recargar()


def test_no_hay_esperas_clinicas_inventadas():
    reglas = json.loads((RAIZ / "data/reglas.json").read_text(encoding="utf-8"))
    assert all("15 minutos" not in str(r["accion"]) and "30 minutos" not in str(r["accion"]) for r in reglas["indicadores"])
    import emergencia
    estado = {"indicadores": [{"indicador": "pulso", "valor": 148, "unidad": "lpm", "color": "rojo"}]}
    assert "15 minutos" not in emergencia.protocolo_alerta(estado, False)[0]
