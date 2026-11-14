import {config} from './config.js';
import {enviarMensaje} from './api.js';
import {mostrarFuentes} from './fichas.js';
import {validarRespuesta} from './contratos.js';
export function iniciarChat(){
 const form=document.querySelector('#chat-form'),input=document.querySelector('#chat-input'),send=document.querySelector('#chat-send'),messages=document.querySelector('#messages');let busy=false;
 function add(text,role='assistant'){const item=document.createElement('div');item.className='message '+role;const label=document.createElement('small'),p=document.createElement('p');label.textContent=role==='user'?'TÚ':role==='error'?'NO SE PUDO RESPONDER':config.mode==='demo'?'ASISTENTE · SIMULACIÓN':'ASISTENTE LOCAL';p.textContent=text;item.append(label,p);messages.append(item);messages.scrollTop=messages.scrollHeight;return item;}
 add(config.mode==='demo'?'Interfaz lista. Las respuestas actuales son ejemplos y no contienen recomendaciones médicas.':'Haz una pregunta al asistente local de la misión.');
 input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();if(!busy)form.requestSubmit();}});
 form.addEventListener('submit',async event=>{event.preventDefault();const texto=input.value.trim();if(!texto||busy)return;busy=true;send.disabled=true;input.disabled=true;add(texto,'user');input.value='';const waiting=add('Preparando respuesta…');
 try{const result=validarRespuesta(await enviarMensaje(texto,{simularError:document.querySelector('#demo-chat-error').checked}));waiting.remove();const item=add(result.respuesta);mostrarFuentes(item,result.fuentes);document.querySelector('#local-status').textContent=config.mode==='demo'?'Asistente local: respuesta simulada':'Asistente local: disponible';}
 catch(error){waiting.remove();add(error.message,'error');input.value=texto;document.querySelector('#local-status').textContent=config.mode==='demo'?'Asistente local: error simulado':'Asistente local: no disponible';}
 finally{busy=false;send.disabled=false;input.disabled=false;input.focus();messages.scrollTop=messages.scrollHeight;}
 });
}

