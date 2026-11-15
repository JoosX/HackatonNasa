"""Registro manual local. No clasifica resultados ni modifica el estado de demostración."""
import datetime as dt
import json
import os
import sqlite3
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from evolucion import describir

CATALOGO = {
    "pulso": ("Pulso", "lpm"), "presion_arterial": ("Presión arterial", "mmHg"),
    "oxigeno": ("Oxígeno", "%"), "glucosa": ("Glucosa", "mg/dL"),
    "temperatura": ("Temperatura", "°C"), "sueno": ("Sueño", "h"),
    "animo": ("Ánimo", "/5"), "estres": ("Estrés", "/5"),
}


class Medicion(BaseModel):
    id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    astronauta_id: str = Field(default="A1", pattern=r"^[A-Za-z0-9_-]{1,40}$")
    indicador: Literal["pulso", "presion_arterial", "oxigeno", "glucosa", "temperatura", "sueno", "animo", "estres"]
    valor: float = Field(allow_inf_nan=False)
    diastolica: float | None = Field(default=None, allow_inf_nan=False)
    fecha: dt.datetime
    contexto: Literal["sin_especificar", "reposo", "despues_ejercicio", "ayunas", "despues_comida", "otro"] = "sin_especificar"
    nota: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validar(self):
        if self.fecha.tzinfo is None or self.fecha.utcoffset() is None:
            raise ValueError("La fecha debe incluir zona horaria.")
        self.fecha = self.fecha.astimezone(dt.timezone.utc)
        if self.fecha > dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=30):
            raise ValueError("La medición no puede estar en el futuro.")
        if self.indicador != "temperatura" and self.valor < 0:
            raise ValueError("El valor no puede ser negativo.")
        if self.indicador == "oxigeno" and self.valor > 100:
            raise ValueError("Un porcentaje no puede superar 100.")
        if self.indicador == "sueno" and self.valor > 24:
            raise ValueError("El sueño diario no puede superar 24 horas.")
        if self.indicador in ("animo", "estres") and (not self.valor.is_integer() or not 1 <= self.valor <= 5):
            raise ValueError("La escala admite enteros del 1 al 5.")
        if self.indicador == "presion_arterial":
            if self.diastolica is None or self.diastolica <= 0 or self.valor <= self.diastolica:
                raise ValueError("Ingresa sistólica y diastólica positivas; sistólica debe ser mayor.")
        elif self.diastolica is not None:
            raise ValueError("La diastólica solo corresponde a presión arterial.")
        return self


