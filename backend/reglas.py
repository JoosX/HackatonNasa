"""
Motor de reglas (Bloque 3).
Lee data/reglas.json y decide: color, si es sospechoso, si esta vencido y que accion sugerir.

El JSON se vuelve a leer solo cuando el archivo cambia, asi que si reemplazas
reglas.json (por ejemplo con el de P6) NO hace falta tocar codigo ni reiniciar.
"""
import json
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "data" / "reglas.json"
_cache = {"mtime": None, "reglas": {}}


def cargar() -> dict:
    """Devuelve {indicador: regla}. Acepta una lista, un dict {"reglas": [...]},
    un dict {indicador: regla} o una sola regla."""
    try:
        mtime = RUTA.stat().st_mtime
    except FileNotFoundError:
        return {}
    if _cache["mtime"] != mtime:
        with open(RUTA, encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict) and "reglas" in datos:
            datos = datos["reglas"]
        if isinstance(datos, dict):
            if "indicador" in datos:
                datos = [datos]
            else:
                datos = [{"indicador": k, **v} for k, v in datos.items()]
        _cache["reglas"] = {r["indicador"]: r for r in datos}
        _cache["mtime"] = mtime
    return _cache["reglas"]


def _en(valor, rango) -> bool:
    return bool(rango) and rango[0] <= valor <= rango[1]


def evaluar(indicador: str, valor: float, anterior: float | None = None) -> dict:
    """Evalua una medicion.
    anterior: valor reciente del mismo indicador (para detectar saltos bruscos).
    Devuelve: color (verde|amarillo|rojo|gris), sospechoso, accion, mensaje, fuente."""
    regla = cargar().get(indicador)
    if regla is None:
        return {"color": "gris", "sospechoso": False, "accion": None,
                "mensaje": None, "fuente": None}

    unidad = regla.get("unidad", "")
    fuente = regla.get("fuente")

    # 1) Sospechoso: fuera de lo humanamente posible o salto brusco
    fuera_posible = not _en(valor, regla.get("posible"))
    max_salto = regla.get("max_salto")
    salto = anterior is not None and max_salto is not None and abs(valor - anterior) > max_salto
    if fuera_posible or salto:
        motivo = "valor imposible" if fuera_posible else "cambio demasiado brusco"
        return {"color": "gris", "sospechoso": True,
                "accion": "Dato sospechoso: mide de nuevo",
                "mensaje": f"{indicador} {valor} {unidad}: {motivo}", "fuente": fuente}

    # 2) Semaforo
    if _en(valor, regla.get("verde")):
        color = "verde"
    elif _en(valor, regla.get("amarillo")):
        color = "amarillo"
    else:
        color = "rojo"

    accion = regla.get("accion", {}).get(color)
    mensaje = None if color == "verde" else f"{indicador} {valor} {unidad}: fuera del rango verde"
    return {"color": color, "sospechoso": False, "accion": accion,
            "mensaje": mensaje, "fuente": fuente}


def vencido(indicador: str, antiguedad_min: int) -> bool:
    regla = cargar().get(indicador)
    limite = regla.get("max_antiguedad_min") if regla else None
    return limite is not None and antiguedad_min > limite
