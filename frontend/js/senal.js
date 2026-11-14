import {config} from './config.js';
import {obtenerSenal,alternarSenalDemo} from './api.js';
export function iniciarSenal(){
 const status=document.querySelector('#signal-status'),toggle=document.querySelector('#toggle-signal'),send=document.querySelector('#send-earth'),label=document.querySelector('#earth-status'),bar=document.querySelector('#earth-progress');
 let conectado=false,active=false,elapsed=0,previous=performance.now();
 async function refresh(){try{const data=await obtenerSenal();if(typeof data.conectado!=='boolean')throw new Error('Formato desconocido');conectado=data.conectado;status.textContent=conectado?'Enlace con Tierra disponible':'Sin enlace con Tierra';toggle.textContent=conectado?'Simular desconexión':'Simular reconexión';}catch{conectado=false;status.textContent='Enlace desconocido · API no disponible';}}
 toggle.hidden=config.mode!=='demo';toggle.addEventListener('click',()=>{alternarSenalDemo();refresh();});
 // Representación visual exclusivamente: no envía ninguna solicitud de ayuda.
 send.addEventListener('click',()=>{active=true;elapsed=0;previous=performance.now();send.disabled=true;bar.value=0;label.textContent=conectado?'Viaje simulado iniciado.':'Simulación en cola hasta recuperar el enlace.';});
 setInterval(()=>{const now=performance.now(),delta=(now-previous)/1000;previous=now;if(!active)return;if(!conectado){label.textContent='Simulación en pausa: esperando enlace con Tierra.';return;}elapsed=Math.min(840,elapsed+delta);bar.value=elapsed;const left=Math.ceil(840-elapsed);label.textContent='Viaje simulado · '+Math.floor(left/60)+':'+String(left%60).padStart(2,'0')+' restantes';if(elapsed>=840){active=false;send.disabled=false;label.textContent='Simulación completada. No se envió un mensaje real.';}},1000);
 refresh();setInterval(refresh,15000);
}

