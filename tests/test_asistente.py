"""Pruebas del asistente RAG y de la API.
Las pruebas con el modelo se saltan solas si Ollama no está corriendo.
Escrito con asistencia de IA (Claude); revisado por el equipo."""

import pytest

import ollama_cliente
import rag

ESTADO_ROJO = {"indicadores": [{"indicador": "pulso", "valor": 150, "unidad": "lpm", "color": "rojo", "antiguedad_min": 1}]}
ESTADO_VERDE = {"indicadores": [{"indicador": "pulso", "valor": 70, "unidad": "lpm", "color": "verde", "antiguedad_min": 1}]}
hay_ollama = pytest.mark.skipif(not ollama_cliente.disponible(), reason="Ollama no está corriendo")


@pytest.fixture
def sin_ollama(monkeypatch):
    """Simula que Ollama está apagado: la app debe seguir respondiendo con las guías."""
    def falla(*_a, **_k):
        raise ollama_cliente.OllamaNoDisponible("apagado (prueba)")
    monkeypatch.setattr(ollama_cliente, "embeber", falla)
    monkeypatch.setattr(ollama_cliente, "chatear", falla)


@pytest.mark.parametrize("pregunta", ["¿Cuál es la capital de Francia?", "Me torcí el tobillo", "receta de pizza"])
def test_fuera_de_las_guias_no_inventa(sin_ollama, pregunta):
    r = rag.responder(pregunta, ESTADO_VERDE)
    assert r["modo"] == "sin_informacion"
    assert r["fuentes"] == []
    assert "No tengo información" in r["respuesta"]


@pytest.mark.parametrize("pregunta,guia", [
    ("Me duele la cabeza", "Dolor de cabeza en el espacio"),
    ("No puedo dormir bien", "Sueño y fatiga en misiones espaciales"),
    ("Mi oxígeno salió bajo", "Oxígeno en sangre y aire de la nave"),
    ("Tengo una erupción en la piel", "Temperatura corporal y piel"),
    ("Hay aviso de tormenta solar", "Radiación espacial"),
])
def test_encuentra_la_guia_correcta_sin_ia(sin_ollama, pregunta, guia):
    r = rag.responder(pregunta, ESTADO_VERDE)
    assert r["modo"] == "respaldo_sin_ia"
    assert guia in [f["guia"] for f in r["fuentes"]]


def test_alerta_roja_la_deciden_las_reglas(sin_ollama):
    """Con un indicador en rojo, el aviso fijo aparece siempre, haya o no IA."""
    r = rag.responder("Siento el corazón rápido", ESTADO_ROJO)
    assert r["alerta_roja"] is True
    assert r["respuesta"].startswith(rag.AVISO_ROJO)
    r2 = rag.responder("¿Cuál es la capital de Francia?", ESTADO_ROJO)
    assert r2["respuesta"].startswith(rag.AVISO_ROJO)


def test_resumen_de_estado():
    texto, rojo = rag.resumir_estado(ESTADO_ROJO)
    assert "pulso" in texto and "ROJO" in texto and rojo
    assert rag.resumir_estado(None) == ("Sin datos recientes del astronauta.", False)


@hay_ollama
def test_ia_local_responde_con_fuente():
    r = rag.responder("Me duele la cabeza y dormí 4 horas, ¿qué hago?", ESTADO_VERDE)
    assert r["modo"] == "ia_local"
    assert r["fuentes"]
    assert len(r["respuesta"]) > 40


@hay_ollama
def test_ia_local_no_inventa_fuera_de_tema():
    r = rag.responder("¿Cuál es la capital de Francia?", ESTADO_VERDE)
    assert r["modo"] == "sin_informacion"


# ---------- API ----------

@pytest.fixture(scope="module")
def cliente():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


def test_api_fichas_reglas_y_nasa(cliente):
    assert len(cliente.get("/api/fichas").json()["fichas"]) == 7
    assert len(cliente.get("/api/reglas").json()["indicadores"]) >= 10
    assert "C001" in cliente.get("/api/nasa/osd575").json()["tripulantes"]


def test_api_chat_usa_el_estado_enviado(cliente, sin_ollama):
    r = cliente.post("/api/chat", json={"pregunta": "Siento el corazón rápido", "estado": ESTADO_ROJO}).json()
    for clave in ("respuesta", "fuentes", "datos_usados", "modo", "alerta_roja", "segundos"):
        assert clave in r
    assert r["alerta_roja"] is True


def test_api_sirve_el_frontend(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "Copiloto de salud" in r.text
    assert cliente.get("/modelos/cuerpo.glb").status_code == 200
