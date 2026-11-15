import datetime as dt
import uuid

from evolucion import describir
import mediciones
import rag

AHORA=dt.datetime(2026,11,14,23,0,tzinfo=dt.timezone.utc)


def punto(dia,valor,hora=12,contexto='reposo',**extras):
    return {'fecha':f'2026-11-{dia:02d}T{hora:02d}:00:00+00:00','valor':valor,'contexto':contexto,**extras}


def indicador(nombre,puntos,calidad='vigente'):
    return {'indicador':nombre,'unidad':'h' if nombre=='sueno' else 'lpm','historial':puntos,'calidad':calidad}


def test_sueno_compara_dias_y_no_suma_registros_del_mismo_dia():
    e=describir(indicador('sueno',[punto(12,7),punto(13,6),punto(14,8,hora=8),punto(14,5,hora=12)]),AHORA)
    assert e['registros_validos']==4 and e['muestras_usadas']==3 and e['repetidos_dia']==1
    assert [m['valor'] for m in e['muestras']]==[7,6,5]
    assert e['comparacion']['diferencia']==-1 and e['dias_sin_registro']==0


def test_huecos_no_se_presentan_como_dias_consecutivos():
    e=describir(indicador('sueno',[punto(10,7),punto(14,5)]),AHORA)
    assert e['dias_sin_registro']==3
    assert any('no se asume continuidad' in a for a in e['advertencias'])


def test_pulso_distingue_contextos_y_no_inventa_reposo():
    e=describir(indicador('pulso',[punto(14,72,hora=10),punto(14,105,contexto='despues_ejercicio')]),AHORA)
    assert e['comparacion']['diferencia']==33
    assert any('condiciones' in a for a in e['advertencias'])
    e=describir(indicador('pulso',[punto(14,72,hora=10,contexto='sin_especificar'),punto(14,75)]),AHORA)
    assert any('no se asume' in a for a in e['advertencias'])


def test_una_muestra_horas_iguales_y_ultimo_sospechoso_no_producen_cambio():
    for puntos,calidad in [([punto(14,72)],'vigente'),([punto(14,72),punto(14,74)],'vigente'),([punto(13,72),punto(14,10000,sospechoso=True)],'sospechoso')]:
        e=describir(indicador('pulso',puntos,calidad),AHORA)
        assert e['estado']=='insuficiente' and e['comparacion'] is None


def test_ventana_fechas_futuras_vencimiento_y_limite_son_explicitos():
    e=describir(indicador('pulso',[punto(1,60),punto(13,70),punto(14,75),punto(15,80)],'vencido'),AHORA,truncado=True)
    assert e['fuera_ventana']==1 and e['registros_validos']==2
    assert e['comparacion']['diferencia']==5
    assert any('vencida' in a for a in e['advertencias'])
    assert any('100 registros' in a for a in e['advertencias'])
    assert any('futura' in a for a in e['advertencias'])


def test_cero_no_se_pierde_y_orden_se_basa_en_fecha():
    e=describir(indicador('sueno',[punto(14,0),punto(13,2)]),AHORA)
    assert e['comparacion']['ultima']['valor']==0 and e['comparacion']['diferencia']==-2


def test_dias_utc_son_independientes_del_desfase_original():
    p=[{'fecha':'2026-11-12T23:30:00-05:00','valor':7},{'fecha':'2026-11-13T15:00:00+00:00','valor':6}]
    e=describir(indicador('sueno',p),AHORA)
    assert e['muestras_usadas']==1 and e['repetidos_dia']==1


def test_sqlite_y_ori_reciben_la_misma_comparacion():
    for minutos,valor in [(20,70),(10,75)]:
        mediciones.guardar(mediciones.Medicion(id=str(uuid.uuid4()),indicador='pulso',valor=valor,contexto='reposo',fecha=dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=minutos)))
    i=mediciones.estado_pulso('A1')
    assert i['evolucion']['comparacion']['diferencia']==5
    texto,_=rag.resumen_estado({'indicadores':[i]})
    assert '70 → 75' in texto and 'sin diagnóstico' in texto
    assert 'Cambio histórico' in rag.resumir_estado({'indicadores':[i]})[0]
