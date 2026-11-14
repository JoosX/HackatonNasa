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

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "data" / "nasa_donki.json"
NOMBRE = "Radiación (clima espacial)"


def _fecha(t: str | None) -> dt.datetime | None:
    if not t:
        return None
    try:
        return dt.datetime.strptime(t[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def _hace(delta: dt.timedelta) -> str:
    h = int(delta.total_seconds() // 3600)
    return f"hace {h} h" if h < 48 else f"hace {h // 24} d"


def cargar() -> dict | None:
    if not ARCHIVO.exists():
        return None
    return json.loads(ARCHIVO.read_text(encoding="utf-8"))


def evaluar(datos: dict | None, ahora: dt.datetime | None = None) -> dict:
    """Devuelve el indicador 'radiacion' (mismo formato que los demás) más el detalle para la ficha."""
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    if not datos:
        return {"indicador": "radiacion", "nombre": NOMBRE, "valor": "sin datos", "unidad": "", "color": "sin dato",
                "accion": "Sincroniza el clima espacial cuando haya señal con la Tierra.", "eventos": [], "fuente": "NASA DONKI"}

    eventos = [{**e, "_t": _fecha(e.get("pico") or e.get("inicio"))} for e in datos.get("eventos", [])]
    eventos = [e for e in eventos if e["_t"]]
    recientes = lambda horas: [e for e in eventos if ahora - e["_t"] <= dt.timedelta(hours=horas)]  # noqa: E731

    color, motivo, accion = "verde", "Sin eventos solares relevantes recientes.", "Sigue revisando tu dosímetro como de costumbre."
    sep = [e for e in recientes(72) if e["tipo"] == "particulas"]
    x = [e for e in recientes(72) if e["tipo"] == "llamarada" and str(e.get("clase", "")).startswith("X")]
    m = [e for e in recientes(24) if e["tipo"] == "llamarada" and str(e.get("clase", "")).startswith("M")]
    gst = [e for e in recientes(72) if e["tipo"] == "tormenta_geomagnetica" and (e.get("kp") or 0) >= 7]
    if sep:
        color, motivo = "rojo", f"Evento de partículas solares {_hace(ahora - sep[-1]['_t'])}."
        accion = "Ve al área protegida de la nave según el protocolo y revisa tu dosímetro."
    elif x or m or gst:
        e = (x or m or gst)[-1]
        color, motivo = "amarillo", f"{'Llamarada ' + e['clase'] if e['tipo'] == 'llamarada' else 'Tormenta geomagnética ' + str(e['clase'])} {_hace(ahora - e['_t'])}."
        accion = "Vigila el dosímetro y los avisos de clima espacial; prepárate por si hay que ir al área protegida."

    ultimo = eventos[-1] if eventos else None
    valor = f"{ultimo['clase']} {_hace(ahora - ultimo['_t'])}" if ultimo else "sin eventos"
    sync = _fecha(datos.get("sincronizado"))
    antiguedad_min = int((ahora - sync).total_seconds() // 60) if sync else None
    if antiguedad_min is not None and antiguedad_min > 48 * 60:
        motivo += f" Datos sin sincronizar desde {_hace(ahora - sync)}: pueden faltar eventos nuevos."

    return {
        "indicador": "radiacion", "nombre": NOMBRE, "valor": valor, "unidad": "", "color": color,
        "antiguedad_min": antiguedad_min, "motivo": motivo, "accion": accion,
        "sincronizado": datos.get("sincronizado"), "desde": datos.get("desde"), "hasta": datos.get("hasta"),
        "fuente": datos.get("fuente", "NASA DONKI"), "url": datos.get("url"),
        "eventos": [{k: v for k, v in e.items() if k != "_t"} for e in eventos[-40:]],
    }


def indicador() -> dict:
    """Solo los campos del indicador (para mezclar con el estado del astronauta)."""
    r = evaluar(cargar())
    return {k: r[k] for k in ("indicador", "nombre", "valor", "unidad", "color", "antiguedad_min", "accion", "motivo") if k in r}
