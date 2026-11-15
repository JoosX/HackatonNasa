"""Biblioteca de orientación: cómo medir, por qué importa, qué hacer y cuándo avisar, por indicador.

Expuesta sin IA ni acceso a archivos arbitrarios. Autor original: Romario (rama romario/orientacion-fundamentada),
integrado en esta versión con el catálogo de indicadores de data/reglas.json.
"""
import json
from guias import RAIZ, CARPETA_GUIAS, leer_guia, fragmentar

# Los ocho indicadores que se pueden registrar a bordo (nombre y unidad salen de reglas.json).
INDICADORES = ("pulso", "presion_arterial", "oxigeno", "glucosa", "temperatura", "sueno", "animo", "estres")


def _catalogo() -> dict:
    reglas = {r["indicador"]: r for r in json.loads((RAIZ / "data/reglas.json").read_text(encoding="utf-8"))["indicadores"]}
    return {n: (reglas[n]["nombre"], reglas[n].get("unidad", "")) for n in INDICADORES}


CATALOGO = _catalogo()

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
    reglas = json.loads((RAIZ / 'data/reglas.json').read_text(encoding='utf-8'))['indicadores']
    medicion = json.loads((RAIZ / 'data/medicion_guiada.json').read_text(encoding='utf-8'))
    salida = {}
    for nombre in CATALOGO:
        regla = next(r for r in reglas if r['indicador'] == nombre)
        meta, cuerpo = leer_guia(CARPETA_GUIAS / regla['guia'])
        secciones = {f['seccion']: f['texto'] for f in fragmentar(meta,cuerpo)}
        medir = secciones.get('Cómo medir a bordo', '')
        if nombre == 'sueno':
            medir = 'Registra las horas dormidas de cada día y su fecha. Usa el mismo criterio entre días y anota si el dato es estimado o proviene de un dispositivo.'
        if nombre == 'pulso':
            medir = 'Utiliza el monitor del kit según su manual. Registra si estabas en reposo o después de ejercicio y conserva la lectura en latidos por minuto.'
        salida[nombre] = {
            'indicador': nombre, 'nombre': CATALOGO[nombre][0], 'unidad': CATALOGO[nombre][1],
            'equipo': EQUIPOS[nombre], 'como_medir': medir, 'por_que': secciones.get('Por qué importa',''),
            'espacio': secciones.get('Qué pasa en el espacio',''),
            'pasos_guia': [l.lstrip('- ').strip() for l in secciones.get('Qué hacer','').splitlines() if l.startswith('- ')],
            'senales': secciones.get('Señales de alerta',''), 'cuando_avisar': secciones.get('Cuándo avisar',''),
            'archivo': regla['guia'], 'titulo': meta['titulo'], 'fuente': meta.get('fuente',''),
            'url': meta.get('url',''), 'version': meta.get('version',''),
            'estado_revision': meta.get('estado','ilustrativo, sin revisión clínica'),
            'autor_contenido': 'Adaptación del equipo basada en las fuentes indicadas; no es un protocolo oficial NASA.',
            'medicion': dict(medicion['indicadores'][nombre], alcance=medicion['alcance'], version=medicion['version']),
            'regla': {k: regla[k] for k in ('verde','amarillo','componentes','posible','max_antiguedad_min','validacion') if k in regla},
        }
    return {'indicadores':salida}
