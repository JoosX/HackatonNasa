"""Cliente mínimo para los motores de IA de ORI (sin librerías externas).

- "local": Ollama en la misma computadora (http://localhost:11434), sin internet. Es el modo de la nave.
  OLLAMA_URL también puede apuntar a otra computadora (p. ej., la tuya, a través de un túnel).
- "nube": Gemini (Google AI Studio) por internet, solo para la demo en línea. Se activa con GEMINI_API_KEY.

La búsqueda por vectores usa siempre Ollama; si no está, ORI busca en las guías por palabras.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import contextvars
import json
import os
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELO_CHAT = os.environ.get("MODELO_CHAT", "gemma3:4b")
MODELO_EMBED = os.environ.get("MODELO_EMBED", "nomic-embed-text")
# Mantener los modelos cargados en memoria (Ollama los descarga a los 5 min; la primera respuesta sería lenta).
MANTENER = os.environ.get("OLLAMA_KEEP_ALIVE", "60m")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELO = os.environ.get("GEMINI_MODELO", "gemini-flash-latest")
# Motor por defecto: "auto" usa la IA local si responde y, si no, Gemini (si hay clave).
MOTOR_POR_DEFECTO = os.environ.get("MOTOR_IA", "auto")
MOTORES = ("auto", "local", "nube")

# Motor pedido en esta solicitud (lo fija la API con lo que elige el usuario en la app).
_motor: contextvars.ContextVar[str | None] = contextvars.ContextVar("motor_ia", default=None)


def _clave_gemini() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def fijar_motor(motor: str | None) -> None:
    _motor.set(motor if motor in MOTORES else None)


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


def nube_disponible() -> bool:
    """True si el servidor tiene una clave de Gemini configurada."""
    return bool(_clave_gemini())


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


def _chatear_gemini(mensajes: list[dict], timeout: float) -> str:
    """Misma conversación, enviada a Gemini (el mensaje "system" va como instrucción del sistema)."""
    clave = _clave_gemini()
    if not clave:
        raise OllamaNoDisponible("falta GEMINI_API_KEY")
    sistema = "\n\n".join(m["content"] for m in mensajes if m["role"] == "system")
    contenidos = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in mensajes if m["role"] != "system"
    ]
    cuerpo = {"contents": contenidos, "generationConfig": {"temperature": 0.2}}
    if sistema:
        cuerpo["systemInstruction"] = {"parts": [{"text": sistema}]}
    pedido = urllib.request.Request(
        f"{GEMINI_URL}/{GEMINI_MODELO}:generateContent",
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": clave},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resp:
            r = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise OllamaNoDisponible(f"Gemini respondió {e.code}") from e
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise OllamaNoDisponible(str(e)) from e
    try:
        partes = r["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError) as e:
        raise OllamaNoDisponible("respuesta de Gemini sin texto") from e
    texto = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip()
    if not texto:
        raise OllamaNoDisponible("respuesta de Gemini vacía")
    return texto


def motor_a_usar() -> str:
    """'local' o 'nube', según lo pedido y lo que esté disponible."""
    pedido = _motor.get() or MOTOR_POR_DEFECTO
    if pedido == "nube":
        return "nube"
    if pedido == "local":
        return "local"
    return "local" if disponible() or not nube_disponible() else "nube"


def chatear_con_motor(mensajes: list[dict], timeout: float = 180) -> tuple[str, str]:
    """Responde con el motor elegido. Devuelve (texto, motor usado)."""
    motor = motor_a_usar()
    if motor == "nube":
        return _chatear_gemini(mensajes, min(timeout, 60)), "nube"
    return chatear(mensajes, timeout), "local"


def chatear(mensajes: list[dict], timeout: float = 180) -> str:
    """Envía la conversación al modelo de chat local (Ollama) y devuelve el texto de respuesta."""
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
