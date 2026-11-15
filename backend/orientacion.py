"""Biblioteca de orientación: cómo medir, por qué importa, qué hacer y cuándo avisar, por indicador.

Expuesta sin IA ni acceso a archivos arbitrarios. Autor original: Romario (rama romario/orientacion-fundamentada),
integrado en esta versión con el catálogo de indicadores de data/reglas.json.
"""
import json

import idioma
from guias import RAIZ, CARPETA_GUIAS, leer_guia, fragmentar  # noqa: F401  (CARPETA_GUIAS: lo usan las pruebas)
from idioma import t as T

# Los ocho indicadores que se pueden registrar a bordo (nombre y unidad salen de reglas.json).
INDICADORES = ("pulso", "presion_arterial", "oxigeno", "glucosa", "temperatura", "sueno", "animo", "estres")


def _catalogo() -> dict:
    reglas = {r["indicador"]: r for r in idioma.reglas()["indicadores"]}
    return {n: (reglas[n]["nombre"], reglas[n].get("unidad", "")) for n in INDICADORES}


CATALOGO = _catalogo()   # en español; biblioteca() usa el del idioma de la petición

EQUIPOS_EN = {
    'pulso': 'Pulse monitor available in the mission kit; follow its manual.',
    'presion_arterial': 'Properly sized blood pressure monitor and cuff from the mission kit.',
    'oxigeno': 'Pulse oximeter from the mission kit.',
    'glucosa': 'Glucose meter and supplies from the kit; follow the manual and the mission protocol.',
    'temperatura': 'Thermometer from the kit; also log the measurement method.',
    'sueno': 'Daily log of hours of sleep; say whether it is an estimate or a device reading.',
    'animo': 'Self-report: demo scale 1 = very low, 5 = very good; not clinically validated.',
    'estres': 'Self-report: demo scale 1 = very low, 5 = very high; not clinically validated.',
}

EQUIPOS = {
    'pulso': 'Monitor de pulso disponible en el kit de la misión; sigue su manual.',
    'presion_arterial': 'Tensiómetro y manguito adecuados del kit de la misión.',
    'oxigeno': 'Oxímetro del kit de la misión.',
    'glucosa': 'Glucómetro y material del kit; sigue el manual y el protocolo de la misión.',
    'temperatura': 'Termómetro del kit; registra también el método de medición.',
    'sueno': 'Registro diario de horas de sueño; indica si es estimación o lectura de un dispositivo.',
    'animo': 'Autorreporte: escala de demostración 1 = muy bajo, 5 = muy bueno; no validada clínicamente.',
    'estres': 'Autorreporte: escala de demostración 1 = muy bajo, 5 = muy alto; no validada clínicamente.',
}


def biblioteca():
    reglas = idioma.reglas()['indicadores']
    medicion = json.loads(idioma.datos('medicion_guiada.json').read_text(encoding='utf-8'))
    catalogo = _catalogo()
    equipos = EQUIPOS_EN if idioma.en() else EQUIPOS
    S = idioma.seccion
    salida = {}
    for nombre in catalogo:
        regla = next(r for r in reglas if r['indicador'] == nombre)
        meta, cuerpo = leer_guia(idioma.carpeta_guias() / regla['guia'])
        secciones = {f['seccion']: f['texto'] for f in fragmentar(meta,cuerpo)}
        medir = secciones.get(S('medir'), '')
        if nombre == 'sueno':
            medir = T('Registra las horas dormidas de cada día y su fecha. Usa el mismo criterio entre días y anota si el dato es estimado o proviene de un dispositivo.',
                      'Log the hours slept each day and the date. Use the same criterion every day and note whether the value is an estimate or comes from a device.')
        if nombre == 'pulso':
            medir = T('Utiliza el monitor del kit según su manual. Registra si estabas en reposo o después de ejercicio y conserva la lectura en latidos por minuto.',
                      'Use the kit monitor according to its manual. Log whether you were at rest or after exercise and keep the reading in beats per minute.')
        salida[nombre] = {
            'indicador': nombre, 'nombre': catalogo[nombre][0], 'unidad': catalogo[nombre][1],
            'equipo': equipos[nombre], 'como_medir': medir, 'por_que': secciones.get(S('por_que'),''),
            'espacio': secciones.get(S('espacio'),''),
            'pasos_guia': [l.lstrip('- ').strip() for l in secciones.get(S('hacer'),'').splitlines() if l.startswith('- ')],
            'senales': secciones.get(S('senales'),''), 'cuando_avisar': secciones.get(S('avisar'),''),
            'archivo': regla['guia'], 'titulo': meta['titulo'], 'fuente': meta.get('fuente',''),
            'url': meta.get('url',''), 'version': meta.get('version',''),
            'estado_revision': meta.get('estado', T('ilustrativo, sin revisión clínica', 'illustrative, no clinical review')),
            'autor_contenido': T('Adaptación del equipo basada en las fuentes indicadas; no es un protocolo oficial NASA.',
                                 'Team adaptation based on the sources shown; not an official NASA protocol.'),
            'medicion': dict(medicion['indicadores'][nombre], alcance=medicion['alcance'], version=medicion['version']),
            'regla': {k: regla[k] for k in ('verde','amarillo','componentes','posible','max_antiguedad_min','validacion') if k in regla},
        }
    return {'indicadores':salida}
