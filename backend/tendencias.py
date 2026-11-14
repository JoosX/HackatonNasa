"""
Tendencias (Bloque 3).
- linea_base: el "tu normal" personal = promedio de los primeros registros validos.
- direccion: subiendo / bajando / estable, segun la pendiente de los ultimos registros.
Los datos sospechosos se ignoran en todos los calculos.
"""

N_BASE = 5          # cuantos primeros registros forman la linea base
N_VENTANA = 6       # cuantos ultimos registros se usan para la direccion
MIN_PUNTOS = 3      # con menos puntos no se puede decir nada
UMBRAL_PCT = 5.0    # cambio total menor a este % del promedio = "estable"


def linea_base(valores: list[float], n: int = N_BASE) -> float | None:
    primeros = valores[:n]
    if not primeros:
        return None
    return round(sum(primeros) / len(primeros), 2)


def direccion(valores: list[float]) -> str:
    """Pendiente por minimos cuadrados sobre los ultimos N_VENTANA valores."""
    v = valores[-N_VENTANA:]
    n = len(v)
    if n < MIN_PUNTOS:
        return "desconocida"
    xs = range(n)
    mx = (n - 1) / 2
    my = sum(v) / n
    den = sum((x - mx) ** 2 for x in xs)
    pendiente = sum((x - mx) * (y - my) for x, y in zip(xs, v)) / den
    cambio_total = pendiente * (n - 1)
    referencia = abs(my) or 1.0
    if abs(cambio_total) / referencia * 100 < UMBRAL_PCT:
        return "estable"
    return "subiendo" if cambio_total > 0 else "bajando"


def resumen(todos: list[dict], ventana: list[dict] | None = None) -> dict:
    """todos: historial completo (para la linea base). ventana: puntos a mostrar
    (para la direccion); si no se da, se usan todos. Cada punto: {"valor", "sospechoso"}."""
    validos = [p["valor"] for p in todos if not p.get("sospechoso")]
    base = linea_base(validos)

    origen = ventana if ventana is not None else todos
    recientes = [p["valor"] for p in origen if not p.get("sospechoso")]

    desviacion = None
    if base and recientes:
        desviacion = round((recientes[-1] - base) / abs(base) * 100, 1)

    return {
        "linea_base": base,
        "direccion": direccion(recientes),
        "desviacion_pct": desviacion,   # % del ultimo valor respecto a tu normal
        "n_validos": len(validos),
    }
