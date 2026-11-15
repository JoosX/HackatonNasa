"""Voz 100 % local: Whisper (voz a texto) y Piper (texto a voz). Nada sale de la nave.

Texto a voz (Piper): ORI habla con voz natural generada en el servidor, así suena igual en cualquier
equipo (no depende de las voces instaladas en cada navegador). Voces en data/voces/:
es_MX-ald-medium y en_US-lessac-medium (se descargan con scripts/descargar_voces.py).

Voz a texto 100 % local con Whisper (faster-whisper): la voz del astronauta nunca sale de la nave.

No se usa el reconocimiento de voz del navegador porque Chrome envía el audio a servidores externos
(necesita internet). Aquí el audio del micrófono llega al servidor local, ffmpeg lo convierte a 16 kHz
y Whisper lo transcribe en la misma computadora.

Requisitos (opcionales: si faltan, la app funciona igual y solo se oculta el micrófono):
    faster-whisper y numpy  (uv run --with faster-whisper --with numpy ...)
    ffmpeg en el sistema
    el modelo se descarga una vez (VOZ_MODELO, por defecto "small"); después funciona sin internet.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import io
import os
import shutil
import wave
from pathlib import Path
import subprocess
import threading
import time

MODELO = os.environ.get("VOZ_MODELO", "small")
MAX_BYTES = 8 * 1024 * 1024        # ~1 minuto de audio comprimido es mucho menos que esto
_modelo = None
_cerrojo = threading.Lock()


class VozNoDisponible(RuntimeError):
    pass


# ---------- Texto a voz con Piper ----------
CARPETA_VOCES = Path(__file__).resolve().parent.parent / "data" / "voces"
VOCES = {"es": "es_MX-ald-medium", "en": "en_US-lessac-medium"}
MAX_TEXTO = 1200
_voces: dict = {}


def tts_disponible() -> bool:
    """¿Puede ORI hablar desde el servidor? (librería Piper y al menos una voz descargada)."""
    try:
        import piper  # noqa: F401
    except ImportError:
        return False
    return any((CARPETA_VOCES / f"{v}.onnx").exists() for v in VOCES.values())


def _voz(idioma: str):
    nombre = VOCES.get(idioma, VOCES["es"])
    with _cerrojo:
        if nombre not in _voces:
            ruta = CARPETA_VOCES / f"{nombre}.onnx"
            if not ruta.exists():
                raise VozNoDisponible(f"Falta la voz {nombre}.")
            from piper import PiperVoice
            _voces[nombre] = PiperVoice.load(str(ruta))
    return _voces[nombre]


def hablar(texto: str, idioma: str = "es") -> bytes:
    """Texto -> audio WAV con la voz de ORI en el idioma pedido."""
    texto = (texto or "").strip()[:MAX_TEXTO]
    if not texto:
        raise ValueError("Texto vacío.")
    if not tts_disponible():
        raise VozNoDisponible("Piper no está instalado o faltan las voces.")
    voz = _voz(idioma)
    salida = io.BytesIO()
    with wave.open(salida, "wb") as w:
        if hasattr(voz, "synthesize_wav"):   # piper-tts >= 1.3
            voz.synthesize_wav(texto, w)
        else:                                 # versiones anteriores
            voz.synthesize(texto, w)
    return salida.getvalue()


def disponible() -> bool:
    """¿Se puede transcribir en esta computadora? (librería instalada y ffmpeg)."""
    if not shutil.which("ffmpeg"):
        return False
    try:
        import faster_whisper  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        return False
    return True


def _cargar():
    global _modelo
    with _cerrojo:
        if _modelo is None:
            if not disponible():
                raise VozNoDisponible("Falta faster-whisper, numpy o ffmpeg.")
            from faster_whisper import WhisperModel
            _modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")
    return _modelo


def precargar() -> None:
    """Carga los modelos en segundo plano al iniciar, así la primera transcripción y la primera frase son rápidas."""
    for lengua in VOCES:
        try:
            if tts_disponible():
                _voz(lengua)
        except Exception:   # noqa: BLE001 - falta una voz: se usará la del navegador
            pass
    if disponible():
        try:
            _cargar()
        except Exception:   # noqa: BLE001 - sin modelo descargado o sin memoria: el micrófono avisará al usarse
            pass


def _a_muestras(audio: bytes):
    """Cualquier formato que grabe el navegador (webm/ogg/mp4/wav) -> muestras float32 a 16 kHz mono."""
    import numpy as np
    proc = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", "pipe:0",
                           "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
                          input=audio, capture_output=True, timeout=60)
    if proc.returncode != 0 or not proc.stdout:
        raise ValueError("No se pudo leer el audio.")
    return np.frombuffer(proc.stdout, np.int16).astype(np.float32) / 32768


def transcribir(audio: bytes, idioma: str = "es") -> dict:
    """Devuelve {"texto", "idioma", "segundos"}. El idioma de la app guía a Whisper (es / en)."""
    if not audio:
        raise ValueError("Audio vacío.")
    if len(audio) > MAX_BYTES:
        raise ValueError("Audio demasiado largo.")
    inicio = time.time()
    muestras = _a_muestras(audio)
    if len(muestras) < 16000 * 0.3:
        raise ValueError("Audio demasiado corto.")
    segmentos, info = _cargar().transcribe(muestras, language=idioma if idioma in ("es", "en") else None,
                                           vad_filter=True, beam_size=1)
    texto = " ".join(s.text.strip() for s in segmentos).strip()
    return {"texto": texto, "idioma": info.language, "segundos": round(time.time() - inicio, 2)}
