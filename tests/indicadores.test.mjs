import test from 'node:test';
import assert from 'node:assert/strict';
import { colorOrgano, historial } from '../frontend/js/organos.js';
import { graficaRegistro } from '../frontend/js/graficas-registros.js';

test('cerebro requiere sueño, ánimo y estrés; una alerta conocida no se oculta por un faltante', () => {
  const estado={indicadores:['sueno','animo','estres'].map(indicador=>({indicador,color:'verde',calidad:'vigente'}))};
  assert.equal(colorOrgano(estado,'cerebro'),'verde');
  estado.indicadores[2].calidad='ausente';estado.indicadores[2].color='sin dato';
  assert.equal(colorOrgano(estado,'cerebro'),'sin dato');
  estado.indicadores[0].color='amarillo';
  assert.equal(colorOrgano(estado,'cerebro'),'amarillo');
});

test('presión grafica ambos componentes y conserva la separación de muestras sospechosas', () => {
  const p={indicador:'presion_arterial',nombre:'Presión',unidad:'mmHg',calidad:'vigente',motivo:'Prueba',fecha:'2026-01-01T12:00Z',historial:[
    {valor:120,diastolica:80,fecha:'2026-01-01T10:00Z'},
    {valor:1000,diastolica:80,fecha:'2026-01-01T11:00Z',sospechoso:true},
    {valor:122,diastolica:78,fecha:'2026-01-01T12:00Z'},
  ]};
  const html=graficaRegistro(p,'#fff');
  assert.match(html,/Sistólica/);assert.match(html,/Diastólica/);
  assert.match(html,/: 80 mmHg/);assert.match(html,/: 78 mmHg/);
  assert.equal((html.match(/<circle /g)||[]).length,4);
  assert.deepEqual(historial({indicadores:[p]},'presion_arterial'),[120,null,122]);
});
