import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient
from backend.main import app
import mediciones
import rag


def guardar(indicador, valor, minutos=0, **extra):
    return mediciones.guardar(mediciones.Medicion(id=str(uuid.uuid4()), indicador=indicador, valor=valor,
        fecha=dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=minutos), **extra))


CASOS = [('pulso',82,{}), ('presion_arterial',120,{'diastolica':80}), ('oxigeno',98,{}),
         ('glucosa',85,{'contexto':'ayunas'}), ('temperatura',36.7,{}), ('sueno',7,{}), ('animo',4,{}), ('estres',2,{})]


@pytest.mark.parametrize('nombre,valor,extra', CASOS)
def test_cada_indicador_usa_su_registro_y_no_un_ejemplo(nombre,valor,extra):
    guardar(nombre,valor,**extra)
    p = mediciones.estado_indicador('A1',nombre)
    assert p['color'] == 'verde' and p['calidad'] == 'vigente'
    assert p['origen'] == 'registro_manual' and p['regla_ilustrativa'] is True
    assert p['historial'][0]['valor'] == valor
    if nombre == 'presion_arterial':
        assert p['valor'] == '120/80' and p['historial'][0]['diastolica'] == 80
    else:
        assert p['valor'] == valor


@pytest.mark.parametrize('nombre,valor,extra', CASOS)
def test_cada_indicador_sin_datos_o_con_muestra_antigua_se_muestra_gris(nombre,valor,extra):
    assert mediciones.estado_indicador('A1',nombre)['calidad'] == 'ausente'
    guardar(nombre,valor,minutos=3000,**extra)
    p = mediciones.estado_indicador('A1',nombre)
    assert p['color'] == 'sin dato' and p['calidad'] == 'vencido'
    assert p['historial'][0]['valor'] == valor


@pytest.mark.parametrize('sistolica,diastolica,color', [(120,80,'verde'),(120,95,'amarillo'),(120,105,'rojo'),(170,80,'rojo')])
def test_presion_considera_ambos_componentes(sistolica,diastolica,color):
    guardar('presion_arterial',sistolica,diastolica=diastolica)
    assert mediciones.estado_indicador('A1','presion_arterial')['color'] == color


@pytest.mark.parametrize('contexto', ['sin_especificar','despues_comida','reposo'])
def test_glucosa_no_aplica_un_rango_de_ayunas_a_otro_contexto(contexto):
    guardar('glucosa',85,contexto=contexto)
    p = mediciones.estado_indicador('A1','glucosa')
    assert p['calidad'] == 'contexto_pendiente' and p['color'] == 'sin dato'
    texto,_ = rag.resumen_estado({'indicadores':[p]})
    assert 'No puedo afirmar' in texto


def test_valor_sospechoso_no_oculta_su_historial_ni_se_usa_para_clasificar():
    guardar('temperatura',36.7,minutos=2)
    guardar('temperatura',100)
    p = mediciones.estado_indicador('A1','temperatura')
    assert p['valor'] == 100 and p['color'] == 'sin dato' and p['calidad'] == 'sospechoso'
    assert [m['sospechoso'] for m in p['historial']] == [False,True]


def test_api_y_ori_usan_los_ocho_registros_actuales(monkeypatch):
    for nombre,valor,extra in CASOS: guardar(nombre,valor,**extra)
    cliente = TestClient(app)
    estado = cliente.get('/api/estado/A1').json()
    propios = estado['indicadores'][:8]
    assert all(i['calidad'] == 'vigente' for i in propios)
    assert {i['indicador'] for i in propios} == set(mediciones.CATALOGO)
    assert all(i['valor'] is None for i in estado['indicadores'][8:-1])
    captura = {}
    def responder(pregunta,estado): captura.update(estado); return {'respuesta':'ok'}
    monkeypatch.setattr(rag,'responder',responder)
    r = cliente.post('/api/chat',json={'pregunta':'cómo estoy', 'estado':{'indicadores':[{'indicador':'oxigeno','valor':50,'color':'rojo'}]}})
    assert r.status_code == 200
    assert next(i for i in captura['indicadores'] if i['indicador']=='oxigeno')['valor'] == 98
    texto,_ = rag.resumen_estado({'indicadores':propios})
    assert '120/80' in texto and '98' in texto and 'Estrés' in texto
    assert 'rango ilustrativo' in texto
