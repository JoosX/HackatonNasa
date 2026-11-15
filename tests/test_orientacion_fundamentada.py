import json
import pytest
from guias import RAIZ, cargar_fragmentos
from orientacion import biblioteca
import rag


@pytest.mark.parametrize('nombre', ['pulso','presion_arterial','oxigeno','glucosa','temperatura','sueno','animo','estres'])
def test_medicion_y_limites_trazables(nombre):
    g=biblioteca()['indicadores'][nombre]
    m=g['medicion']
    assert all(m[c] for c in ('preparacion','errores','sin_equipo','alcance'))
    assert len(m['pasos'])>=3
    assert m['fuente']['url'].startswith('https://')
    assert not g['regla']['validacion']['aprobado_para_uso_clinico']
    assert g['regla']['validacion']['estado']=='pendiente_revision_medica'


@pytest.mark.parametrize('pregunta',['Me duele el pecho','Mi compañero no responde y solo jadea','Me cuesta respirar','Se desplomó','Tuvo un desmayo'])
def test_sintomas_priorizan_ayuda_sin_ollama_ni_busqueda(monkeypatch,pregunta):
    def prohibido(*a,**k): raise AssertionError('No debe esperar a búsqueda o IA')
    monkeypatch.setattr(rag,'buscar',prohibido)
    r=rag.responder(pregunta,{'indicadores':[{'indicador':'pulso','valor':80,'color':'verde'}]})
    assert r['modo']=='orientacion_urgente'
    assert r['alerta_roja']
    assert 'No esperes al chat' in r['respuesta']
    assert r['fuentes'][0]['url'].startswith('https://www.resus.org.uk/')


def test_un_indice_antiguo_no_devuelve_consejos_retirados(tmp_path,monkeypatch):
    actual=cargar_fragmentos()
    anterior=[dict(f,vector=[1]) for f in actual]
    anterior[0]['texto']='Consejo antiguo no vigente'
    ruta=tmp_path/'indice.json'
    ruta.write_text(json.dumps({'fragmentos':anterior}),encoding='utf-8')
    monkeypatch.setattr(rag,'INDICE',ruta)
    rag.recargar()
    try:
        assert rag._fragmentos()==actual
        assert all('vector' not in f for f in rag._fragmentos())
    finally: rag.recargar()


def test_no_esperas_clinicas_inventadas_en_las_acciones():
    reglas=json.loads((RAIZ/'data/reglas.json').read_text(encoding='utf-8'))
    assert all('15 minutos' not in str(r['accion']) and '30 minutos' not in str(r['accion']) for r in reglas['indicadores'])
    assert 'no validan límites de alarma' in biblioteca()['indicadores']['glucosa']['regla']['validacion']['nota']
