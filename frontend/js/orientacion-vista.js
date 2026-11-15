const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function siguientePaso(i) {
  if (!i || i.calidad === 'ausente') return {titulo:'Falta una medición', texto:'No hay un registro para evaluar. Sigue las instrucciones de medición y registra el resultado con fecha y contexto.'};
  if (i.calidad === 'error') return {titulo:'No se pudo consultar el registro',texto:'No podemos confirmar el estado del dato. Reintenta cuando el servidor local esté disponible; no se sustituye por un valor normal.'};
  if (i.calidad === 'sospechoso') return {titulo:'Comprueba la lectura',texto:'La lectura está fuera del intervalo de plausibilidad ilustrativo. Comprueba equipo, unidad y registro. No se interpreta como normal ni se descarta un problema de salud.'};
  if (i.calidad === 'vencido') return {titulo:'La lectura ya no describe el momento actual',texto:'Conservamos el dato en el historial. Registra una medición nueva con el equipo disponible para volver a evaluar su vigencia.'};
  if (i.calidad === 'contexto_pendiente') return {titulo:'El contexto no permite aplicar este rango',texto:'La glucosa se conserva sin clasificar. Registra si realmente fue en ayunas o después de comer; no asumas un contexto para obtener un color.'};
  if (i.calidad !== 'vigente') return {titulo:'No hay una evaluación disponible',texto:'Consulta la guía y comprueba el dato antes de interpretarlo.'};
  if (i.color === 'rojo') return {titulo:'Alerta según el rango ilustrativo',texto:'Avisa a la tripulación y sigue el protocolo de a bordo. Si hay síntomas importantes, no esperes una respuesta del chat ni del enlace con la Tierra.'};
  if (i.color === 'amarillo') return {titulo:'Revisa el resultado y su contexto',texto:'El valor está fuera del rango ilustrativo verde. Consulta la guía y las condiciones de medición; una lectura aislada no establece un diagnóstico.'};
  return {titulo:'Lectura dentro del rango ilustrativo',texto:'Conserva la medición y su contexto para revisar la evolución. Este resultado no descarta síntomas ni equivale a una evaluación completa de salud.'};
}

