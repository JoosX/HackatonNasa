"""Base de datos local de la misión (SQLite): mediciones, alertas y conversación con ORI.

Un solo archivo (data/mision.db), sin servidor: funciona sin internet, como debe ser en la nave.
Al primer arranque se siembra un historial de 7 días de demostración (realista y determinista)
para que las tendencias y el "tu normal" tengan datos. Las mediciones nuevas se agregan encima.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import datetime as dt
import os
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA = Path(os.environ.get("DB_RUTA", RAIZ / "data" / "mision.db"))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS mediciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  astronauta TEXT NOT NULL, indicador TEXT NOT NULL,
  valor TEXT NOT NULL, valor_num REAL, unidad TEXT, origen TEXT NOT NULL DEFAULT 'manual',
  ts TEXT NOT NULL, contexto TEXT
);
CREATE INDEX IF NOT EXISTS idx_med ON mediciones (astronauta, indicador, ts);
CREATE TABLE IF NOT EXISTS alertas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  astronauta TEXT NOT NULL, indicador TEXT NOT NULL, color TEXT NOT NULL, mensaje TEXT, ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversacion (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  astronauta TEXT NOT NULL, rol TEXT NOT NULL, texto TEXT NOT NULL, ts TEXT NOT NULL
);
"""


def ahora() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_creada = False


def conectar() -> sqlite3.Connection:
    global _creada
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(RUTA)
    con.row_factory = sqlite3.Row
    if not _creada:   # las tablas se crean solas en el primer uso
        con.executescript(ESQUEMA)
        columnas = {f[1] for f in con.execute("PRAGMA table_info(mediciones)")}
        if "contexto" not in columnas:   # bases creadas antes de guardar el contexto de la medición
            con.execute("ALTER TABLE mediciones ADD COLUMN contexto TEXT")
        _creada = True
    return con


def crear() -> None:
    conectar().close()   # conectar() crea las tablas y migra columnas nuevas


def insertar(astronauta: str, indicador: str, valor, valor_num, unidad: str, origen: str = "manual",
             ts: dt.datetime | None = None, contexto: str | None = None) -> int:
    with conectar() as con:
        cur = con.execute(
            "INSERT INTO mediciones (astronauta, indicador, valor, valor_num, unidad, origen, ts, contexto) VALUES (?,?,?,?,?,?,?,?)",
            (astronauta, indicador, str(valor), valor_num, unidad, origen, iso(ts or ahora()), contexto))
        return cur.lastrowid


def ultimas(astronauta: str) -> dict[str, sqlite3.Row]:
    """Última medición de cada indicador."""
    with conectar() as con:
        filas = con.execute("""
            SELECT m.* FROM mediciones m
            JOIN (SELECT indicador, MAX(ts) AS t FROM mediciones WHERE astronauta=? GROUP BY indicador) u
              ON m.indicador = u.indicador AND m.ts = u.t
            WHERE m.astronauta=? ORDER BY m.id""", (astronauta, astronauta)).fetchall()
    return {f["indicador"]: f for f in filas}


def serie(astronauta: str, indicador: str, dias: int = 7) -> list[sqlite3.Row]:
    desde = iso(ahora() - dt.timedelta(days=dias))
    with conectar() as con:
        return con.execute("SELECT * FROM mediciones WHERE astronauta=? AND indicador=? AND ts>=? ORDER BY ts",
                           (astronauta, indicador, desde)).fetchall()


def contar(astronauta: str) -> int:
    with conectar() as con:
        return con.execute("SELECT COUNT(*) FROM mediciones WHERE astronauta=?", (astronauta,)).fetchone()[0]


def registrar_alerta(astronauta: str, indicador: str, color: str, mensaje: str) -> None:
    with conectar() as con:
        con.execute("INSERT INTO alertas (astronauta, indicador, color, mensaje, ts) VALUES (?,?,?,?,?)",
                    (astronauta, indicador, color, mensaje, iso(ahora())))


def alertas(astronauta: str, limite: int = 20) -> list[dict]:
    with conectar() as con:
        return [dict(f) for f in con.execute(
            "SELECT * FROM alertas WHERE astronauta=? ORDER BY id DESC LIMIT ?", (astronauta, limite))]


