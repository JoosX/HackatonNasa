"""API local del asistente de salud (FastAPI).

Sirve la interfaz, el registro e historial SQLite y el asistente local.
El pulso del estado se calcula desde los registros con reglas ilustrativas;
los demás indicadores personales aún son de demostración.

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

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import clima_espacial  # noqa: E402
import ollama_cliente  # noqa: E402
import rag  # noqa: E402
import mediciones  # noqa: E402
from guias import RAIZ  # noqa: E402

app = FastAPI(title="Asistente de salud local para astronautas")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _precalentar() -> None:
    """Carga los modelos de Ollama en segundo plano al arrancar (la primera respuesta no espera)."""
    import threading
    threading.Thread(target=ollama_cliente.precalentar, daemon=True).start()


def obtener_estado(astronauta_id: str) -> dict:
    """Pulso de SQLite; los otros indicadores personales siguen siendo demostración."""
    estado = json.loads((RAIZ / "data" / "estado_ejemplo.json").read_text(encoding="utf-8"))
    estado['astronauta_id'] = astronauta_id
    estado['origen'] = 'mixto'
    estado['notas'] = []
    estado['indicadores'] = [dict(i, origen='demo') for i in estado['indicadores'] if i['indicador'] != 'pulso']
    estado['indicadores'].insert(0, mediciones.estado_pulso(astronauta_id))
    estado["indicadores"].append(clima_espacial.indicador())
    return estado


class PreguntaChat(BaseModel):
    astronauta_id: str = "A1"
    pregunta: str
    estado: dict | None = None   # opcional: si viene, se usa en vez de obtener_estado()


@app.get("/api/estado/{astronauta_id}")
def estado(astronauta_id: str) -> dict:
    return obtener_estado(astronauta_id)


@app.post("/api/chat")
def chat(p: PreguntaChat) -> dict:
    inicio = time.time()
    estado = p.estado or obtener_estado(p.astronauta_id)
    if not estado.get('modo_demo'):
        # El cliente puede tener un dato antiguo. ORI usa el pulso actual de SQLite.
        estado = {**estado, 'indicadores': [i for i in estado.get('indicadores', []) if i.get('indicador') != 'pulso'] + [mediciones.estado_pulso(p.astronauta_id)]}
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


@app.post("/api/mediciones", status_code=201)
def registrar_medicion(m: mediciones.Medicion):
    try:
        return mediciones.guardar(m)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/historial/{astronauta_id}")
def historial_mediciones(astronauta_id: str, indicador: str | None = None,
                        limite: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
    if indicador is not None and indicador not in mediciones.CATALOGO:
        raise HTTPException(status_code=422, detail="Indicador desconocido.")
    return mediciones.historial(astronauta_id, indicador, limite, offset)


# El frontend se sirve desde el mismo servidor (va al final para no tapar /api).
from fastapi.staticfiles import StaticFiles  # noqa: E402

app.mount("/", StaticFiles(directory=RAIZ / "frontend", html=True), name="frontend")
