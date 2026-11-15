"""La app en español y en inglés: datos traducidos completos, API y ORI en el idioma elegido.

Escrito con asistencia de IA (Claude); revisado por el equipo.
"""
import json
import re

import pytest
from fastapi.testclient import TestClient

import idioma
import rag
from backend.main import app
from guias import RAIZ, fragmentar, leer_guia

ROJO = {"modo_demo": True, "indicadores": [
    {"indicador": "pulso", "valor": 148, "unidad": "bpm", "color": "rojo"},
    {"indicador": "oxigeno", "valor": 97, "unidad": "%", "color": "verde"}]}


@pytest.fixture
def cliente():
    return TestClient(app)


# ---------- Datos traducidos ----------
def test_cada_guia_tiene_version_en_ingles_con_la_misma_estructura():
    es = sorted((RAIZ / "data" / "guias").glob("*.md"))
    en = {p.name: p for p in (RAIZ / "data" / "guias_en").glob("*.md")}
    assert [p.name for p in es] == sorted(en)
    for ruta in es:
        meta_es, cuerpo_es = leer_guia(ruta)
        meta_en, cuerpo_en = leer_guia(en[ruta.name])
        assert len(fragmentar(meta_es, cuerpo_es)) == len(fragmentar(meta_en, cuerpo_en)), ruta.name
        assert cuerpo_es.count("\n- ") == cuerpo_en.count("\n- "), ruta.name   # mismos pasos
        assert meta_en["url"] == meta_es["url"] and meta_en["version"] == meta_es["version"]
        assert "illustrative" in meta_en["estado"]
        with idioma.usar("en"):
            assert idioma.seccion("avisar") in [f["seccion"] for f in fragmentar(meta_en, cuerpo_en)], ruta.name


def test_datos_en_ingles_sin_texto_en_espanol():
    for nombre in ("fichas.json", "medicion_guiada.json", "reglas.json"):
        texto = (RAIZ / "data" / "en" / nombre).read_text(encoding="utf-8")
        sin_claves = re.sub(r'"[a-z_]+":', "", texto)            # las claves internas siguen en español
        sin_claves = re.sub(r'"(sin cambios|cambio leve|perdida brusca)"', "", sin_claves)
        assert not re.search(r"[áéíóúñ¿¡]", sin_claves), nombre


def test_capa_de_reglas_cubre_todo_y_conserva_los_rangos():
    base = json.loads((RAIZ / "data" / "reglas.json").read_text(encoding="utf-8"))
    with idioma.usar("en"):
        en = idioma.reglas()
    for r_es, r_en in zip(base["indicadores"], en["indicadores"]):
        assert r_es["indicador"] == r_en["indicador"]
        assert r_es.get("verde") == r_en.get("verde") and r_es.get("amarillo") == r_en.get("amarillo")
        assert r_es["nombre"] != r_en["nombre"]
        assert set(r_en["accion"]) == set(r_es["accion"])
        assert not r_en["validacion"]["aprobado_para_uso_clinico"]


def test_fichas_en_ingles_completas():
    es = json.loads((RAIZ / "data" / "fichas.json").read_text(encoding="utf-8"))["fichas"]
    en = json.loads((RAIZ / "data" / "en" / "fichas.json").read_text(encoding="utf-8"))["fichas"]
    assert set(es) == set(en)
    for k in es:
        assert en[k]["indicadores"] == es[k]["indicadores"] and en[k]["guia"] == es[k]["guia"]
        for campo in ("nombre", "como_medir", "por_que", "efecto_espacio", "a_quien_avisar", "prevencion"):
            assert en[k][campo] and en[k][campo] != es[k][campo], (k, campo)


# ---------- API ----------
def test_idioma_por_cookie_o_url_y_espanol_por_defecto(cliente):
    assert cliente.get("/api/reglas").json()["indicadores"][0]["nombre"] == "Pulso"
    assert cliente.get("/api/reglas?lang=en").json()["indicadores"][0]["nombre"] == "Pulse"
    assert cliente.get("/api/reglas", cookies={"idioma": "en"}).json()["indicadores"][0]["unidad"] == "bpm"
    assert cliente.get("/api/fichas", cookies={"idioma": "en"}).json()["fichas"]["corazon"]["nombre"] == "Heart"
    assert cliente.get("/api/reglas?lang=xx").json()["indicadores"][0]["nombre"] == "Pulso"   # desconocido: español


