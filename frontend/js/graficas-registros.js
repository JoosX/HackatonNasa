import { renderEvolucion } from './evolucion.js';
const escapar = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const numero = v => Number(v).toLocaleString('es',{maximumFractionDigits:2});
const fecha = f => new Date(f).toLocaleString('es',{dateStyle:'short',timeStyle:'short'});

export function graficaRegistro(i, color) {
  const puntos = i.historial ?? [], validos = puntos.filter(p=>!p.sospechoso);
  const presion = i.indicador === 'presion_arterial';
  const aviso = `<p class="registro-aviso"><strong>${escapar(i.nombre)} · ${escapar(i.calidad)}</strong><br>${escapar(i.motivo)} Rangos ilustrativos; no diagnóstico.</p>` + renderEvolucion(i);
  if (!validos.length) return aviso + '<p>Sin muestras confiables para graficar este indicador.</p>';
  const W=400,H=160,t0=new Date(puntos[0].fecha).getTime(),t1=new Date(puntos.at(-1).fecha).getTime();
  const vals=validos.flatMap(p=>presion ? [p.valor,p.diastolica] : [p.valor]);
  const lo=Math.min(...vals),hi=Math.max(...vals),pad=(hi-lo)*.15||1;
  const X=p=>t1===t0?W/2:45+(new Date(p.fecha).getTime()-t0)/(t1-t0)*(W-65);
  const Y=v=>18+(hi+pad-v)/(hi-lo+2*pad)*100;
  function trazo(campo,tono) {
    let d='',segmento=false;
    for(const p of puntos) { if(p.sospechoso) {segmento=false;continue;} d+=`${segmento?'L':'M'}${X(p)},${Y(p[campo])} `;segmento=true; }
    return `<path d="${d}" fill="none" stroke="${tono}" stroke-width="1.8"/>${validos.map(p=>`<circle cx="${X(p)}" cy="${Y(p[campo])}" r="3" style="stroke:${tono}"><title>${escapar(fecha(p.fecha))}: ${numero(p[campo])} ${escapar(i.unidad)}${presion ? campo==='valor'?' · Sistólica':' · Diastólica':''}</title></circle>`).join('')}`;
  }
  return aviso+`<figure class="grafica" style="--c:${color}"><figcaption>${escapar(i.nombre)} · ${puntos.length} ${puntos.length===1?'registro guardado':'registros guardados'}</figcaption>
    ${presion?'<p>Sistólica: línea clara · Diastólica: línea azul</p>':''}
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escapar(i.nombre)}: historial manual con eje proporcional al tiempo${presion?', sistólica y diastólica':''}">
      ${trazo('valor',presion?'#e6e6e6':color)}${presion?trazo('diastolica','#91c8ff'):''}
      <text x="5" y="28">${numero(hi)}</text><text x="5" y="117">${numero(lo)}</text>
      <text x="45" y="147">${escapar(fecha(puntos[0].fecha))}</text></svg>
    <p>Última muestra: ${escapar(fecha(i.fecha))}. Solo registros manuales, hasta 100; sin puntos generados. Los valores sospechosos cortan el trazo. Los segmentos no son medición continua.</p>
    <p>Valores exactos y fechas en Registro e historial.${i.indicador==='animo'||i.indicador==='estres'?' Escala 1–5 de demostración, no validada clínicamente.':''}</p></figure>`;
}
