import test from 'node:test';
import assert from 'node:assert/strict';
import { siguientePaso, renderOrientacion } from '../frontend/js/orientacion-vista.js';

for(const calidad of ['ausente','vencido','sospechoso','error','contexto_pendiente']) {
  test(`la orientación no afirma normalidad ante ${calidad}`,()=>{
    const paso=siguientePaso({calidad,color:'verde'});
    assert.doesNotMatch(paso.titulo,/dentro del rango/);
    assert.ok(paso.texto.length>20);
  });
}

test('una alerta prioriza avisar sin esperar al chat',()=>{
  const paso=siguientePaso({calidad:'vigente',color:'rojo'});
  assert.match(paso.texto,/Avisa a la tripulación/);
  assert.match(paso.texto,/no esperes/);
});

test('la fuente no permite enlaces ejecutables ni HTML de guías',()=>{
  const g={nombre:'Pulso',indicador:'pulso',equipo:'Kit',como_medir:'<img src=x>',unidad:'lpm',por_que:'Texto',espacio:'Texto',pasos_guia:['<script>'],cuando_avisar:'Avisar',senales:'Síntomas',titulo:'Guía',archivo:'pulso.md',version:'2026',estado_revision:'ilustrativo',autor_contenido:'Adaptación',fuente:'Referencia',url:'javascript:alert(1)'};
  const html=renderOrientacion(g,{calidad:'ausente',valor:null});
  assert.match(html,/Sin dato/);
  assert.match(html,/&lt;img/);
  assert.doesNotMatch(html,/<script>|href="javascript:/);
  assert.match(html,/Fuente de contexto/);
  const urgente=renderOrientacion(g,{calidad:'vigente',color:'verde',valor:80},{urgente:true});
  assert.doesNotMatch(urgente,/Registrar medición|Lectura dentro del rango|80 lpm/);
  assert.match(urgente,/No retrases la ayuda/);
});
