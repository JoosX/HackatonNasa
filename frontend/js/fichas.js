import {organos} from './config.js';
import {colores,etiquetas} from './estado.js';
export function mostrarFuentes(parent,fuentes=[]){
 const box=document.createElement('div');box.className='source';box.textContent='Fuentes';
 for(const fuente of fuentes){const line=document.createElement('div');let url;try{url=new URL(fuente.url);}catch{}
 if(url&&['https:','http:'].includes(url.protocol)){const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent=fuente.titulo||url.hostname;line.append(link);}else line.textContent=fuente.titulo||'Referencia sin enlace';box.append(line);}
 if(!fuentes.length)box.append(document.createTextNode(' · No se recibieron fuentes.'));
 parent.append(box);
}
export function mostrarFicha(id,fichas,estado){
 document.querySelector('#ficha-title').textContent=organos[id]||id;
 const value=estado[id]||{color:'sin_datos',pulso:null},status=document.querySelector('#ficha-status'),content=document.querySelector('#ficha-content');
 status.textContent=etiquetas[value.color];status.style.color=colores[value.color];content.replaceChildren();
 if(id==='corazon'){const metric=document.createElement('div');metric.className='metric';const n=document.createElement('strong'),unit=document.createElement('span');n.textContent=value.pulso??'—';unit.textContent=value.pulso===null?'Pulso sin datos':'latidos por minuto';metric.append(n,unit);content.append(metric);}
 const ficha=fichas.find(f=>f.id===id);
 if(!ficha){const p=document.createElement('p');p.className='hint';p.textContent='Ficha no disponible. Pendiente de contenido de P6.';content.append(p);return;}
 const list=document.createElement('dl');for(const row of ficha.preguntas||[]){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=row.pregunta;dd.textContent=row.respuesta;list.append(dt,dd);}content.append(list);mostrarFuentes(content,ficha.fuentes);
}

