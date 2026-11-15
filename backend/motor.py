"""Motor de reglas: convierte las mediciones guardadas en el estado del astronauta.

Para cada indicador calcula, con data/reglas.json:
  - color del semáforo (verde, amarillo, rojo),
  - dato sospechoso (fuera de lo físicamente posible: hay que repetir la medición),
  - dato vencido (más viejo que su antigüedad máxima: no se usa para recomendar),
  - tendencia (sube, baja, estable) frente a las mediciones anteriores,
  - "tu normal": promedio de los primeros días de la misión de ESA persona y cuánto se aleja hoy.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import datetime as dt
import json
from statistics import mean

import db

ORDEN = {"verde": 1, "amarillo": 2, "rojo": 3}


def reglas() -> dict:
    datos = json.loads((db.RAIZ / "data" / "reglas.json").read_text(encoding="utf-8"))
    return {r["indicador"]: r for r in datos["indicadores"]}


def valor_num(indicador: str, valor) -> float | None:
    """Número para graficar y comparar (la presión usa la sistólica; lo categórico no tiene número)."""
    try:
        return float(str(valor).split("/")[0].replace(",", "."))
    except ValueError:
        return None


def _rango(c: dict, v: float) -> str:
    if c["verde"][0] <= v <= c["verde"][1]:
        return "verde"
    if c["amarillo"][0] <= v <= c["amarillo"][1]:
        return "amarillo"
    return "rojo"


def clasificar(regla: dict, valor) -> tuple[str, bool]:
    """(color, sospechoso)."""
    if "categorias" in regla:
        return regla["categorias"].get(str(valor).strip().lower(), "amarillo"), False
    if "componentes" in regla:
        partes = str(valor).replace(" ", "").split("/")
        if len(partes) != 2:
            raise ValueError("La presión se escribe como sistólica/diastólica, por ejemplo 120/80.")
        nums = [float(p) for p in partes]
        colores, sospechoso = [], False
        for c, v in zip(regla["componentes"].values(), nums):
            colores.append(_rango(c, v))
            sospechoso |= not (c["posible"][0] <= v <= c["posible"][1])
        return max(colores, key=ORDEN.get), sospechoso
    v = float(str(valor).replace(",", "."))
    return _rango(regla, v), not (regla["posible"][0] <= v <= regla["posible"][1])


def _tendencia(nums: list[float], regla: dict) -> str | None:
    if len(nums) < 3:
        return None
    previo = mean(nums[-4:-1])
    ancho = (regla.get("verde") or regla.get("componentes", {}).get("sistolica", {}).get("verde") or [0, 1])
    umbral = max(abs(ancho[1] - ancho[0]) * 0.08, 0.05)
    delta = nums[-1] - previo
    return "sube" if delta > umbral else "baja" if delta < -umbral else "estable"


def _noches_cortas(nums: list[float]) -> int:
    n = 0
    for v in reversed(nums):
        if v < 6:
            n += 1
        else:
            break
    return n


def evaluar(astronauta: str) -> dict:
    """Estado actual calculado desde la base de datos (mismo formato que usa toda la app)."""
    rs = reglas()
    ultimas = db.ultimas(astronauta)
    t_ahora = db.ahora()
    indicadores, notas = [], []
    for nombre, regla in rs.items():
        fila = ultimas.get(nombre)
        if not fila:
            continue
        color, sospechoso = clasificar(regla, fila["valor"])
        t = dt.datetime.strptime(fila["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        antig = int((t_ahora - t).total_seconds() // 60)
        filas = db.serie(astronauta, nombre, 7)
        nums = [f["valor_num"] for f in filas if f["valor_num"] is not None]
        item = {"indicador": nombre, "valor": _mostrar(fila["valor"]), "unidad": regla.get("unidad", fila["unidad"]),
                "color": color, "antiguedad_min": antig, "origen": fila["origen"]}
        tend = _tendencia(nums, regla)
        if tend:
            item["tendencia"] = tend
        if len(nums) >= 5:   # "tu normal": promedio de las primeras mediciones (inicio de la semana)
            base = mean(nums[:3])
            item["normal"] = round(base, 1)
            if base:
                item["desviacion_pct"] = round((nums[-1] - base) / abs(base) * 100)
        if sospechoso:
            item["sospechoso"] = True
        if antig > regla.get("max_antiguedad_min", 10 ** 9):
            item["vencido"] = True
        indicadores.append(item)
        if nombre == "sueno" and _noches_cortas(nums) >= 2:
            notas.append(f"{_noches_cortas(nums)} noches seguidas durmiendo menos de 6 horas")
    return {"astronauta_id": astronauta, "indicadores": indicadores, "notas": notas, "origen": "base de datos"}


def _mostrar(valor: str):
    """Devuelve números como número (para que el frontend los formatee) y el resto como texto."""
    try:
        f = float(valor)
        return int(f) if f.is_integer() else f
    except ValueError:
        return valor


def registrar(astronauta: str, indicador: str, valor, origen: str = "manual") -> dict:
    """Guarda una medición, la clasifica y devuelve el resultado con la acción de la guía."""
    rs = reglas()
    if indicador not in rs:
        raise ValueError(f"Indicador desconocido: {indicador}")
    regla = rs[indicador]
    texto = str(valor).strip()
    if not texto:
        raise ValueError("Escribe un valor.")
    try:
        color, sospechoso = clasificar(regla, texto)
    except ValueError as e:
        raise ValueError(str(e) if "presión" in str(e) else f"El valor de {regla['nombre'].lower()} debe ser un número.") from e
    db.insertar(astronauta, indicador, texto, valor_num(indicador, texto), regla.get("unidad", ""), origen)
    if sospechoso:
        mensaje = "Valor inusual: puede ser un error de medición. Repite la medición antes de actuar."
    else:
        mensaje = {"verde": "Valor normal. ¡Bien!", "amarillo": regla["accion"]["amarillo"],
                   "rojo": regla["accion"]["rojo"]}[color]
    if color == "rojo" and not sospechoso:
        db.registrar_alerta(astronauta, indicador, color, mensaje)
    return {"indicador": indicador, "nombre": regla["nombre"], "valor": texto, "unidad": regla.get("unidad", ""),
            "color": color, "sospechoso": sospechoso, "mensaje": mensaje}


def historial(astronauta: str, dias: int = 7) -> dict:
    """Series de todos los indicadores numéricos (para las gráficas)."""
    salida = {}
    for nombre in reglas():
        filas = db.serie(astronauta, nombre, dias)
        puntos = [{"ts": f["ts"], "valor": f["valor"], "num": f["valor_num"]} for f in filas if f["valor_num"] is not None]
        if puntos:
            salida[nombre] = puntos
    return salida
