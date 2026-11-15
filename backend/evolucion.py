"""Cambios descriptivos de registros manuales; sin inferencia clínica ni referencia normal."""
import datetime as dt
import math


def describir(indicador, ahora, truncado=False):
    nombre = indicador['indicador']
    if nombre not in ('pulso','sueno'):
        return None
    inicio = ahora - dt.timedelta(days=7)
    validos, sospechosos, fuera, futuras = [], 0, 0, 0
    for m in indicador.get('historial',[]):
        try:
            fecha = dt.datetime.fromisoformat(m['fecha'])
            if fecha.utcoffset() is None:
                continue
            fecha = fecha.astimezone(dt.timezone.utc)
        except (KeyError, ValueError, TypeError):
            continue
        if fecha > ahora:
            futuras += 1
            continue
        if fecha < inicio:
            fuera += 1
            continue
        if m.get('sospechoso') or not isinstance(m.get('valor'), (float,int)) or not math.isfinite(m['valor']):
            sospechosos += 1
            continue
        validos.append({**m, 'fecha':fecha.isoformat(), '_fecha':fecha})
    validos.sort(key=lambda m:m['_fecha'])
    avisos = []
    if truncado:
        avisos.append('Solo se analizaron los últimos 100 registros; la ventana puede estar incompleta.')
    if sospechosos:
        avisos.append(f'{sospechosos} registros sospechosos o inválidos excluidos de la comparación.')
    if futuras:
        avisos.append(f'{futuras} registros con fecha futura no se utilizaron.')
    seleccion = validos[-2:]
    repetidos, huecos = 0, 0
    if nombre == 'sueno':
        diarios = {}
        for m in validos:
            diarios[m['_fecha'].date()] = m
        seleccion = list(diarios.values())
        repetidos = len(validos)-len(seleccion)
        if repetidos:
            avisos.append(f'{repetidos} {"registro adicional del mismo día UTC no se sumó" if repetidos==1 else "registros adicionales del mismo día UTC no se sumaron"}: se usa el último de cada día.')
        if len(seleccion)>1:
            huecos = (seleccion[-1]['_fecha'].date()-seleccion[0]['_fecha'].date()).days+1-len(seleccion)
            if huecos:
                avisos.append(f'Hay {huecos} días UTC sin registro entre la primera y la última fecha; no se asume continuidad.')
        avisos.append('Días agrupados en UTC; pueden diferir de la fecha local. No se verifican dispositivo ni método de estimación.')
    if indicador.get('calidad') == 'vencido':
        avisos.append('La última medición está vencida: esta comparación es histórica y no describe el estado actual.')
    resultado = {
        'ventana_dias':7, 'max_registros':100, 'registros_validos':len(validos),
        'registros_ventana':len(validos)+sospechosos, 'muestras_usadas':len(seleccion),
        'sospechosos_excluidos':sospechosos, 'fuera_ventana':fuera, 'repetidos_dia':repetidos,
        'dias_sin_registro':huecos if nombre=='sueno' else None,
        'metodo':'Último registro de cada día UTC; cambio entre los dos últimos días registrados.' if nombre=='sueno' else 'Diferencia entre las dos últimas lecturas válidas, sin ajustar por contexto.',
        'estado':'insuficiente', 'resumen':'Faltan dos días distintos con registro para comparar.' if nombre=='sueno' else 'Faltan dos lecturas válidas con horas distintas para comparar.',
        'advertencias':avisos, 'comparacion':None,
        'muestras':[{'fecha':m['fecha'],'valor':m['valor'],'contexto':m.get('contexto','sin_especificar')} for m in seleccion],
    }
    if indicador.get('calidad') in ('ausente','error','sospechoso'):
        resultado['resumen']='No se calcula un cambio actual: la última medición está ausente, es sospechosa o no pudo consultarse.'
        return resultado
    if len(seleccion)<2:
        return resultado
    anterior, ultima = seleccion[-2:]
    if anterior['_fecha']==ultima['_fecha']:
        resultado['resumen']='Las dos últimas lecturas tienen la misma hora; no se puede establecer su secuencia temporal.'
        return resultado
    if nombre=='pulso':
        ca, cb = anterior.get('contexto','sin_especificar'), ultima.get('contexto','sin_especificar')
        if ca != cb:
            avisos.append('Las condiciones registradas son distintas; la diferencia no se interpreta como una tendencia comparable.')
        if 'sin_especificar' in (ca,cb):
            avisos.append('Falta especificar el contexto de alguna lectura; no se asume que ambas fueron en reposo.')
    delta = round(ultima['valor']-anterior['valor'],6)
    resultado['estado']='comparacion'
    resultado['comparacion']={'anterior':{'fecha':anterior['fecha'],'valor':anterior['valor']},'ultima':{'fecha':ultima['fecha'],'valor':ultima['valor']},'diferencia':delta,'unidad':indicador['unidad']}
    if nombre=='sueno':
        valores=', '.join(f"{m['valor']:g} h ({m['_fecha'].date().isoformat()} UTC)" for m in seleccion)
        resultado['resumen']=f'Registros diarios seleccionados: {valores}. Cambio entre los dos últimos días registrados: {delta:+g} h.'
    else:
        resultado['resumen']=f"Pulso: {anterior['valor']:g} → {ultima['valor']:g} lpm. Diferencia entre estas dos lecturas: {delta:+g} lpm."
    return resultado