function fuente(g) {
  const url=/^https:\/\//.test(g.url??'')?g.url:null;
  return `<section class="orientacion-fuente" aria-label="Fuente y revisión de la orientación"><p><strong>Guía local:</strong> ${esc(g.titulo)} · ${esc(g.archivo)} · Versión ${esc(g.version)}</p>
    <p><strong>Estado:</strong> ${esc(g.estado_revision)}.</p><p>${esc(g.autor_contenido)}</p>
    <p><strong>Fuente de contexto:</strong> ${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(g.fuente)} ↗</a>`:esc(g.fuente)}. El enlace no acredita revisión clínica de esta adaptación.</p>
    <p>Texto disponible sin internet con el servidor local activo. Abrir la fuente externa requiere conexión.</p></section>`;
}

function detalleMedicion(g) {
  const m=g.medicion;
  if(!m)return `<ol><li>${esc(g.como_medir)}</li><li>Comprueba la unidad (${esc(g.unidad)}) y anota fecha, contexto y cualquier detalle relevante.</li></ol>`;
  return `<p><strong>Antes de empezar:</strong> ${esc(m.preparacion)}</p><ol>${m.pasos.map(p=>`<li>${esc(p)}</li>`).join('')}</ol>
    <details><summary>Errores frecuentes y si no obtengo el dato</summary><p>${esc(m.errores)}</p><p>${esc(m.sin_equipo)}</p></details>
    <p class="orientacion-enlace"><a href="${esc(/^https:\/\//.test(m.fuente.url)?m.fuente.url:'#')}" target="_blank" rel="noopener noreferrer">${esc(m.fuente.nombre)} ↗</a> · Adaptación educativa del equipo.</p><p class="orientacion-enlace">${esc(m.alcance)}</p>`;
}

function detalleRegla(g) {
  const r=g.regla;
  if(!r)return '';
  const fila=(nombre,v)=>`<tr><th scope="row">${esc(nombre)}</th><td>${esc(v.verde?.join('–'))}</td><td>${esc(v.amarillo?.join('–'))}</td></tr>`;
  return `<details class="orientacion-auditoria"><summary>¿De dónde salen estos colores?</summary><p><strong>Sin aprobación clínica.</strong> ${esc(r.validacion.nota)}</p>
    <div class="orientacion-tabla"><table><caption>Configuración ilustrativa actual (${esc(g.unidad)}). Fuera del amarillo se muestra rojo.</caption><thead><tr><th>Dato</th><th>Verde</th><th>Amarillo (incluye verde)</th></tr></thead><tbody>${r.componentes?Object.entries(r.componentes).map(([n,v])=>fila(n,v)).join(''):fila(g.nombre,r)}</tbody></table></div>
    <p>El registro se marca vencido tras ${esc(r.max_antiguedad_min)} minutos. ${esc(r.validacion.vigencia)}</p><p>${esc(r.validacion.responsable)}. NASA HRP y OSD-575 no certifican esta configuración.</p></details>`;
}

export function renderOrientacion(g,i,{urgente=false}={}) {
  if(urgente) return `<div class="orientacion-grid"><section class="orientacion-paso"><p class="rotulo">Referencia local</p><h3>Señales descritas en la guía</h3><p>${esc(g.senales)}</p></section>
    <section class="orientacion-paso"><p class="rotulo">Escalamiento</p><h3>Cuándo avisar según el borrador</h3><p>${esc(g.cuando_avisar)}</p><p>Ante síntomas importantes, prioriza avisar y seguir el protocolo de a bordo. No retrases la ayuda para completar un registro.</p></section></div>${fuente(g)}`;
  const paso=siguientePaso(i);
  const valor=i?.valor==null?'Sin dato':typeof i.valor==='number'?i.valor.toLocaleString('es'):i.valor;
  return `<div class="orientacion-estado"><strong>${esc(g.nombre)}: ${esc(valor)} ${i?.valor==null?'':esc(i?.unidad)}</strong><span>${esc(i?.calidad??'no disponible')} · ${i?.fecha?esc(new Date(i.fecha).toLocaleString('es')):'sin fecha registrada'}</span></div>
    <div class="orientacion-grid">
      <section class="orientacion-paso"><p class="rotulo">01 / Medir</p><h3>Cómo obtener el dato</h3><p><strong>Equipo o entrada:</strong> ${esc(g.equipo)}</p>
        ${detalleMedicion(g)}
        <button type="button" class="btn" data-orientacion-registrar="${esc(g.indicador)}">Registrar medición</button></section>
      <section class="orientacion-paso"><p class="rotulo">02 / Comprender</p><h3>Por qué importa</h3><p>${esc(g.por_que)}</p><details><summary>Qué cambia en el espacio</summary><p>${esc(g.espacio)}</p></details>
        <p>${esc(i?.motivo??'No se pudo consultar una medición actual de este indicador.')}</p></section>
      <section class="orientacion-paso orientacion-dato"><p class="rotulo">03 / Actuar</p><h3>${esc(paso.titulo)}</h3><p>${esc(paso.texto)}</p>
        ${detalleRegla(g)}<button type="button" class="btn btn-peligro" data-abrir-urgente="${esc(g.indicador)}">Consultar orientación urgente</button>
        <details><summary>Consultar la guía local ilustrativa</summary><ol>${g.pasos_guia.map(p=>`<li>${esc(p)}</li>`).join('')}</ol></details></section>
      <section class="orientacion-paso"><p class="rotulo">04 / Pedir ayuda</p><h3>Cuándo avisar</h3><p>${esc(g.cuando_avisar)}</p><details><summary>Señales descritas en la guía</summary><p>${esc(g.senales)}</p></details>
        <p>Si hay síntomas importantes, usa el protocolo de a bordo aunque el dato aparezca en rango.</p></section>
    </div>
    ${fuente(g)}`;
}
