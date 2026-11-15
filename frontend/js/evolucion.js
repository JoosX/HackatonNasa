const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const numero=v=>Number(v).toLocaleString('es',{maximumFractionDigits:6});
const fecha=f=>new Date(f).toLocaleString('es');

export function renderEvolucion(i) {
  const e=i.evolucion;
  if(!e)return '';
  const c=e.comparacion;
  return `<section class="evolucion-tarjeta" aria-label="Cambios observados de ${esc(i.nombre)}">
    <p class="rotulo">Tu evolución / últimos ${e.ventana_dias} días</p><h3>${c?'Cambio observado entre registros':'Aún no hay una comparación suficiente'}</h3>
    <p>${esc(e.resumen)}</p>
    <p class="evolucion-conteo">${e.registros_ventana} registros en la ventana · ${e.registros_validos} válidos · ${e.muestras_usadas} muestras seleccionadas</p>
    ${c?`<dl class="evolucion-comparacion"><div><dt>Anterior · ${esc(fecha(c.anterior.fecha))}</dt><dd>${numero(c.anterior.valor)} ${esc(c.unidad)}</dd></div><div><dt>Última · ${esc(fecha(c.ultima.fecha))}</dt><dd>${numero(c.ultima.valor)} ${esc(c.unidad)}</dd></div><div><dt>Diferencia</dt><dd>${c.diferencia>0?'+':''}${numero(c.diferencia)} ${esc(c.unidad)}</dd></div></dl>`:''}
    ${e.advertencias.length?`<ul class="evolucion-avisos">${e.advertencias.map(a=>`<li>${esc(a)}</li>`).join('')}</ul>`:''}
    <details><summary>Cómo se hizo la comparación</summary><p>${esc(e.metodo)} Se revisan hasta ${e.max_registros} registros. No se rellenan días sin datos ni se establece un «normal personal».</p></details>
    <p>Descripción de tus registros; no identifica causas ni establece un diagnóstico.</p>
    <button type="button" class="btn" data-orientacion="${esc(i.indicador)}">Consultar guía de ${esc(i.nombre)}</button></section>`;
}
