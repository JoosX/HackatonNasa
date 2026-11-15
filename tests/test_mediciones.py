import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient
from backend.main import app
import mediciones


@pytest.fixture
def cliente_registro(tmp_path, monkeypatch):
    monkeypatch.setenv("APELOGIC_DB_PATH", str(tmp_path / "registros.sqlite3"))
    return TestClient(app)


def registro(**cambios):
    return {"id": str(uuid.uuid4()), "astronauta_id": "A1", "indicador": "pulso", "valor": 72,
            "fecha": "2026-01-01T12:00:00-05:00", "contexto": "reposo", "nota": "Prueba ficticia", **cambios}


def test_guarda_persiste_y_no_duplica_al_reintentar(cliente_registro):
    m = registro()
    assert cliente_registro.post('/api/mediciones', json=m).status_code == 201
    assert cliente_registro.post('/api/mediciones', json=m).status_code == 201
    # Nueva conexión SQLite: el dato no depende de la memoria del proceso ni del navegador.
    d = mediciones.historial('A1')
    assert d['total'] == 1
    assert d['mediciones'][0]['fecha'] == '2026-01-01T17:00:00+00:00'
    assert d['mediciones'][0]['unidad'] == 'lpm'
    assert cliente_registro.post('/api/mediciones', json={**m, 'valor':80}).status_code == 409


def test_presion_ambos_valores_filtro_orden_y_separacion(cliente_registro):
    for m in [registro(), registro(indicador='presion_arterial', valor=122, diastolica=78), registro(astronauta_id='A2')]:
        assert cliente_registro.post('/api/mediciones', json=m).status_code == 201
    d = cliente_registro.get('/api/historial/A1?indicador=presion_arterial').json()
    assert d['total'] == 1 and d['mediciones'][0]['diastolica'] == 78
    assert cliente_registro.get('/api/historial/A1?limite=1').json()['total'] == 2
    assert len(cliente_registro.get('/api/historial/A1?limite=1&offset=1').json()['mediciones']) == 1
    assert cliente_registro.get('/api/historial/A3').json()['total'] == 0


@pytest.mark.parametrize('cambio', [
    {'valor': -1}, {'indicador': 'oxigeno', 'valor':101}, {'indicador':'sueno','valor':25},
    {'indicador':'animo','valor':2.5}, {'indicador':'estres','valor':6},
    {'indicador':'presion_arterial','valor':80,'diastolica':120},
    {'indicador':'presion_arterial','valor':120}, {'diastolica':80},
    {'fecha':'2026-01-01T12:00:00'}, {'fecha':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=1)).isoformat()},
    {'indicador':'radiacion'}, {'nota':'x'*1001},
])
def test_rechaza_entradas_invalidas_sin_guardar(cliente_registro, cambio):
    assert cliente_registro.post('/api/mediciones', json=registro(**cambio)).status_code == 422
    assert mediciones.historial('A1')['total'] == 0


def test_paginacion_y_filtros_invalidos(cliente_registro):
    assert cliente_registro.get('/api/historial/A1?limite=101').status_code == 422
    assert cliente_registro.get('/api/historial/A1?indicador=no_existe').status_code == 422
    assert cliente_registro.get('/api/historial/A1?offset=-1').status_code == 422
