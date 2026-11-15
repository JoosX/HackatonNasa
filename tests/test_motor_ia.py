"""Motor de IA elegible: local (Ollama) o nube (Gemini). Sin red: se simulan las respuestas.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import ollama_cliente as oc  # noqa: E402

MENSAJES = [
    {"role": "system", "content": "Eres ORI."},
    {"role": "user", "content": "hola"},
    {"role": "assistant", "content": "¡Hola!"},
    {"role": "user", "content": "me duele la cabeza"},
]


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def limpiar(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    oc.fijar_motor(None)
    yield
    oc.fijar_motor(None)


def test_gemini_arma_el_pedido_y_lee_la_respuesta(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    visto = {}

    def falso_urlopen(pedido, timeout):
        visto["url"] = pedido.full_url
        visto["clave"] = pedido.headers.get("X-goog-api-key")
        visto["cuerpo"] = json.loads(pedido.data)
        return _Resp(json.dumps({"candidates": [{"content": {"parts": [{"text": "Te entiendo."}]}}]}).encode())

    monkeypatch.setattr(oc.urllib.request, "urlopen", falso_urlopen)
    oc.fijar_motor("nube")
    texto, motor = oc.chatear_con_motor(MENSAJES)
    assert (texto, motor) == ("Te entiendo.", "nube")
    assert visto["url"].endswith(f"/{oc.GEMINI_MODELO}:generateContent")
    assert visto["clave"] == "clave-de-prueba"
    assert visto["cuerpo"]["systemInstruction"]["parts"][0]["text"] == "Eres ORI."
    assert [c["role"] for c in visto["cuerpo"]["contents"]] == ["user", "model", "user"]


def test_nube_sin_clave_cae_al_respaldo():
    oc.fijar_motor("nube")
    with pytest.raises(oc.OllamaNoDisponible):
        oc.chatear_con_motor(MENSAJES)


def test_error_de_gemini_cae_al_respaldo(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")

    def falla(pedido, timeout):
        raise oc.urllib.error.HTTPError(pedido.full_url, 429, "límite", {}, None)

    monkeypatch.setattr(oc.urllib.request, "urlopen", falla)
    oc.fijar_motor("nube")
    with pytest.raises(oc.OllamaNoDisponible):
        oc.chatear_con_motor(MENSAJES)


def test_local_elegido_usa_ollama(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(oc, "chatear", lambda m, t=180: "desde ollama")
    oc.fijar_motor("local")
    assert oc.chatear_con_motor(MENSAJES) == ("desde ollama", "local")


def test_auto_prefiere_local_y_usa_nube_si_no_hay_ollama(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(oc, "disponible", lambda: True)
    assert oc.motor_a_usar() == "local"
    monkeypatch.setattr(oc, "disponible", lambda: False)
    assert oc.motor_a_usar() == "nube"


def test_motor_desconocido_se_ignora():
    oc.fijar_motor("otro")
    assert oc._motor.get() is None
