import test from 'node:test';
import assert from 'node:assert/strict';
import { renderEvolucion } from '../frontend/js/evolucion.js';

test('la vista conserva límites, conteos, fechas y acceso a la guía',()=>{
  const html=renderEvolucion({nombre:'Sueño',indicador:'sueno',evolucion:{ventana_dias:7,max_registros:100,registros_ventana:4,registros_validos:3,muestras_usadas:2,resumen:'Cambio observado',advertencias:['Hay días sin datos'],metodo:'UTC',comparacion:{anterior:{fecha:'2026-11-12T12:00Z',valor:6},ultima:{fecha:'2026-11-14T12:00Z',valor:5},diferencia:-1,unidad:'h'}}});
  assert.match(html,/4 registros/);assert.match(html,/3 válidos/);assert.match(html,/2 muestras/);
  assert.match(html,/días sin datos/);assert.match(html,/-1 h/);assert.match(html,/data-orientacion="sueno"/);
  assert.match(html,/no identifica causas/);
});

test('sin evolución disponible no se fabrica una comparación',()=>{
  assert.equal(renderEvolucion({indicador:'glucosa'}),'');
});