def conectar():
    ruta = Path(os.environ.get("APELOGIC_DB_PATH", Path(__file__).resolve().parent.parent / "data/local/mediciones.sqlite3"))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ruta, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS mediciones (
      id TEXT PRIMARY KEY, astronauta_id TEXT NOT NULL, indicador TEXT NOT NULL,
      valor REAL NOT NULL, diastolica REAL, fecha TEXT NOT NULL,
      contexto TEXT NOT NULL, nota TEXT NOT NULL, creado TEXT NOT NULL)""")
    conn.execute("CREATE INDEX IF NOT EXISTS mediciones_persona_fecha ON mediciones(astronauta_id, fecha)")
    return conn


def serializar(fila):
    d = dict(fila)
    d.update(nombre=CATALOGO[d["indicador"]][0], unidad=CATALOGO[d["indicador"]][1], origen="registro_manual")
    return d


def guardar(m):
    valores = (m.id, m.astronauta_id, m.indicador, m.valor, m.diastolica, m.fecha.isoformat(), m.contexto, m.nota)
    conn = conectar()
    try:
        with conn:
            anterior = conn.execute("SELECT * FROM mediciones WHERE id=?", (m.id,)).fetchone()
            if anterior:
                if tuple(anterior[k] for k in ("id", "astronauta_id", "indicador", "valor", "diastolica", "fecha", "contexto", "nota")) != valores:
                    raise ValueError("Este identificador ya corresponde a otro registro.")
                return serializar(anterior)
            conn.execute("INSERT INTO mediciones VALUES (?,?,?,?,?,?,?,?,?)", (*valores, dt.datetime.now(dt.timezone.utc).isoformat()))
            return serializar(conn.execute("SELECT * FROM mediciones WHERE id=?", (m.id,)).fetchone())
    finally:
        conn.close()


def historial(astronauta_id, indicador=None, limite=100, offset=0):
    conn = conectar()
    try:
        filtro, params = "astronauta_id=?", [astronauta_id]
        if indicador:
            filtro += " AND indicador=?"
            params.append(indicador)
        total = conn.execute(f"SELECT COUNT(*) FROM mediciones WHERE {filtro}", params).fetchone()[0]
        filas = conn.execute(f"SELECT * FROM mediciones WHERE {filtro} ORDER BY fecha DESC, creado DESC, id DESC LIMIT ? OFFSET ?", [*params, limite, offset]).fetchall()
        return {"mediciones": [serializar(f) for f in filas], "total": total, "limite": limite, "offset": offset}
    finally:
        conn.close()


def estado_indicador(astronauta_id, nombre, ahora=None):
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    regla = next(r for r in json.loads((Path(__file__).resolve().parent.parent / 'data/reglas.json').read_text(encoding='utf-8'))['indicadores'] if r['indicador'] == nombre)
    registros = historial(astronauta_id, nombre, 100)
    filas = registros['mediciones']
    def componentes(m):
        if nombre == 'presion_arterial':
            return [(m['valor'], regla['componentes']['sistolica']), (m['diastolica'], regla['componentes']['diastolica'])]
        return [(m['valor'], regla)]
    def sospechoso(m):
        return any(v is None or not r['posible'][0] <= v <= r['posible'][1] for v, r in componentes(m))
    base = {'indicador': nombre, 'nombre': CATALOGO[nombre][0], 'valor': None, 'unidad': CATALOGO[nombre][1], 'color': 'sin dato',
            'origen': 'registro_manual', 'calidad': 'ausente', 'antiguedad_min': None,
            'motivo': f'Sin mediciones de {CATALOGO[nombre][0].lower()} guardadas. Registra una medición.', 'historial': [],
            'regla_ilustrativa': True, 'fuente': regla['fuente']}
    base['historial'] = [{'valor': m['valor'], 'diastolica': m['diastolica'], 'fecha': m['fecha'], 'contexto': m['contexto'],
                          'sospechoso': sospechoso(m)} for m in reversed(filas)]
    if not filas:
        if nombre in ('pulso','sueno'):
            base['evolucion'] = describir(base,ahora,registros['total']>100)
        return base
    ultima = filas[0]
    edad = max(0, int((ahora - dt.datetime.fromisoformat(ultima['fecha'])).total_seconds() // 60))
    v = f"{ultima['valor']:g}/{ultima['diastolica']:g}" if nombre == 'presion_arterial' else ultima['valor']
    base.update(valor=v, diastolica=ultima['diastolica'], fecha=ultima['fecha'], antiguedad_min=edad, contexto=ultima['contexto'])
    if sospechoso(ultima):
        base.update(calidad='sospechoso', motivo='Valor fuera del intervalo de plausibilidad ilustrativo. Comprueba la medición; no se clasifica como normal.')
    elif edad > regla['max_antiguedad_min']:
        base.update(calidad='vencido', motivo=f'Medición vencida según el límite ilustrativo de {regla["max_antiguedad_min"]} minutos. Registra una nueva; no describe el estado actual.')
    elif nombre == 'glucosa' and ultima['contexto'] != 'ayunas':
        base.update(calidad='contexto_pendiente', motivo='El rango ilustrativo de glucosa no está adaptado a comidas u otros contextos. Conservamos el valor sin clasificar; registra si fue en ayunas.')
    else:
        def clasificar(v, r):
            return 'verde' if r['verde'][0] <= v <= r['verde'][1] else 'amarillo' if r['amarillo'][0] <= v <= r['amarillo'][1] else 'rojo'
        color = max((clasificar(v, r) for v, r in componentes(ultima)), key=['verde','amarillo','rojo'].index)
        base.update(calidad='vigente', color=color, motivo='Registro manual reciente.',
                    accion=regla['accion'].get(color, 'Consulta el contexto y la evolución de tu medición.'))
    if nombre in ('pulso','sueno'):
        base['evolucion'] = describir(base,ahora,registros['total']>100)
    return base


def estado_pulso(astronauta_id, ahora=None):
    return estado_indicador(astronauta_id, 'pulso', ahora)


def estado_personal(astronauta_id):
    return [estado_indicador(astronauta_id, nombre) for nombre in CATALOGO]
