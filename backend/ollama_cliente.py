"""Cliente mínimo para la API local de Ollama (sin librerías externas).

Ollama corre en la misma computadora (http://localhost:11434), así que
nada de esto necesita internet.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import json
import os
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO_CHAT = os.environ.get("MODELO_CHAT", "gemma3:4b")
MODELO_EMBED = os.environ.get("MODELO_EMBED", "nomic-embed-text")
# Mantener los modelos cargados en memoria (Ollama los descarga a los 5 min; la primera respuesta sería lenta).
MANTENER = os.environ.get("OLLAMA_KEEP_ALIVE", "60m")


class OllamaNoDisponible(Exception):
    """Ollama no está corriendo o el modelo no está descargado."""


def _post(ruta: str, cuerpo: dict, timeout: float) -> dict:
    datos = json.dumps(cuerpo).encode("utf-8")
    pedido = urllib.request.Request(
        OLLAMA_URL + ruta, data=datos, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise OllamaNoDisponible(str(e)) from e


def disponible() -> bool:
    """True si Ollama responde."""
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def embeber(textos: list[str], timeout: float = 120) -> list[list[float]]:
    """Convierte textos en vectores con el modelo de embeddings."""
    r = _post("/api/embed", {"model": MODELO_EMBED, "input": textos, "keep_alive": MANTENER}, timeout)
    if "embeddings" not in r:
        raise OllamaNoDisponible(r.get("error", "respuesta sin embeddings"))
    return r["embeddings"]


def chatear(mensajes: list[dict], timeout: float = 180) -> str:
    """Envía la conversación al modelo de chat y devuelve el texto de respuesta."""
    r = _post(
        "/api/chat",
        {
            "model": MODELO_CHAT,
            "messages": mensajes,
            "stream": False,
            "keep_alive": MANTENER,
            "options": {"temperature": 0.2},
        },
        timeout,
    )
    if "message" not in r:
        raise OllamaNoDisponible(r.get("error", "respuesta sin mensaje"))
    return r["message"]["content"].strip()


def precalentar() -> None:
    """Carga los modelos en memoria al iniciar el servidor para que la primera pregunta sea rápida."""
    try:
        embeber(["precalentar"])
        chatear([{"role": "user", "content": "Responde solo: listo"}], timeout=120)
    except OllamaNoDisponible:
        pass
