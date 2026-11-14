import {config,organos} from './config.js';
const demo={organos:Object.fromEntries(Object.keys(organos).map(id=>[id,{color:['huesos','ojos','cuerpo'].includes(id)?'sin_datos':'verde',pulso:null}]))};
demo.organos.corazon={color:'amarillo',pulso:82};
let conectado=true;
async function request(path,options={}){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),config.timeoutMs);
 try{const response=await fetch(config.apiBase+path,{...options,signal:controller.signal});if(!response.ok)throw new Error('La API respondió HTTP '+response.status);return await response.json();}
 catch(error){if(error.name==='AbortError')throw new Error('Se agotó el tiempo de espera. Inténtalo de nuevo.');throw error;}
 finally{clearTimeout(timer);}
}
export async function obtenerEstado(){return config.mode==='demo'?structuredClone(demo):request('/api/estado/'+encodeURIComponent(config.astronautaId));}
export async function obtenerFichas(){
 if(config.mode!=='demo')return request('/api/fichas');
 const preguntas=['¿Cómo medir?','¿Por qué importa?','¿Qué cambia en el espacio?','¿A quién avisar?','¿Cómo prevenir?'];
 const textos=['Aquí se explicará cómo registrar sus indicadores.','Aquí aparecerá su relevancia para la salud de la tripulación.','Aquí aparecerán los efectos del entorno espacial, revisados por el equipo.','Aquí se indicará el contacto y protocolo de la misión.','Aquí aparecerán medidas de prevención documentadas.'];
 return {fichas:Object.entries(organos).map(([id,titulo])=>({id,titulo,preguntas:preguntas.map((pregunta,i)=>({pregunta,respuesta:textos[i]+' Contenido pendiente de P6.'})),fuentes:[{titulo:'Ficha de ejemplo · pendiente de P6',url:null}]}))};
}
export async function enviarMensaje(mensaje,{simularError=false}={}){
 if(config.mode!=='demo')return request('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({astronauta_id:config.astronautaId,mensaje})});
 await new Promise(resolve=>setTimeout(resolve,900));
 if(simularError)throw new Error('Error de conexión simulado. Tu mensaje se conserva para volver a enviarlo.');
 return {respuesta:'Esta es una respuesta de demostración, no una respuesta de IA. Cuando P5 conecte el asistente local, aquí aparecerá su respuesta basada en las guías disponibles.',fuentes:[{titulo:'Fuente de ejemplo · sin documento médico conectado',url:null}]};
}
export async function obtenerSenal(){return config.mode==='demo'?{conectado}:request('/api/sync');}
export function alternarSenalDemo(){if(config.mode==='demo')conectado=!conectado;}
export function cambiarEstadoDemo(color,pulso){if(config.mode==='demo')demo.organos.corazon={color,pulso:color==='sin_datos'?null:Number(pulso)};}

