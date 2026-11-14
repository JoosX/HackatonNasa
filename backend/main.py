"""API local del asistente de salud (FastAPI).

Por ahora contiene la parte de IA (P5). P4 agrega aquí sus endpoints
(mediciones, estado, historial, alertas, fichas, sync) y reemplaza
obtener_estado() por el estado real calculado con las reglas.

Ejecutar desde la carpeta asistente-salud:
    uvicorn backend.main:app --reload --port 8000
Documentación automática: http://localhost:8000/docs

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import ollama_cliente  # noqa: E402
import rag  # noqa: E402
from guias import RAIZ  # noqa: E402

app = FastAPI(title="Asistente de salud local para astronautas")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def obtener_estado(astronauta_id: str) -> dict:
    """TODO (P4): devolver el estado real (mismo formato que estado_ejemplo.json)."""
    return json.loads((RAIZ / "data" / "estado_ejemplo.json").read_text(encoding="utf-8"))


class PreguntaChat(BaseModel):
    astronauta_id: str = "A1"
    pregunta: str
    estado: dict | None = None   # opcional: si viene, se usa en vez de obtener_estado()


@app.post("/api/chat")
def chat(p: PreguntaChat) -> dict:
    inicio = time.time()
    estado = p.estado or obtener_estado(p.astronauta_id)
    resultado = rag.responder(p.pregunta, estado)
    resultado["segundos"] = round(time.time() - inicio, 2)
    return resultado


@app.get("/api/ia/estado")
def estado_ia() -> dict:
    """Para el indicador del front: ¿la IA local está lista?"""
    return {
        "ollama": ollama_cliente.disponible(),
        "modelo_chat": ollama_cliente.MODELO_CHAT,
        "modelo_embeddings": ollama_cliente.MODELO_EMBED,
        "indice_guias": rag.INDICE.exists(),
        "fragmentos": len(rag._fragmentos()),
    }


@app.post("/api/ia/recargar")
def recargar() -> dict:
    """Llamar después de volver a indexar las guías."""
    rag.recargar()
    return {"ok": True, "fragmentos": len(rag._fragmentos())}


def _json(nombre: str) -> dict:
    return json.loads((RAIZ / "data" / nombre).read_text(encoding="utf-8"))


@app.get("/api/fichas")
def fichas() -> dict:
    """Fichas por órgano con las 5 preguntas del reto (P6)."""
    return _json("fichas.json")


@app.get("/api/reglas")
def reglas() -> dict:
    """Rangos del semáforo (P6). El motor de reglas real es de P4."""
    return _json("reglas.json")


@app.get("/api/nasa/osd575")
def osd575() -> dict:
    """Panel metabólico real de la tripulación de Inspiration4 (NASA OSDR OSD-575)."""
    return _json("nasa_osd575.json")


# El frontend se sirve desde el mismo servidor (va al final para no tapar /api).
from fastapi.staticfiles import StaticFiles  # noqa: E402

app.mount("/", StaticFiles(directory=RAIZ / "frontend", html=True), name="frontend")
