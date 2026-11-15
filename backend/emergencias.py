"""Detección conservadora de expresiones explícitas; no es un clasificador clínico."""
import re
import unicodedata

FUENTE = 'https://www.resus.org.uk/professional-library/2025-resuscitation-guidelines/adult-basic-life-support-guidelines'


def expresion_urgente(texto):
    t = ''.join(c for c in unicodedata.normalize('NFD', texto.lower()) if unicodedata.category(c) != 'Mn')
    # También puede activar ejemplos o negaciones: deriva al recorrido, nunca diagnostica.
    return bool(re.search(r'dolor (?:en (?:el )?)?pecho|duele (?:el )?pecho|falta de aire|cuesta respirar|no (?:respira|responde)|desmay\w*|desplom\w*|inconsciente|solo jadea', t))


def respuesta_urgente():
    return {
        'modo':'orientacion_urgente', 'alerta_roja':True, 'busqueda':'recorrido_local',
        'respuesta':'Tu mensaje menciona una posible señal urgente. Esto no es un diagnóstico. Si está ocurriendo ahora, avisa de inmediato a la tripulación y activa el protocolo de emergencia de la misión. No esperes al chat ni al enlace con la Tierra. Abre «Orientación urgente» para seguir las preguntas sobre respuesta y respiración. No retrases la ayuda para completar mediciones. Un valor verde no descarta una emergencia.',
        'fuentes':[{'guia':'Resuscitation Council UK — soporte vital básico adulto 2025', 'seccion':'Reconocimiento y aviso temprano (referencia terrestre)', 'fuente':'RCUK; adaptación del equipo pendiente de revisión médica', 'url':FUENTE, 'version':'2025', 'relevancia':1.0}],
    }
