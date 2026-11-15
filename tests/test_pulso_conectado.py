import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient
from backend.main import app
import mediciones
import rag


def guardar(valor, minutos=0, persona='A1'):
    m = mediciones.Medicion(id=str(uuid.uuid4()), astronauta_id=persona, indicador='pulso', valor=valor,
        fecha=dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=minutos), nota='PRUEBA FICTICIA')
    return mediciones.guardar(m)


@pytest.mark.parametrize('valor,color', [(74,'verde'),(110,'amarillo'),(150,'rojo')])
def test_pulso_actual_usa_las_reglas_existentes(valor,color):
    guardar(valor)
    p = mediciones.estado_pulso('A1')
    assert p['valor'] == valor and p['color'] == color
    assert p['calidad'] == 'vigente' and p['regla_ilustrativa'] is True
    assert len(p['historial']) == 1


def test_no_hay_pulso_ficticio_ni_datos_de_otra_persona():
    guardar(74, persona='A2')
    p = mediciones.estado_pulso('A1')
    assert p['calidad'] == 'ausente' and p['valor'] is None and p['color'] == 'sin dato'


def test_edad_se_recalcula_sin_reemplazar_un_valor_sospechoso_por_otro_bueno():
    m = guardar(74, minutos=10)
    p = mediciones.estado_pulso('A1', dt.datetime.fromisoformat(m['fecha'])+dt.timedelta(minutes=241))
    assert p['calidad'] == 'vencido' and p['color'] == 'sin dato'
    guardar(10000)
    p = mediciones.estado_pulso('A1')
    assert p['calidad'] == 'sospechoso' and p['color'] == 'sin dato'
    assert p['valor'] == 10000 and p['historial'][-1]['sospechoso'] is True


def test_orden_depende_de_la_medicion_y_no_del_momento_de_ingreso():
    guardar(80, minutos=5)
    guardar(70, minutos=30)
    p = mediciones.estado_pulso('A1')
    assert p['valor'] == 80
    assert [m['valor'] for m in p['historial']] == [70,80]


def test_ori_no_afirma_normalidad_con_un_pulso_vencido():
    guardar(74, minutos=300)
    p = mediciones.estado_pulso('A1')
    texto, _ = rag.resumen_estado({'indicadores':[p, {'indicador':'oxigeno','valor':97,'color':'verde','origen':'demo'}]})
    assert 'No puedo afirmar' in texto and 'vencida' in texto
    assert 'Todos tus indicadores' not in texto


def test_resumen_muestra_el_valor_registrado_sin_evaluar_datos_demo():
    guardar(82)
    p = mediciones.estado_pulso('A1')
    texto, _ = rag.resumen_estado({'indicadores':[p, {'indicador':'oxigeno','valor':50,'color':'rojo','origen':'demo'}]})
    assert '82 lpm' in texto and 'rango ilustrativo' in texto
    datos, rojo = rag.resumir_estado({'indicadores':[p, {'indicador':'oxigeno','valor':50,'color':'rojo','origen':'demo'}]})
    assert '82' in datos and '50' not in datos and rojo is False


def test_chat_recarga_el_pulso_guardado_aunque_el_cliente_envie_un_valor_antiguo(monkeypatch):
    guardar(83)
    captura = {}
    def responder(pregunta, estado):
        captura.update(estado)
        return {'respuesta':'ok'}
    monkeypatch.setattr(rag, 'responder', responder)
    cliente = TestClient(app)
    r = cliente.post('/api/chat',json={'pregunta':'cómo estoy','estado':{'indicadores':[{'indicador':'pulso','valor':10,'color':'rojo'}]}})
    assert r.status_code == 200
    assert captura['indicadores'][0]['valor'] == 83
    estado = cliente.get('/api/estado/A1').json()
    assert estado['indicadores'][0]['valor'] == 83
    assert all(i['origen'] == 'demo' for i in estado['indicadores'][1:-1])
