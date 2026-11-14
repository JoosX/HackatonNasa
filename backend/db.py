"""
Capa de base de datos (SQLite, solo libreria estandar: no hay que instalar nada).
Archivo: backend/salud.db  (agregalo al .gitignore)
"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "salud.db"

PARTE_CUERPO = {
    "pulso": "corazon", "presion": "corazon",
    "glucosa": "sangre", "temperatura": "piel", "oxigeno": "pulmones",
    "sueno": "cerebro", "animo": "cerebro", "estres": "cerebro",
}

UNIDADES = {
    "pulso": "lpm", "presion": "mmHg", "glucosa": "mg/dL", "temperatura": "C",
    "oxigeno": "%", "sueno": "h", "animo": "1-5", "estres": "1-10",
}


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def ahora_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def init_db() -> None:
    with conectar() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS astronautas (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                creado_en TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mediciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                astronauta_id INTEGER NOT NULL,
                indicador TEXT NOT NULL,
                valor REAL NOT NULL,
                unidad TEXT,
                origen TEXT NOT NULL DEFAULT 'manual',
                medido_en TEXT NOT NULL,
                registrado_en TEXT NOT NULL,
                color TEXT,
                sospechoso INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (astronauta_id) REFERENCES astronautas(id)
            );
            CREATE INDEX IF NOT EXISTS idx_med
                ON mediciones (astronauta_id, indicador, medido_en);
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                astronauta_id INTEGER NOT NULL,
                indicador TEXT NOT NULL,
                nivel TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                accion TEXT,
                creada_en TEXT NOT NULL,
                activa INTEGER NOT NULL DEFAULT 1,
                medicion_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS config (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cola_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                payload TEXT NOT NULL,
                creada_en TEXT NOT NULL,
                enviada INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        existe = con.execute("SELECT 1 FROM astronautas WHERE id = 1").fetchone()
        if not existe:
            con.execute(
                "INSERT INTO astronautas (id, nombre, creado_en) VALUES (1, 'Astronauta 1', ?)",
                (ahora_iso(),),
            )


# ------------------------------------------------------------ Mediciones
def guardar_medicion(astronauta_id, indicador, valor, origen, medido_en,
                     color=None, sospechoso=False) -> dict:
    registrado = ahora_iso()
    with conectar() as con:
        cur = con.execute(
            """INSERT INTO mediciones
               (astronauta_id, indicador, valor, unidad, origen, medido_en,
                registrado_en, color, sospechoso)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (astronauta_id, indicador, valor, UNIDADES.get(indicador),
             origen, medido_en or registrado, registrado, color, int(sospechoso)),
        )
        return {"id": cur.lastrowid, "medido_en": medido_en or registrado}


def ultimas_por_indicador(astronauta_id: int) -> list[dict]:
    """Ultima medicion de cada indicador."""
    with conectar() as con:
        filas = con.execute(
            """SELECT m.* FROM mediciones m
               JOIN (SELECT indicador, MAX(medido_en) AS mx
                     FROM mediciones WHERE astronauta_id = ?
                     GROUP BY indicador) u
                 ON m.indicador = u.indicador AND m.medido_en = u.mx
               WHERE m.astronauta_id = ?
               GROUP BY m.indicador""",
            (astronauta_id, astronauta_id),
        ).fetchall()
    return [dict(f) for f in filas]


def ultimo_valor(astronauta_id: int, indicador: str) -> dict | None:
    """Ultima medicion de un indicador (valor y hora), o None si no hay."""
    with conectar() as con:
        f = con.execute(
            """SELECT valor, medido_en FROM mediciones
               WHERE astronauta_id = ? AND indicador = ?
               ORDER BY medido_en DESC LIMIT 1""",
            (astronauta_id, indicador),
        ).fetchone()
    return dict(f) if f else None


def historial(astronauta_id: int, indicador: str, desde_iso: str | None = None) -> list[dict]:
    sql = "SELECT medido_en, valor, color, sospechoso FROM mediciones WHERE astronauta_id = ? AND indicador = ?"
    params: list = [astronauta_id, indicador]
    if desde_iso:
        sql += " AND medido_en >= ?"
        params.append(desde_iso)
    sql += " ORDER BY medido_en ASC"
    with conectar() as con:
        return [dict(f) for f in con.execute(sql, params).fetchall()]


def total_mediciones(astronauta_id: int) -> int:
    with conectar() as con:
        return con.execute(
            "SELECT COUNT(*) FROM mediciones WHERE astronauta_id = ?", (astronauta_id,)
        ).fetchone()[0]


# ------------------------------------------------------------ Alertas
def crear_alerta(astronauta_id, indicador, nivel, mensaje, accion, medicion_id=None) -> int:
    with conectar() as con:
        cur = con.execute(
            """INSERT INTO alertas
               (astronauta_id, indicador, nivel, mensaje, accion, creada_en, medicion_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (astronauta_id, indicador, nivel, mensaje, accion, ahora_iso(), medicion_id),
        )
        return cur.lastrowid


def alertas_activas(astronauta_id: int) -> list[dict]:
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM alertas WHERE astronauta_id = ? AND activa = 1 ORDER BY creada_en DESC",
            (astronauta_id,),
        ).fetchall()
    return [dict(f) | {"activa": bool(f["activa"])} for f in filas]


def cerrar_alertas(astronauta_id: int, indicador: str) -> None:
    """Cierra las alertas activas de un indicador (cuando vuelve a verde)."""
    with conectar() as con:
        con.execute(
            "UPDATE alertas SET activa = 0 WHERE astronauta_id = ? AND indicador = ? AND activa = 1",
            (astronauta_id, indicador),
        )


# ------------------------------------------------------------ Config y cola de sincronizacion
def get_config(clave: str, defecto: str | None = None) -> str | None:
    with conectar() as con:
        f = con.execute("SELECT valor FROM config WHERE clave = ?", (clave,)).fetchone()
    return f["valor"] if f else defecto


def set_config(clave: str, valor: str) -> None:
    with conectar() as con:
        con.execute(
            "INSERT INTO config (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, valor),
        )


def encolar(tipo: str, payload_json: str) -> int:
    with conectar() as con:
        cur = con.execute(
            "INSERT INTO cola_sync (tipo, payload, creada_en) VALUES (?, ?, ?)",
            (tipo, payload_json, ahora_iso()),
        )
        return cur.lastrowid


def contar_pendientes() -> int:
    with conectar() as con:
        return con.execute("SELECT COUNT(*) FROM cola_sync WHERE enviada = 0").fetchone()[0]


def enviar_pendientes() -> int:
    """Marca como enviados todos los pendientes y devuelve cuantos eran."""
    with conectar() as con:
        cur = con.execute("UPDATE cola_sync SET enviada = 1 WHERE enviada = 0")
        return cur.rowcount
