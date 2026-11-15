"""API local del asistente de salud (FastAPI).

Mediciones en SQLite (db.py), estado calculado con reglas.json (motor.py),
asistente ORI con RAG local (rag.py) y clima espacial de NASA DONKI (clima_espacial.py).

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

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import clima_espacial  # noqa: E402
import db  # noqa: E402
import motor  # noqa: E402
import ollama_cliente  # noqa: E402
import rag  # noqa: E402
from guias import RAIZ  # noqa: E402

app = FastAPI(title="Asistente de salud local para astronautas")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _iniciar() -> None:
    """Crea la base de datos (con historial de demostración si está vacía) y precarga los modelos de IA."""
    db.sembrar("A1", valor_num=motor.valor_num)
    import threading
    threading.Thread(target=ollama_cliente.precalentar, daemon=True).start()


def obtener_estado(astronauta_id: str) -> dict:
    """Estado real: últimas mediciones de SQLite evaluadas con reglas.json + radiación de NASA DONKI."""
    db.sembrar(astronauta_id, valor_num=motor.valor_num)   # no hace nada si ya hay datos
    estado = motor.evaluar(astronauta_id)
    estado["indicadores"].append(clima_espacial.indicador())
    return estado


class PreguntaChat(BaseModel):
    astronauta_id: str = "A1"
    pregunta: str
    estado: dict | None = None   # opcional: si viene, se usa en vez de obtener_estado()


class Medicion(BaseModel):
    astronauta_id: str = "A1"
    indicador: str
    valor: str
    origen: str = "manual"   # manual | sensor


@app.get("/api/estado/{astronauta_id}")
def estado(astronauta_id: str) -> dict:
    """Estado actual del astronauta calculado desde la base de datos."""
    return obtener_estado(astronauta_id)


@app.post("/api/mediciones")
def nueva_medicion(m: Medicion) -> dict:
    """Guarda una medición, la clasifica con las reglas y devuelve el estado actualizado."""
    try:
        resultado = motor.registrar(m.astronauta_id, m.indicador, m.valor, m.origen)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"resultado": resultado, "estado": obtener_estado(m.astronauta_id)}


@app.get("/api/historial/{astronauta_id}")
def historial(astronauta_id: str, dias: int = 7) -> dict:
    """Series de los últimos días de cada indicador (para las gráficas)."""
    return motor.historial(astronauta_id, dias)


@app.get("/api/alertas/{astronauta_id}")
def alertas(astronauta_id: str) -> list[dict]:
    return db.alertas(astronauta_id)


@app.post("/api/demo/reiniciar")
def reiniciar_demo(astronauta_id: str = "A1") -> dict:
    """Vuelve al historial de demostración (para repetir la demo desde cero)."""
    db.sembrar(astronauta_id, forzar=True, valor_num=motor.valor_num)
    return obtener_estado(astronauta_id)


@app.post("/api/chat")
def chat(p: PreguntaChat) -> dict:
    inicio = time.time()
    estado = p.estado or obtener_estado(p.astronauta_id)
    turnos = db.ultimos_turnos(p.astronauta_id, 4)          # memoria corta de la conversación
    resultado = rag.responder(p.pregunta, estado, turnos)
    db.guardar_turno(p.astronauta_id, "astronauta", p.pregunta)
    db.guardar_turno(p.astronauta_id, "ori", resultado["respuesta"][:600])
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


@app.get("/api/clima-espacial")
def clima() -> dict:
    """Clima espacial con datos reales de NASA DONKI (último archivo sincronizado) y su nivel de alerta."""
    return clima_espacial.evaluar(clima_espacial.cargar())


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