def guardar_turno(astronauta: str, rol: str, texto: str) -> None:
    with conectar() as con:
        con.execute("INSERT INTO conversacion (astronauta, rol, texto, ts) VALUES (?,?,?,?)",
                    (astronauta, rol, texto, iso(ahora())))


def ultimos_turnos(astronauta: str, n: int = 4) -> list[dict]:
    with conectar() as con:
        filas = con.execute("SELECT rol, texto FROM conversacion WHERE astronauta=? ORDER BY id DESC LIMIT ?",
                            (astronauta, n)).fetchall()
    return [dict(f) for f in reversed(filas)]


# ---------- Historial de demostración (7 días) ----------
# Cuenta una historia coherente para la demo: pulso y presión que suben, sueño que cae noche a noche,
# ánimo que baja. Termina en los mismos valores que el estado de ejemplo.
HISTORIA = {
    # indicador: (unidad, [(días atrás, horas atrás extra, valor), ...])
    "pulso": ("lpm", [(6, 2, 68), (6, 12, 71), (5, 2, 70), (5, 12, 72), (4, 2, 69), (4, 12, 74), (3, 2, 76),
                      (3, 12, 79), (2, 2, 83), (2, 12, 86), (1, 2, 90), (1, 12, 92), (0, 0.2, 96)]),
    "presion_arterial": ("mmHg", [(6, 2, "118/76"), (5, 2, "116/75"), (4, 2, "121/78"), (3, 2, "126/80"),
                                  (2, 2, "131/84"), (1, 2, "137/88"), (0, 0.2, "142/92")]),
    "oxigeno": ("%", [(6, 2, 98), (5, 2, 97), (4, 2, 98), (3, 2, 97), (2, 2, 98), (1, 2, 97), (0, 0.2, 97)]),
    "glucosa": ("mg/dL", [(6, 8, 86), (5, 8, 88), (4, 8, 85), (3, 8, 91), (2, 8, 95), (1, 8, 99), (0, 1.5, 103)]),
    "temperatura": ("°C", [(6, 3, 36.6), (5, 3, 36.5), (4, 3, 36.7), (3, 3, 36.6), (2, 3, 36.7), (1, 3, 36.7), (0, 1, 36.8)]),
    "sueno": ("h", [(6, 8, 7.2), (5, 8, 6.9), (4, 8, 6.4), (3, 8, 5.6), (2, 8, 5.4), (1, 8, 4.9), (0, 8, 4.5)]),
    "animo": ("/5", [(6, 1, 4), (5, 1, 4), (4, 1, 3), (3, 1, 3), (2, 1, 3), (1, 1, 2), (0, 0.5, 2)]),
    "estres": ("/5", [(6, 1, 2), (5, 1, 2), (4, 1, 2), (3, 1, 3), (2, 1, 3), (1, 1, 3), (0, 0.5, 3)]),
    "perdida_osea": ("%/mes", [(6, 0, "-0,9"), (0, 168 - 144, "-1,1")]),
    "vision": ("", [(6, 0, "sin cambios"), (3, 0, "sin cambios")]),
}


def sembrar(astronauta: str = "A1", forzar: bool = False, valor_num=None) -> bool:
    """Carga el historial de demostración si la base está vacía (o si se fuerza, para reiniciar la demo)."""
    crear()
    if contar(astronauta) and not forzar:
        return False
    with conectar() as con:
        con.execute("DELETE FROM mediciones WHERE astronauta=?", (astronauta,))
        con.execute("DELETE FROM alertas WHERE astronauta=?", (astronauta,))
        con.execute("DELETE FROM conversacion WHERE astronauta=?", (astronauta,))
    t0 = ahora()
    for indicador, (unidad, puntos) in HISTORIA.items():
        for dias, horas, valor in puntos:
            ts = t0 - dt.timedelta(days=dias, hours=horas)
            insertar(astronauta, indicador, valor, valor_num(indicador, valor) if valor_num else None, unidad, "demo", ts)
    return True
