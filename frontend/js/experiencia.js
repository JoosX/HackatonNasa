'use strict';
// Capa de experiencia P2. P3 puede escuchar apelogic:indicator-selected.
const bodySystems={pulso:{name:'Cardiovascular',organ:'corazon',y:72},glucosa:{name:'Metabolismo',organ:'sangre',y:101},temperatura:{name:'Temperatura corporal',organ:'piel',y:54},oxigeno:{name:'Respiratorio',organ:'pulmones',y:76},sueno:{name:'Sueño y recuperación',organ:'cerebro',y:24},animo:{name:'Bienestar emocional',organ:'cerebro',y:24}};
let activeRecord=null;
function signedDifference(n){return `${n>0?'+':''}${value(n)}`;}
function originLabel(r){return r?.origen==='manual'?'Entrada manual':'Datos simulados';}
function renderExperience(resetRecord=true){
 const sleep=series('sueno'),last=sleep.at(-1),first=sleep[0],down=last&&first&&sleep.length>1&&last.valor<first.valor;
 $('#focus-title').textContent=down?'Tu sueño cambió. Mira la evolución.':'Tu historial cuenta una parte de la historia.';
 $('#focus-description').textContent=down?`El último registro de sueño es de ${value(last.valor)} h, frente a ${value(first.valor)} h al inicio del historial disponible. Explora las fechas y el contexto antes de interpretar el cambio.`:'Compara tus registros, comprueba cuándo se tomaron y revisa su procedencia. Si falta información, completa una nueva medición.';
 $('#focus-data').textContent=last?`${value(last.valor)} h de sueño`:'Sin registros de sueño';
 $('#focus-change').textContent=last&&sleep.length>1?`${signedDifference(last.valor-first.valor)} h desde el primero`:'Sin comparación disponible';
 $('#focus-source').textContent=last?originLabel(last):'Sin datos';
 const latest=[...records].sort((a,b)=>Date.parse(b.fecha)-Date.parse(a.fecha))[0];
 $('#last-update').textContent=latest?`Último registro: ${age(latest.fecha)}`:'Sin registros';
 const d=definitions.find(d=>d.id===selected),system=bodySystems[selected];
 $('#system-title').textContent=system.name;$('#system-subtitle').textContent=d.label;
 ['#system-halo','#system-point'].forEach(id=>$(id).setAttribute('cy',system.y));
 const rows=series(selected).slice(-7);if(resetRecord||!rows[activeRecord])activeRecord=rows.length-1;
 $('#record-picker').innerHTML=rows.map((r,i)=>`<button data-record="${i}" class="record-button ${i===activeRecord?'active':''}" aria-pressed="${i===activeRecord}" aria-label="Registro ${i+1}, ${escapeHtml(new Date(r.fecha).toLocaleString('es'))}, ${value(r.valor)} ${d.unit}"><small>${String(i+1).padStart(2,'0')}</small>${new Date(r.fecha).toLocaleDateString('es',{day:'2-digit',month:'2-digit'})}</button>`).join('');
 const r=rows[activeRecord],prev=rows[activeRecord-1];
 $('#record-detail').innerHTML=r?`<div class="detail-top"><span>${escapeHtml(new Date(r.fecha).toLocaleString('es',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}))}</span><span class="badge">${originLabel(r)}</span></div><div class="detail-values"><div><small>VALOR SELECCIONADO</small><strong>${value(r.valor)} <em>${d.unit}</em></strong></div><div><small>REGISTRO ANTERIOR</small><strong>${prev?`${value(prev.valor)} <em>${d.unit}</em>`:'—'}</strong></div><div><small>DIFERENCIA</small><strong>${prev?`${signedDifference(r.valor-prev.valor)} <em>${d.unit}</em>`:'Sin comparación'}</strong></div></div><p>${escapeHtml(r.nota||'No se registró contexto adicional para esta medición.')}</p>`:'No hay registros disponibles para este indicador.';
 $('#chart').querySelectorAll('circle').forEach((circle,i)=>{circle.classList.toggle('chart-active',i===activeRecord);circle.style.cursor='pointer';circle.onclick=()=>{activeRecord=i;renderExperience(false);};});
}
$('#review-observation').onclick=()=>{selected='sueno';render();renderExperience();$('.trend-card').scrollIntoView({behavior:'smooth',block:'start'});};
$('#record-picker').onclick=e=>{const b=e.target.closest('[data-record]');if(b){activeRecord=Number(b.dataset.record);renderExperience(false);}};
$('#system-handoff').onclick=()=>{const detail={indicador:selected,organo:bodySystems[selected].organ};window.dispatchEvent(new CustomEvent('apelogic:indicator-selected',{detail}));toast(`Selección ${definitions.find(d=>d.id===selected).label} emitida. Visor P3 pendiente de integración.`);};
document.addEventListener('click',e=>{if(e.target.closest('[data-metric]'))renderExperience();});
$('#chart-metric').addEventListener('change',()=>renderExperience());
$('#measurement-form').addEventListener('submit',()=>renderExperience());
renderExperience();
