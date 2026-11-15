import test from 'node:test';
import assert from 'node:assert/strict';
import { NODOS, avanzarEmergencia, renderEmergencia } from '../frontend/js/emergencia.js';

test('colapso y jadeos llegan a reanimación sin consultar datos ni chat',()=>{
  let n=avanzarEmergencia('inicio','respiracion');
  n=avanzarEmergencia(n,'reanimacion');
  const html=renderEmergencia(n,['inicio','respiracion']);
  assert.match(html,/Inicia reanimación cardiopulmonar/);
  assert.match(html,/microgravedad/);
  assert.doesNotMatch(html,/Registrar medición|normalidad|fetch\(/);
});
test('las dudas no producen tranquilidad ni se convierten en dato normal',()=>{
  assert.ok(NODOS.inicio.opciones.some(([t,n])=>t==='No estoy seguro'&&n==='respiracion'));
  assert.ok(NODOS.respiracion.opciones.some(([t,n])=>t==='No puedo confirmarlo'&&n==='reanimacion'));
  assert.ok(NODOS.sintomas.opciones.some(([t,n])=>t==='No estoy seguro'&&n==='alerta'));
});
test('persona consciente con dolor recibe ayuda aunque el panel esté verde',()=>{
  assert.equal(avanzarEmergencia(avanzarEmergencia('inicio','sintomas'),'alerta'),'alerta');
  assert.match(renderEmergencia('alerta'),/Un valor en rango no descarta/);
  assert.equal(avanzarEmergencia('alerta','respiracion'),'respiracion');
});
test('cada transición existe y los estados finales permiten reiniciar',()=>{
  for(const [id,n] of Object.entries(NODOS)) {
    for(const [,destino] of n.opciones??[])assert.ok(NODOS[destino]);
    const html=renderEmergencia(id,['inicio']);
    assert.match(html,/data-emergencia-atras/);
    if(id!=='inicio')assert.match(html,/data-emergencia-reiniciar/);
    assert.match(html,/pendiente de revisión médica/);
  }
  assert.equal(avanzarEmergencia('inicio','reanimacion'),'inicio');
});
