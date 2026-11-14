import {organos} from './config.js';
import {colores} from './estado.js';
export async function crearVisor2d(container,onSelect){
 const response=await fetch(new URL('../img/cuerpo.svg',import.meta.url));if(!response.ok)throw new Error('No se pudo cargar el SVG local.');
 // Únicamente se inserta nuestro recurso estático, nunca contenido de la API.
 const doc=new DOMParser().parseFromString(await response.text(),'image/svg+xml'),svg=document.importNode(doc.documentElement,true);container.replaceChildren(svg);
 const elements=[...svg.querySelectorAll('[data-organo]')];
 for(const el of elements){el.setAttribute('role','button');el.setAttribute('tabindex','0');el.setAttribute('aria-label',organos[el.dataset.organo]);el.style.cursor='pointer';el.addEventListener('click',()=>onSelect(el.dataset.organo));el.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();onSelect(el.dataset.organo);}});}
 return {actualizar(data){for(const el of elements)el.setAttribute('fill',el.dataset.organo==='cuerpo'?'#426079':colores[data[el.dataset.organo]?.color]||colores.sin_datos);},seleccionar(id){for(const el of elements){el.setAttribute('stroke',el.dataset.organo===id?'#ffffff':'#7491aa');el.setAttribute('stroke-width',el.dataset.organo===id?'3':'1');el.setAttribute('aria-pressed',String(el.dataset.organo===id));}}};
}