def test_estado_y_orientacion_en_ingles(cliente):
    e = cliente.get("/api/estado/A1?lang=en").json()
    pulso = next(i for i in e["indicadores"] if i["indicador"] == "pulso")
    assert pulso["unidad"] == "bpm" and pulso["motivo"].isascii()
    radiacion = next(i for i in e["indicadores"] if i["indicador"] == "radiacion")
    assert radiacion["nombre"].startswith("Radiation")
    o = cliente.get("/api/orientacion?lang=en").json()["indicadores"]
    assert o["pulso"]["nombre"] == "Pulse" and o["pulso"]["por_que"] and o["pulso"]["cuando_avisar"]
    assert "official NASA protocol" in o["pulso"]["autor_contenido"]


def test_registro_responde_en_ingles(cliente):
    r = cliente.post("/api/mediciones?lang=en", json={"indicador": "glucosa", "valor": "150", "contexto": "despues_comida"})
    assert "fasting" in r.json()["resultado"]["mensaje"]
    error = cliente.post("/api/mediciones?lang=en", json={"indicador": "pulso", "valor": "abc"})
    assert error.status_code == 422 and "must be a number" in error.json()["detail"]


# ---------- ORI en inglés ----------
@pytest.mark.parametrize("pregunta", ["what should I do?", "help", "I feel sick", "we lost the signal, what now?"])
def test_ori_protocolo_de_alerta_en_ingles(pregunta):
    with idioma.usar("en"):
        r = rag.responder(pregunta, ROJO, [], conectado=False)
    assert r["modo"] == "protocolo"
    assert "Call someone now" in r["respuesta"] and "No link to Earth" in r["respuesta"]
    assert "148" in r["respuesta"] and "not alone" in r["respuesta"]


@pytest.mark.parametrize("pregunta,modo", [("My crewmate collapsed and is not responding", "emergencia_companero"),
                                           ("my chest hurts", "emergencia"), ("I can't breathe", "emergencia"),
                                           ("I fainted a moment ago", "emergencia")])
def test_ori_emergencias_en_ingles(pregunta, modo):
    with idioma.usar("en"):
        r = rag.responder(pregunta, None, [])
    assert r["modo"] == modo
    assert "Medical emergency" in r["respuesta"]


def test_tierra_sin_respuesta_no_es_un_companero():
    import emergencia
    assert not emergencia.es_companero("Earth is not responding")
    assert not emergencia.es_companero("no responde la Tierra")


def test_ori_intenciones_en_ingles():
    with idioma.usar("en"):
        assert rag.responder("hello", None, [])["respuesta"].startswith("Hi! I'm **ORI**")
        assert rag.responder("what can you do?", None, [])["modo"] == "conversacion"
        verde = {"indicadores": [{"indicador": "pulso", "valor": 70, "unidad": "bpm", "color": "verde"}]}
        assert "Good news" in rag.responder("how am I doing?", verde, [])["respuesta"]


def test_api_chat_en_ingles(cliente, monkeypatch):
    import ollama_cliente
    def sin_ia(*a, **k):
        raise ollama_cliente.OllamaNoDisponible("apagado")
    monkeypatch.setattr(ollama_cliente, "chatear", sin_ia)
    monkeypatch.setattr(ollama_cliente, "embeber", sin_ia)
    r = cliente.post("/api/chat", cookies={"idioma": "en"}, json={"pregunta": "I have a headache"}).json()
    assert any(f["guia"] == "Headache in space" for f in r["fuentes"])
    assert "What I suggest now" in r["respuesta"]


def test_espanol_sigue_igual():
    r = rag.responder("¿qué hago?", ROJO, [], conectado=False)
    assert "Llama a alguien ahora" in r["respuesta"] and "Sin enlace con la Tierra" in r["respuesta"]


# ---------- Interfaz ----------
def test_selectores_de_la_traduccion_existen_en_la_pagina():
    html = (RAIZ / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (RAIZ / "frontend" / "js" / "i18n.js").read_text(encoding="utf-8")
    ids = set(re.findall(r'\["#([A-Za-z][\w-]*)', js))
    assert ids, "no se encontraron selectores"
    faltan = [i for i in ids if f'id="{i}"' not in html]
    assert not faltan, faltan
