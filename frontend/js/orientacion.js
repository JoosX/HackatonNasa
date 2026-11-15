import { renderOrientacion } from './orientacion-vista.js';
import { renderEmergencia, avanzarEmergencia } from './emergencia.js';

const dialogo=document.querySelector('#orientacionDialogo');
const selector=document.querySelector('#orientacionSelector');
const contenido=document.querySelector('#orientacionContenido');
let version=0, urgente=false;
let nodo='inicio', recorrido=[];

function mostrarEmergencia(enfocar=false) {
  contenido.innerHTML=renderEmergencia(nodo,recorrido);
  if(enfocar)contenido.querySelector('#emergenciaPregunta').focus();
}

async function json(url) {
  try {const r=await fetch(url,{signal:AbortSignal.timeout(5000)});return r.ok?await r.json():null;} catch{return null;}
}
let biblioteca=json('/api/orientacion');

async function cargar() {
  // La emergencia se muestra inmediatamente incluso si la API o la IA fallan.
  if(urgente) {++version;mostrarEmergencia();return;}
  const actual=++version, nombre=selector.value;
  contenido.textContent='Consultando guías y registro del servidor local…';
  const [b,estado]=await Promise.all([biblioteca,urgente?Promise.resolve(null):json('/api/estado/A1')]);
  if(actual!==version)return;
  if(!b?.indicadores?.[nombre]) {
    contenido.innerHTML='<p>No se pudo abrir la biblioteca local. Revisa que el servidor esté activo y reintenta.</p><button type="button" class="btn" id="orientacionReintentar">Reintentar biblioteca</button>';
    return;
  }
  const i=estado?.indicadores?.find(i=>i.indicador===nombre)??{calidad:'error'};
  contenido.innerHTML=renderOrientacion(b.indicadores[nombre],i,{urgente});
}

function abrir(nombre='pulso',esUrgente=false) {
  if(!Array.from(selector.options).some(o=>o.value===nombre))return;
  selector.value=nombre;
  urgente=esUrgente;
  nodo='inicio';recorrido=[];
  selector.closest('label').hidden=urgente;
  document.querySelector('#orientacionRevision').hidden=urgente;
  document.querySelector('#orientacionUrgente').hidden=!urgente;
  document.querySelector('#orientacionTitulo').textContent=urgente?'Orientación urgente':'Medir, comprender y actuar';
  const registro=document.querySelector('#registroDialogo');
  if(registro.open)registro.close();
  if(!dialogo.open)dialogo.showModal();
  dialogo.scrollTop=0;
  cargar();
}

document.querySelector('#abrirUrgente').addEventListener('click',()=>abrir('pulso',true));
document.addEventListener('click',ev=>{
  const urgente=ev.target.closest('[data-abrir-urgente]');
  if(urgente) {abrir(urgente.dataset.abrirUrgente,true);return;}
  const b=ev.target.closest('[data-orientacion]');
  if(b)abrir(b.dataset.orientacion);
});
selector.addEventListener('change',cargar);
contenido.addEventListener('click',ev=>{
  const decision=ev.target.closest('[data-emergencia]');
  if(decision) {
    const siguiente=avanzarEmergencia(nodo,decision.dataset.emergencia);
    if(siguiente!==nodo) {recorrido.push(nodo);nodo=siguiente;mostrarEmergencia(true);}
    return;
  }
  if(ev.target.closest('[data-emergencia-atras]')) {nodo=recorrido.pop()??'inicio';mostrarEmergencia(true);return;}
  if(ev.target.closest('[data-emergencia-reiniciar]')) {nodo='inicio';recorrido=[];mostrarEmergencia(true);return;}
  if(ev.target.closest('#orientacionReintentar')) {biblioteca=json('/api/orientacion');cargar();}
  const b=ev.target.closest('[data-orientacion-registrar]');
  if(!b)return;
  dialogo.close();
  document.dispatchEvent(new CustomEvent('apelogic:abrir-registro',{detail:{indicador:b.dataset.orientacionRegistrar}}));
});
dialogo.addEventListener('close',()=>{++version;nodo='inicio';recorrido=[];contenido.replaceChildren();});
