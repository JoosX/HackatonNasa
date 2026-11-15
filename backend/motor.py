"""Motor de reglas: convierte las mediciones guardadas en el estado del astronauta.

Para cada indicador calcula, con data/reglas.json:
  - color del semáforo (verde, amarillo, rojo),
  - dato sospechoso (fuera de lo físicamente posible: hay que repetir la medición),
  - dato vencido (más viejo que su antigüedad máxima: no se usa para recomendar),
  - tendencia (sube, baja, estable) frente a las mediciones anteriores,
  - "tu normal": promedio de los primeros días de la misión de ESA persona y cuánto se aleja hoy,
  - calidad del dato (vigente, sospechoso, vencido, contexto_pendiente) y su motivo, para no
    presentar como normal un dato que no lo permite (idea de la rama de Romario).

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import datetime as dt
import json
from statistics import mean

import db
import idioma
from idioma import t as T

ORDEN = {"verde": 1, "amarillo": 2, "rojo": 3}
CONTEXTOS = {"reposo": ("en reposo", "at rest"), "despues_ejercicio": ("después de ejercicio", "after exercise"),
             "ayunas": ("en ayunas", "fasting"), "despues_comida": ("después de comer", "after eating"),
             "otro": ("otro", "other")}


def _contexto(c: str) -> str:
    return T(*CONTEXTOS[c]) if c in CONTEXTOS else c


def reglas() -> dict:
    """Reglas por indicador, con nombres, unidades y acciones en el idioma de la petición."""
    return {r["indicador"]: r for r in idioma.reglas()["indicadores"]}


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
            raise ValueError(T("La presión se escribe como sistólica/diastólica, por ejemplo 120/80.",
                               "Blood pressure is written as systolic/diastolic, for example 120/80."))
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
        valor = _mostrar(fila["valor"])
        valor = regla.get("etiquetas", {}).get(valor, valor) if isinstance(valor, str) else valor   # "sin cambios" -> "no change"
        item = {"indicador": nombre, "valor": valor, "unidad": regla.get("unidad", fila["unidad"]),
                "color": color, "antiguedad_min": antig, "origen": fila["origen"], "fecha": fila["ts"],
                "calidad": "vigente", "motivo": T("Medición reciente.", "Recent measurement.")}
        contexto = fila["contexto"] if "contexto" in fila.keys() else None
        if contexto:
            item["contexto"] = contexto
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
            item.update(calidad="sospechoso", motivo=T("Valor fuera de lo físicamente posible: comprueba la medición antes de actuar.",
                                                       "Value outside what is physically possible: check the measurement before acting."))
        elif antig > regla.get("max_antiguedad_min", 10 ** 9):
            item["vencido"] = True
            item.update(calidad="vencido", motivo=T("Medición antigua: registra una nueva, esta ya no describe el momento actual.",
                                                    "Old measurement: log a new one, this one no longer describes the present."))
        elif nombre == "glucosa" and contexto and contexto != "ayunas":
            # El rango de glucosa es de ayunas: no se clasifica una lectura tomada después de comer.
            item.update(calidad="contexto_pendiente", color="sin dato",
                        motivo=T(f"Glucosa medida {_contexto(contexto)}: el rango es de ayunas, así que no la clasifico.",
                                 f"Glucose measured {_contexto(contexto)}: the range is for fasting, so I do not classify it."))
        indicadores.append(item)
        if nombre == "sueno" and _noches_cortas(nums) >= 2:
            notas.append(T(f"{_noches_cortas(nums)} noches seguidas durmiendo menos de 6 horas",
                           f"{_noches_cortas(nums)} nights in a row sleeping less than 6 hours"))
    return {"astronauta_id": astronauta, "indicadores": indicadores, "notas": notas, "origen": "base de datos"}


def _mostrar(valor: str):
    """Devuelve números como número (para que el frontend los formatee) y el resto como texto."""
    try:
        f = float(valor)
        return int(f) if f.is_integer() else f
    except ValueError:
        return valor


def registrar(astronauta: str, indicador: str, valor, origen: str = "manual", contexto: str | None = None) -> dict:
    """Guarda una medición, la clasifica y devuelve el resultado con la acción de la guía."""
    rs = reglas()
    if indicador not in rs:
        raise ValueError(T(f"Indicador desconocido: {indicador}", f"Unknown indicator: {indicador}"))
    regla = rs[indicador]
    texto = str(valor).strip()
    if not texto:
        raise ValueError(T("Escribe un valor.", "Enter a value."))
    try:
        color, sospechoso = clasificar(regla, texto)
    except ValueError as e:
        raise ValueError(str(e) if "/" in str(e) else T(f"El valor de {regla['nombre'].lower()} debe ser un número.",
                                                         f"The {regla['nombre'].lower()} value must be a number.")) from e
    if contexto and contexto not in CONTEXTOS:
        raise ValueError(T("Contexto desconocido.", "Unknown context."))
    db.insertar(astronauta, indicador, texto, valor_num(indicador, texto), regla.get("unidad", ""), origen, contexto=contexto)
    if indicador == "glucosa" and contexto and contexto != "ayunas" and not sospechoso:
        return {"indicador": indicador, "nombre": regla["nombre"], "valor": texto, "unidad": regla.get("unidad", ""),
                "color": "sin dato", "sospechoso": False,
                "mensaje": T(f"Guardado. Medida {_contexto(contexto)}: el rango de glucosa es de ayunas, así que no la clasifico.",
                             f"Saved. Measured {_contexto(contexto)}: the glucose range is for fasting, so I do not classify it.")}
    if sospechoso:
        mensaje = T("Valor inusual: puede ser un error de medición. Repite la medición antes de actuar.",
                    "Unusual value: it may be a measurement error. Repeat the measurement before acting.")
    else:
        mensaje = {"verde": T("Valor normal. ¡Bien!", "Normal value. Good!"), "amarillo": regla["accion"]["amarillo"],
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
