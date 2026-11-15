import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { ANALITOS, puntosSerie, comparar, diaDesdeLanzamiento, csvSerie } from '../frontend/js/nasa-datos.js';

const datos = JSON.parse(await readFile(new URL('../data/nasa_osd575.json', import.meta.url), 'utf8'));

test('el explorador expone las 20 series del contrato existente sin modificar el dataset', () => {
  const original = JSON.stringify(datos);
  for (const id of ['C001', 'C002', 'C003', 'C004']) {
    for (const analito of Object.keys(ANALITOS)) {
      const puntos = puntosSerie(datos, id, analito);
      assert.deepEqual(puntos.map(p => p.momento), datos.momentos);
      for (const p of puntos) assert.equal(p.valor, datos.tripulantes[id][analito].valores[p.momento]);
      assert.equal(csvSerie(datos, id, analito).split('\r\n').length, datos.momentos.length + 1);
    }
  }
  assert.equal(JSON.stringify(datos), original);
});

test('la escala temporal respeta el regreso al día 3 y los intervalos irregulares', () => {
  assert.equal(diaDesdeLanzamiento('L-92'), -92);
  assert.equal(diaDesdeLanzamiento('R+1'), 4);
  assert.equal(diaDesdeLanzamiento('R+194'), 197);
  assert.equal(diaDesdeLanzamiento('otra etiqueta'), null);
});

test('un faltante o un texto no se convierten en cero ni en una comparación válida', () => {
  const parcial = { momentos: ['L-3', 'R+1', 'R+45'], tripulantes: { C001: { glucosa: {
    unidad: 'mg/dL', valores: { 'L-3': 0, 'R+1': null, 'R+45': '85' },
  } } } };
  assert.deepEqual(puntosSerie(parcial, 'C001', 'glucosa').map(p => p.valor), [0, null, null]);
  assert.equal(comparar(parcial.tripulantes.C001.glucosa, 'L-3', 'R+1'), null);
  assert.match(csvSerie(parcial, 'C001', 'glucosa'), /"R\+1","Después del regreso","","mg\/dL"/);
});

test('la diferencia usa las dos muestras elegidas, conserva valores inusuales y no altera el estado', () => {
  const serie = datos.tripulantes.C003.glucosa;
  assert.equal(comparar(serie, 'L-3', 'R+1').diferencia, serie.valores['R+1'] - serie.valores['L-3']);
  assert.equal(puntosSerie(datos, 'C002', 'glucosa').find(p => p.momento === 'R+45').valor, 44);
  assert.equal(comparar({ valores: { a: 0, b: 4 } }, 'a', 'b').porcentaje, null);
});
