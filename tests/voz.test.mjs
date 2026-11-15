import test from 'node:test';
import assert from 'node:assert/strict';
import { textoParaVoz, resumenEmergencia } from '../frontend/js/voz.js';

test('la voz no lee markdown, emojis ni números de lista', () => {
  const t = textoParaVoz('⚠️ **Qué está pasando**\n- **Pulso: 148 lpm**: rápido.\n1. Avisa a la tripulación.');
  assert.doesNotMatch(t, /\*|⚠|^-|1\./);
  assert.match(t, /Qué está pasando/);
  assert.match(t, /Pulso: 148 lpm/);
});

test('en emergencia lee la primera frase y a quién llamar, no todo el protocolo', () => {
  const protocolo = 'Estoy aquí contigo.\n\n**Qué está pasando**\n- dato\n\n**Llama a alguien ahora**\nDi en voz alta: *«Necesito ayuda médica»*.\n\n**Qué hacer**\n1. paso largo';
  const r = resumenEmergencia(protocolo);
  assert.match(r, /Estoy aquí contigo/);
  assert.match(r, /Necesito ayuda médica/);
  assert.doesNotMatch(r, /paso largo|Qué hacer/);
  assert.match(resumenEmergencia('Stay calm.\n\n**Get help now**\nShout *"Medical emergency!"*.\n\n**What to do**\n1. x'), /Medical emergency/);
});
