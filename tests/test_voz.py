"""Voz a texto local (Whisper). Escrito con asistencia de IA (Claude); revisado por el equipo.

La transcripción real necesita faster-whisper y numpy; si no están instalados, esas pruebas se saltan
y se comprueba que la app responde bien sin voz (el micrófono se oculta).
"""
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

import voz
from backend.main import app


@pytest.fixture
def cliente():
    return TestClient(app)


def test_estado_de_la_voz(cliente):
    r = cliente.get("/api/voz/estado").json()
    assert set(r) == {"disponible", "modelo", "habla"} and isinstance(r["disponible"], bool)


def test_sin_whisper_responde_503_y_no_rompe(cliente, monkeypatch):
    def no_hay(*a, **k):
        raise voz.VozNoDisponible("falta")
    monkeypatch.setattr(voz, "transcribir", no_hay)
    r = cliente.post("/api/voz?lang=en", content=b"x" * 2000, headers={"Content-Type": "audio/webm"})
    assert r.status_code == 503 and "not installed" in r.json()["detail"]
    r = cliente.post("/api/voz", content=b"x" * 2000, headers={"Content-Type": "audio/webm"})
    assert "no está instalada" in r.json()["detail"]


def test_audio_vacio_o_invalido_da_422(cliente, monkeypatch):
    monkeypatch.setattr(voz, "_cargar", lambda: pytest.fail("no debe cargar el modelo con audio inválido"))
    assert cliente.post("/api/voz", content=b"", headers={"Content-Type": "audio/webm"}).status_code == 422
    if voz.disponible():
        assert cliente.post("/api/voz", content=b"no es audio", headers={"Content-Type": "audio/webm"}).status_code == 422


@pytest.mark.skipif(not voz.disponible() or not shutil.which("ffmpeg"), reason="sin faster-whisper o ffmpeg")
def test_silencio_no_inventa_texto():
    # medio segundo de silencio en webm/opus, generado con ffmpeg
    audio = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "1",
                            "-c:a", "libopus", "-f", "webm", "pipe:1"], capture_output=True).stdout
    r = voz.transcribir(audio, "es")
    assert r["texto"] == ""


# ---------- Texto a voz (Piper): ORI habla con voz natural generada en el servidor ----------
def test_estado_informa_si_ori_puede_hablar(cliente):
    assert isinstance(cliente.get("/api/voz/estado").json()["habla"], bool)


def test_sin_piper_hablar_responde_503(cliente, monkeypatch):
    monkeypatch.setattr(voz, "tts_disponible", lambda: False)
    r = cliente.post("/api/voz/hablar?lang=en", json={"texto": "Hello"})
    assert r.status_code == 503 and "not installed" in r.json()["detail"]


def test_texto_vacio_no_se_sintetiza(cliente, monkeypatch):
    monkeypatch.setattr(voz, "_voz", lambda *_: pytest.fail("no debe cargar la voz con texto vacío"))
    assert cliente.post("/api/voz/hablar", json={"texto": "   "}).status_code in (422, 503)


@pytest.mark.skipif(not voz.tts_disponible(), reason="sin piper-tts o sin voces descargadas")
@pytest.mark.parametrize("lang,frase,palabra", [("es", "Avisa ahora a la tripulación.", "tripulaci"),
                                                ("en", "Alert the crew now.", "crew")])
def test_ori_habla_y_whisper_lo_entiende(cliente, lang, frase, palabra):
    r = cliente.post(f"/api/voz/hablar?lang={lang}", json={"texto": frase})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    assert r.content[:4] == b"RIFF" and len(r.content) > 20000
    if voz.disponible():   # ida y vuelta: lo que dice ORI, Whisper lo transcribe
        assert palabra in voz.transcribir(r.content, lang)["texto"].lower()
