import {config,organos} from './config.js';
import {obtenerEstado,obtenerFichas,cambiarEstadoDemo} from './api.js';
import {normalizarEstado} from './estado.js';
import {validarFichas} from './contratos.js';
import {mostrarFicha} from './fichas.js';
import {crearVisor2d} from './cuerpo2d.js';
import {iniciarChat} from './chat.js';
import {iniciarSenal} from './senal.js';

let visor3d,visor2d,estado={},fichas=[],selected='corazon',view='3d',modelImported=false,updating=false;
const status=document.querySelector('#viewer-status');
function seleccionar(id){
 if(!Object.hasOwn(organos,id))return;
 selected=id;mostrarFicha(id,fichas,estado);visor3d?.seleccionar(id);visor2d?.seleccionar(id);
 for(const button of document.querySelectorAll('#organ-buttons button'))button.setAttribute('aria-pressed',String(button.dataset.id===id));
}
function aplicar(){visor3d?.actualizar(estado);visor2d?.actualizar(estado);seleccionar(selected);}
function setView(mode){
 const use3d=mode==='3d'&&!!visor3d;view=use3d?'3d':'2d';
 document.querySelector('#visor3d').hidden=!use3d;document.querySelector('#visor2d').hidden=use3d;
 document.querySelector('#view-3d').setAttribute('aria-pressed',String(use3d));
 document.querySelector('#view-2d').setAttribute('aria-pressed',String(!use3d));
 document.querySelector('#reset-camera').hidden=!use3d;visor3d?.setVisible(use3d);
 document.querySelector('#model-label').textContent=use3d&&modelImported?'MODELO IMPORTADO':'MODELO ESQUEMÁTICO';
}
for(const [id,label] of Object.entries(organos)){
 const button=document.createElement('button');button.textContent=label;button.dataset.id=id;
 button.addEventListener('click',()=>seleccionar(id));document.querySelector('#organ-buttons').append(button);
}
iniciarChat();iniciarSenal();seleccionar(selected);
if(config.mode!=='demo'){
 document.querySelector('#mode-label').textContent='Modo API real · El modelo inicial sigue siendo esquemático.';
 document.querySelector('.controls').hidden=true;document.querySelector('#error-control').hidden=true;
 document.querySelector('#chat-kind').textContent='LOCAL';document.querySelector('#local-status').textContent='Asistente local: pendiente de consulta';
}
const dataStatus=document.createElement('p');dataStatus.className='hint padded';dataStatus.setAttribute('role','status');
document.querySelector('#organ-buttons').before(dataStatus);
async function actualizarDatos(){
 if(updating)return;updating=true;
 try{
  const results=await Promise.allSettled([obtenerEstado(),obtenerFichas()]);
  const errors=[];
  try{if(results[0].status==='rejected')throw results[0].reason;estado=normalizarEstado(results[0].value);}catch{estado={};errors.push('Estado no disponible: se muestran órganos sin datos.');}
  try{if(results[1].status==='rejected')throw results[1].reason;fichas=validarFichas(results[1].value);}catch{fichas=[];errors.push('Fichas no disponibles o con formato incorrecto.');}
  dataStatus.textContent=errors.join(' ');dataStatus.hidden=!errors.length;aplicar();
 }finally{updating=false;}
}
// El visor arranca sin esperar una API lenta o desconectada.
void actualizarDatos();
const svgReady=crearVisor2d(document.querySelector('#visor2d'),seleccionar)
 .then(value=>{visor2d=value;aplicar();})
 .catch(()=>{document.querySelector('#view-2d').disabled=true;status.textContent='SVG no disponible; usa los botones de órganos.';});
document.querySelector('#view-3d').disabled=true;
document.querySelector('#model-file').disabled=true;
document.querySelector('#view-3d').addEventListener('click',()=>setView('3d'));
document.querySelector('#view-2d').addEventListener('click',()=>setView('2d'));
document.querySelector('#reset-camera').addEventListener('click',()=>visor3d?.reset());
try{
 const {crearVisor}=await import('./cuerpo3d.js');
 visor3d=crearVisor(document.querySelector('#visor3d'),seleccionar,message=>{
  setView('2d');document.querySelector('#view-3d').disabled=true;document.querySelector('#model-file').disabled=true;status.textContent=message;
 });
 document.querySelector('#view-3d').disabled=false;document.querySelector('#model-file').disabled=false;
 setView(view);aplicar();status.textContent='Arrastra para rotar · Rueda para zoom · Clic para explorar';
}catch(error){
 console.error('Visor 3D:',error);setView('2d');
 status.textContent='3D no disponible. Puedes usar el cuerpo 2D o los botones de órganos.';
}
await svgReady;
async function updateDemo(){
 cambiarEstadoDemo(document.querySelector('#demo-color').value,document.querySelector('#demo-pulse').value);
 document.querySelector('#pulse-output').textContent=document.querySelector('#demo-pulse').value+' lpm';
 estado=normalizarEstado(await obtenerEstado());aplicar();
}
document.querySelector('#demo-color').addEventListener('change',updateDemo);
document.querySelector('#demo-pulse').addEventListener('input',updateDemo);
document.querySelector('#model-file').addEventListener('change',async event=>{
 const input=event.target,file=input.files[0];if(!file||!visor3d)return;
 if(!file.name.toLowerCase().endsWith('.glb')){status.textContent='Selecciona un archivo .glb.';input.value='';return;}
 if(file.size>30*1024*1024){status.textContent='El modelo supera 30 MB. Para esta demo usa un GLB optimizado (ideal: menos de 5 MB).';input.value='';return;}
 const url=URL.createObjectURL(file);input.disabled=true;status.textContent='Cargando modelo…';
 try{
  const faltantes=await visor3d.cargarModelo(url);modelImported=true;
  status.textContent=faltantes.length?'Modelo cargado. Nombres pendientes: '+faltantes.join(', '):'Modelo cargado con todos los nombres acordados.';
  setView('3d');aplicar();
 }catch(error){status.textContent='No se pudo usar el modelo: '+error.message;}
 finally{URL.revokeObjectURL(url);input.disabled=false;input.value='';}
});
if(config.mode==='real')setInterval(actualizarDatos,15000);

