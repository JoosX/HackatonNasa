import test from 'node:test';
import assert from 'node:assert/strict';
import { colorOrgano, historial } from '../frontend/js/organos.js';

test('el corazón representa el pulso local y no la presión demo', () => {
  const estado = { indicadores: [
    { indicador:'pulso', valor:82, color:'verde', calidad:'vigente', historial:[{valor:74},{valor:82}] },
    { indicador:'presion_arterial', color:'rojo', origen:'demo' },
  ] };
  assert.equal(colorOrgano(estado,'corazon'), 'verde');
  assert.deepEqual(historial(estado,'pulso'), [74,82]);
  estado.indicadores[0].calidad = 'vencido'; estado.indicadores[0].color = 'sin dato';
  assert.equal(colorOrgano(estado,'corazon'), 'sin dato');
});

test('no se fabrican puntos cuando no hay pulso registrado', () => {
  const estado = { indicadores:[{indicador:'pulso',valor:null,color:'sin dato',calidad:'ausente',historial:[]}] };
  assert.deepEqual(historial(estado,'pulso'), []);
  estado.indicadores[0].historial = [{valor:74},{valor:10000,sospechoso:true}];
  assert.deepEqual(historial(estado,'pulso'), [74,null]);
});
