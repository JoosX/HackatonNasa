"""
Backend del asistente de salud para astronautas (NASA Space Apps 2026).
BLOQUE 1: API con datos FALSOS. La forma del JSON es la definitiva;
en los siguientes bloques solo se reemplaza el origen de los datos.

Ejecutar (desde la carpeta backend/, con el venv activo):
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
Docs automaticas: http://localhost:8000/docs
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import reglas

app = FastAPI(title="Asistente de salud local para astronautas", version="0.2-sqlite")


@app.on_event("startup")
def _arranque():
    db.init_db()


MINUTOS_SALTO = 120  # un "salto brusco" solo se compara contra una medicion de las ultimas 2 h

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- Modelos
class MedicionIn(BaseModel):
    astronauta_id: int = 1
    indicador: str  # presion, pulso, glucosa, temperatura, oxigeno, sueno, animo, estres
    valor: float
    origen: str = "manual"  # manual | sensor
    medido_en: Optional[str] = None  # ISO 8601; si no viene, se usa la hora actual


class ChatIn(BaseModel):
    astronauta_id: int = 1
    pregunta: str


# ---------------------------------------------------------------- Datos falsos
def ahora() -> datetime:
    return datetime.now().replace(microsecond=0)


def hace(minutos: int) -> str:
    return (ahora() - timedelta(minutes=minutos)).isoformat()


INDICADORES_FALSOS = [
    {"indicador": "pulso", "parte_cuerpo": "corazon", "valor": 88, "unidad": "lpm",
     "color": "verde", "medido_en": hace(5), "antiguedad_min": 5,
     "vencido": False, "sospechoso": False, "accion": None, "tendencia": "estable"},
    {"indicador": "presion", "parte_cuerpo": "corazon", "valor": 128, "unidad": "mmHg",
     "color": "amarillo", "medido_en": hace(30), "antiguedad_min": 30,
     "vencido": False, "sospechoso": False,
     "accion": "Repite en reposo en 15 min", "tendencia": "subiendo"},
    {"indicador": "glucosa", "parte_cuerpo": "sangre", "valor": 95, "unidad": "mg/dL",
     "color": "verde", "medido_en": hace(60), "antiguedad_min": 60,
     "vencido": False, "sospechoso": False, "accion": None, "tendencia": "estable"},
    {"indicador": "temperatura", "parte_cuerpo": "piel", "valor": 36.7, "unidad": "C",
     "color": "verde", "medido_en": hace(45), "antiguedad_min": 45,
     "vencido": False, "sospechoso": False, "accion": None, "tendencia": "estable"},
    {"indicador": "oxigeno", "parte_cuerpo": "pulmones", "valor": 97, "unidad": "%",
     "color": "verde", "medido_en": hace(10), "antiguedad_min": 10,
     "vencido": False, "sospechoso": False, "accion": None, "tendencia": "estable"},
    {"indicador": "sueno", "parte_cuerpo": "cerebro", "valor": 4.5, "unidad": "h",
     "color": "rojo", "medido_en": hace(400), "antiguedad_min": 400,
     "vencido": True, "sospechoso": False,
     "accion": "Avisa a la tripulacion", "tendencia": "bajando"},
    {"indicador": "animo", "parte_cuerpo": "cerebro", "valor": 3, "unidad": "1-5",
     "color": "amarillo", "medido_en": hace(120), "antiguedad_min": 120,
     "vencido": False, "sospechoso": False,
     "accion": "Habla con alguien de la tripulacion", "tendencia": "bajando"},
    {"indicador": "estres", "parte_cuerpo": "cerebro", "valor": 250, "unidad": "1-10",
     "color": "gris", "medido_en": hace(15), "antiguedad_min": 15,
     "vencido": False, "sospechoso": True,
     "accion": "Dato sospechoso: mide de nuevo", "tendencia": "desconocida"},
]

ALERTAS_FALSAS = [
    {"id": 1, "astronauta_id": 1, "indicador": "sueno", "nivel": "rojo",
     "mensaje": "4 noches con poco sueno", "accion": "Avisa a la tripulacion",
     "creada_en": hace(30), "activa": True},
    {"id": 2, "astronauta_id": 1, "indicador": "presion", "nivel": "amarillo",
     "mensaje": "Presion sistolica por encima del rango verde",
     "accion": "Repite en reposo en 15 min", "creada_en": hace(30), "activa": True},
]

FICHAS_FALSAS = [
    {
        "indicador": "pulso",
        "parte_cuerpo": "corazon",
        "titulo": "Pulso",
        "como_medir": "En reposo, con dos dedos en la muneca durante 30 segundos, o con el sensor.",
        "por_que_importa": "Muestra como trabaja el corazon bajo la carga de la mision.",
        "efecto_espacio": "En microgravedad los fluidos se desplazan hacia la cabeza y el corazon se adapta.",
        "a_quien_avisar": "Medico de la tripulacion si pasa de 120 lpm en reposo.",
        "prevencion": "Ejercicio diario, hidratacion y buen descanso.",
        "fuente": "NASA HRP (ejemplo)",
    },
    {
        "indicador": "sueno",
        "parte_cuerpo": "cerebro",
        "titulo": "Sueno",
        "como_medir": "Registrar las horas dormidas cada manana.",
        "por_que_importa": "El sueno corto afecta la atencion y el animo.",
        "efecto_espacio": "El ciclo dia/noche alterado en orbita reduce la calidad del sueno.",
        "a_quien_avisar": "Tripulacion si hay 3 o mas noches seguidas con menos de 6 h.",
        "prevencion": "Horario fijo, luz controlada, evitar pantallas antes de dormir.",
        "fuente": "NASA HRP (ejemplo)",
    },
]

NASA_OSD575_FALSO = {
    "estudio": "OSD-575",
    "mision": "Inspiration4 (ejemplo ilustrativo)",
    "descripcion": "Datos de ejemplo para mostrar 'tu normal'. Seran reemplazados por el JSON real de P6.",
    "series": [
        {"indicador": "pulso", "unidad": "lpm",
         "puntos": [{"dia": 1, "valor": 70}, {"dia": 2, "valor": 72},
                    {"dia": 3, "valor": 69}, {"dia": 4, "valor": 74}]},
    ],
}

# Estado simulado de la sincronizacion
SYNC = {"conectado": False, "retraso_min": 14, "pendientes": 3, "ultima_sync": hace(180)}


# ---------------------------------------------------------------- Endpoints
@app.post("/api/mediciones")
def crear_medicion(m: MedicionIn):
    if m.indicador not in db.PARTE_CUERPO:
        raise HTTPException(status_code=422, detail=f"Indicador desconocido: {m.indicador}")

    medido_en = m.medido_en or ahora().isoformat()

    # Valor anterior reciente (para detectar saltos bruscos)
    anterior = None
    previo = db.ultimo_valor(m.astronauta_id, m.indicador)
    if previo:
        minutos = (datetime.fromisoformat(medido_en) - datetime.fromisoformat(previo["medido_en"])).total_seconds() / 60
        if 0 <= minutos <= MINUTOS_SALTO:
            anterior = previo["valor"]

    ev = reglas.evaluar(m.indicador, m.valor, anterior)
    guardado = db.guardar_medicion(
        m.astronauta_id, m.indicador, m.valor, m.origen, medido_en,
        color=ev["color"], sospechoso=ev["sospechoso"],
    )

    # Alertas: amarillo/rojo crean una; verde cierra las anteriores; sospechoso no toca nada
    alerta = None
    if not ev["sospechoso"]:
        db.cerrar_alertas(m.astronauta_id, m.indicador)
        if ev["color"] in ("amarillo", "rojo"):
            aid = db.crear_alerta(m.astronauta_id, m.indicador, ev["color"],
                                  ev["mensaje"], ev["accion"], guardado["id"])
            alerta = {"id": aid, "nivel": ev["color"], "mensaje": ev["mensaje"]}
    ev["alerta"] = alerta

    return {
        "ok": True,
        "id": guardado["id"],
        "astronauta_id": m.astronauta_id,
        "indicador": m.indicador,
        "valor": m.valor,
        "origen": m.origen,
        "medido_en": guardado["medido_en"],
        "color": ev["color"],
        "alerta": ev["alerta"],
        "accion": ev["accion"],
        "sospechoso": ev["sospechoso"],
    }


@app.get("/api/estado/{astronauta_id}")
def estado(astronauta_id: int):
    # Sin datos reales todavia: se devuelve el ejemplo falso para no frenar al front
    if db.total_mediciones(astronauta_id) == 0:
        return {
            "astronauta_id": astronauta_id,
            "generado_en": ahora().isoformat(),
            "color_global": "rojo",
            "datos_falsos": True,
            "indicadores": INDICADORES_FALSOS,
        }

    indicadores = []
    for f in db.ultimas_por_indicador(astronauta_id):
        antig = int((ahora() - datetime.fromisoformat(f["medido_en"])).total_seconds() // 60)
        # Se recalcula con las reglas ACTUALES: si cambia reglas.json, cambian los colores
        ev = reglas.evaluar(f["indicador"], f["valor"])
        sospechoso = bool(f["sospechoso"]) or ev["sospechoso"]
        esta_vencido = reglas.vencido(f["indicador"], antig)
        accion = "Dato sospechoso: mide de nuevo" if sospechoso else ev["accion"]
        if esta_vencido and not sospechoso:
            accion = "Dato vencido: mide de nuevo"
        indicadores.append({
            "indicador": f["indicador"],
            "parte_cuerpo": db.PARTE_CUERPO.get(f["indicador"]),
            "valor": f["valor"],
            "unidad": f["unidad"],
            "color": "gris" if sospechoso else ev["color"],
            "medido_en": f["medido_en"],
            "antiguedad_min": antig,
            "vencido": esta_vencido,
            "sospechoso": sospechoso,
            "accion": accion,
            "tendencia": "desconocida",  # siguiente paso: tendencias.py
        })

    orden = {"rojo": 3, "amarillo": 2, "verde": 1, "gris": 0}
    color_global = max((i["color"] for i in indicadores), key=lambda c: orden.get(c, 0))
    return {
        "astronauta_id": astronauta_id,
        "generado_en": ahora().isoformat(),
        "color_global": color_global,
        "datos_falsos": False,
        "indicadores": indicadores,
    }


@app.get("/api/historial/{astronauta_id}")
def historial(astronauta_id: int, indicador: str = "pulso", dias: int = 7):
    desde = (ahora() - timedelta(days=dias)).isoformat()
    reales = db.historial(astronauta_id, indicador, desde)
    if reales:
        return {
            "astronauta_id": astronauta_id,
            "indicador": indicador,
            "linea_base": None,  # Bloque 3: tendencias.py
            "direccion": "desconocida",
            "datos_falsos": False,
            "puntos": [{"medido_en": r["medido_en"], "valor": r["valor"],
                        "color": r["color"], "sospechoso": bool(r["sospechoso"])}
                       for r in reales],
        }

    base = {"pulso": 72, "presion": 118, "glucosa": 92, "temperatura": 36.6,
            "oxigeno": 97, "sueno": 7, "animo": 4, "estres": 3}.get(indicador, 50)
    puntos = []
    for i in range(dias * 2):
        t = ahora() - timedelta(hours=12 * (dias * 2 - i))
        puntos.append({"medido_en": t.isoformat(), "valor": round(base + (i % 5) - 2, 1)})
    return {
        "astronauta_id": astronauta_id,
        "indicador": indicador,
        "linea_base": base,
        "direccion": "estable",
        "puntos": puntos,
    }


@app.get("/api/alertas/{astronauta_id}")
def alertas(astronauta_id: int):
    if db.total_mediciones(astronauta_id) == 0:
        return {"astronauta_id": astronauta_id, "datos_falsos": True,
                "alertas": [a for a in ALERTAS_FALSAS if a["astronauta_id"] == astronauta_id]}
    return {"astronauta_id": astronauta_id, "datos_falsos": False,
            "alertas": db.alertas_activas(astronauta_id)}


@app.get("/api/fichas")
def fichas():
    return {"fichas": FICHAS_FALSAS}


@app.post("/api/chat")
def chat(c: ChatIn):
    # Falso: P5 lo reemplazara con rag.py (Ollama + RAG)
    return {
        "respuesta": "Respuesta de ejemplo. Duerme y bebe agua; si el dolor sigue, avisa a la tripulacion.",
        "fuentes": [{"guia": "dolor_de_cabeza.md", "version": "v1", "url": "https://www.nasa.gov/hrp"}],
        "usa_estado": True,
        "tiempo_ms": 1200,
    }


@app.get("/api/sync")
def sync_estado():
    return SYNC


@app.post("/api/sync/simular")
def sync_simular(conectado: Optional[bool] = None):
    SYNC["conectado"] = (not SYNC["conectado"]) if conectado is None else conectado
    if SYNC["conectado"]:
        SYNC["pendientes"] = 0
        SYNC["ultima_sync"] = ahora().isoformat()
    return SYNC


@app.get("/api/nasa/osd575")
def nasa_osd575():
    return NASA_OSD575_FALSO


# ---------------------------------------------------------------- Frontend
# Va AL FINAL para no tapar las rutas /api
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
