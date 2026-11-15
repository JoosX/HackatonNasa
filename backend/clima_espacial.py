"""Clima espacial (NASA DONKI) -> indicador de radiación con semáforo.

Reglas ILUSTRATIVAS del prototipo (deben validarlas especialistas de clima espacial de la misión):
  ROJO      evento de partículas solares (SEP) en las últimas 72 h  -> ir al área protegida.
  AMARILLO  llamarada clase X en las últimas 72 h, llamarada M en las últimas 24 h,
            o tormenta geomagnética Kp >= 7 en las últimas 72 h      -> vigilar dosímetro y avisos.
  VERDE     sin eventos relevantes recientes.
Si los datos tienen más de 48 h sin sincronizar, se avisa de su antigüedad (sin señal con la Tierra).

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import datetime as dt
import json
from pathlib import Path

from idioma import t as T

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "data" / "nasa_donki.json"



def _fecha(t: str | None) -> dt.datetime | None:
    if not t:
        return None
    try:
        return dt.datetime.strptime(t[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def _hace(delta: dt.timedelta) -> str:
    h = int(delta.total_seconds() // 3600)
    cuanto = f"{h} h" if h < 48 else f"{h // 24} d"
    return T(f"hace {cuanto}", f"{cuanto} ago")


def cargar() -> dict | None:
    if not ARCHIVO.exists():
        return None
    return json.loads(ARCHIVO.read_text(encoding="utf-8"))


def evaluar(datos: dict | None, ahora: dt.datetime | None = None) -> dict:
    """Devuelve el indicador 'radiacion' (mismo formato que los demás) más el detalle para la ficha."""
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    nombre = T("Radiación (clima espacial)", "Radiation (space weather)")
    if not datos:
        return {"indicador": "radiacion", "nombre": nombre, "valor": T("sin datos", "no data"), "unidad": "", "color": "sin dato",
                "accion": T("Sincroniza el clima espacial cuando haya señal con la Tierra.", "Sync space weather when there is a signal to Earth."),
                "eventos": [], "fuente": "NASA DONKI"}

    eventos = [{**e, "_t": _fecha(e.get("pico") or e.get("inicio"))} for e in datos.get("eventos", [])]
    eventos = [e for e in eventos if e["_t"]]
    recientes = lambda horas: [e for e in eventos if ahora - e["_t"] <= dt.timedelta(hours=horas)]  # noqa: E731

    color = "verde"
    motivo = T("Sin eventos solares relevantes recientes.", "No relevant recent solar events.")
    accion = T("Sigue revisando tu dosímetro como de costumbre.", "Keep checking your dosimeter as usual.")
    sep = [e for e in recientes(72) if e["tipo"] == "particulas"]
    x = [e for e in recientes(72) if e["tipo"] == "llamarada" and str(e.get("clase", "")).startswith("X")]
    m = [e for e in recientes(24) if e["tipo"] == "llamarada" and str(e.get("clase", "")).startswith("M")]
    gst = [e for e in recientes(72) if e["tipo"] == "tormenta_geomagnetica" and (e.get("kp") or 0) >= 7]
    if sep:
        color, motivo = "rojo", T("Evento de partículas solares", "Solar particle event") + f" {_hace(ahora - sep[-1]['_t'])}."
        accion = T("Ve al área protegida de la nave según el protocolo y revisa tu dosímetro.",
                   "Go to the ship's shielded area per protocol and check your dosimeter.")
    elif x or m or gst:
        e = (x or m or gst)[-1]
        tipo = T("Llamarada", "Flare") if e["tipo"] == "llamarada" else T("Tormenta geomagnética", "Geomagnetic storm")
        color, motivo = "amarillo", f"{tipo} {e['clase']} {_hace(ahora - e['_t'])}."
        accion = T("Vigila el dosímetro y los avisos de clima espacial; prepárate por si hay que ir al área protegida.",
                   "Watch your dosimeter and space weather alerts; be ready in case you need to go to the shielded area.")

    ultimo = eventos[-1] if eventos else None
    hace = _hace(ahora - ultimo["_t"]) if ultimo else None
    valor = f"{ultimo['clase']} {hace}" if ultimo else T("sin eventos", "no events")
    sync = _fecha(datos.get("sincronizado"))
    antiguedad_min = int((ahora - sync).total_seconds() // 60) if sync else None
    if antiguedad_min is not None and antiguedad_min > 48 * 60:
        motivo += " " + T(f"Datos sin sincronizar desde {_hace(ahora - sync)}: pueden faltar eventos nuevos.",
                          f"Data not synced for {_hace(ahora - sync).replace(' ago', '')}: new events may be missing.")

    return {
        "indicador": "radiacion", "nombre": nombre, "valor": valor, "unidad": "", "color": color,
        "evento": ultimo["clase"] if ultimo else None, "hace": hace,
        "antiguedad_min": antiguedad_min, "motivo": motivo, "accion": accion,
        "sincronizado": datos.get("sincronizado"), "desde": datos.get("desde"), "hasta": datos.get("hasta"),
        "fuente": datos.get("fuente", "NASA DONKI"), "url": datos.get("url"),
        "eventos": [{k: v for k, v in e.items() if k != "_t"} for e in eventos[-40:]],
    }


def indicador() -> dict:
    """Solo los campos del indicador (para mezclar con el estado del astronauta)."""
    r = evaluar(cargar())
    return {k: r[k] for k in ("indicador", "nombre", "valor", "unidad", "color", "antiguedad_min", "accion", "motivo",
                              "evento", "hace") if k in r}
