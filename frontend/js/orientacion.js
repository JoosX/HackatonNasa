// Orientación: recorrido de emergencia (árbol de decisión) y "medir, comprender y actuar" por indicador.
// Autor original: Romario (rama romario/orientacion-fundamentada); integrado con el registro de esta versión.
// El recorrido de emergencia funciona aunque fallen el servidor, la IA o el enlace con la Tierra.
import { renderOrientacion } from './orientacion-vista.js';
import { renderEmergencia, avanzarEmergencia } from './emergencia.js';
import { L } from './i18n.js';

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
  contenido.textContent=L('Consultando guías y registro del servidor local…','Checking guides and records on the local server…');
  const [b,estado]=await Promise.all([biblioteca,urgente?Promise.resolve(null):json('/api/estado/A1')]);
  if(actual!==version)return;
  if(!b?.indicadores?.[nombre]) {
    contenido.innerHTML=`<p>${L('No se pudo abrir la biblioteca local. Revisa que el servidor esté activo y reintenta.','The local library could not be opened. Check that the server is running and try again.')}</p><button type="button" class="btn" id="orientacionReintentar">${L('Reintentar biblioteca','Retry library')}</button>`;
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
  document.querySelector('#orientacionTitulo').textContent=urgente?L('Orientación urgente','Urgent guidance'):L('Medir, comprender y actuar','Measure, understand and act');
  const registro=document.querySelector('#dlgRegistro');
  if(registro?.open)registro.close();
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
  window.abrirRegistro?.(b.dataset.orientacionRegistrar);
});
window.abrirOrientacion=abrir;   // para el chat y otros módulos
dialogo.addEventListener('close',()=>{++version;nodo='inicio';recorrido=[];contenido.replaceChildren();});
