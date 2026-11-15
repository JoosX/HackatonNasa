import pytest
from fastapi.testclient import TestClient
from backend.main import app
import ollama_cliente
from orientacion import biblioteca
from mediciones import CATALOGO
from guias import CARPETA_GUIAS, leer_guia, fragmentar


@pytest.mark.parametrize('nombre', list(CATALOGO))
def test_todos_los_indicadores_tienen_medicion_fuente_y_revision(nombre):
    g=biblioteca()['indicadores'][nombre]
    for campo in ('equipo','como_medir','por_que','cuando_avisar','archivo','version','fuente','estado_revision'):
        assert g[campo]
    assert 'ilustrativo' in g['estado_revision']
    assert g['url'].startswith('https://')
    assert 'no es un protocolo oficial NASA' in g['autor_contenido']


def test_api_no_necesita_ollama(monkeypatch):
    def no_llamar(*a,**k): raise AssertionError('La biblioteca no debe invocar la IA')
    monkeypatch.setattr(ollama_cliente,'chatear',no_llamar)
    monkeypatch.setattr(ollama_cliente,'embeber',no_llamar)
    r=TestClient(app).get('/api/orientacion')
    assert r.status_code==200
    assert set(r.json()['indicadores'])==set(CATALOGO)


def test_pasos_y_aviso_conservan_el_texto_de_las_guias_locales():
    for g in biblioteca()['indicadores'].values():
        meta,cuerpo=leer_guia(CARPETA_GUIAS/g['archivo'])
        secciones={f['seccion']:f['texto'] for f in fragmentar(meta,cuerpo)}
        assert all(p in secciones['Qué hacer'] for p in g['pasos_guia'])
        assert g['cuando_avisar']==secciones['Cuándo avisar']
        assert g['version']==meta['version']
