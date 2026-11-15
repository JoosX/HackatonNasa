// Vista de "Medir, comprender y actuar". Autor original: Romario (rama romario/orientacion-fundamentada).
// Versión bilingüe español / inglés.
import { L, LOCALE } from './i18n.js';

const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function siguientePaso(i) {
  if (!i || i.calidad === 'ausente') return {titulo:L('Falta una medición','A measurement is missing'), texto:L('No hay un registro para evaluar. Sigue las instrucciones de medición y registra el resultado con fecha y contexto.','There is no record to evaluate. Follow the measurement instructions and log the result with date and context.')};
  if (i.calidad === 'error') return {titulo:L('No se pudo consultar el registro','The record could not be checked'),texto:L('No podemos confirmar el estado del dato. Reintenta cuando el servidor local esté disponible; no se sustituye por un valor normal.','We cannot confirm the status of the data. Try again when the local server is available; it is not replaced by a normal value.')};
  if (i.calidad === 'sospechoso') return {titulo:L('Comprueba la lectura','Check the reading'),texto:L('La lectura está fuera del intervalo de plausibilidad ilustrativo. Comprueba equipo, unidad y registro. No se interpreta como normal ni se descarta un problema de salud.','The reading is outside the illustrative plausibility range. Check the device, unit and record. It is not read as normal and a health problem is not ruled out.')};
  if (i.calidad === 'vencido') return {titulo:L('La lectura ya no describe el momento actual','The reading no longer describes the present'),texto:L('Conservamos el dato en el historial. Registra una medición nueva con el equipo disponible para volver a evaluar su vigencia.','We keep the value in the history. Log a new measurement with the available device to evaluate it again.')};
  if (i.calidad === 'contexto_pendiente') return {titulo:L('El contexto no permite aplicar este rango','The context does not allow this range'),texto:L('La glucosa se conserva sin clasificar. Registra si realmente fue en ayunas o después de comer; no asumas un contexto para obtener un color.','Glucose is kept unclassified. Log whether it was really fasting or after eating; do not assume a context to get a color.')};
  if (i.calidad !== 'vigente') return {titulo:L('No hay una evaluación disponible','No evaluation available'),texto:L('Consulta la guía y comprueba el dato antes de interpretarlo.','Check the guide and the value before interpreting it.')};
  if (i.color === 'rojo') return {titulo:L('Alerta según el rango ilustrativo','Warning according to the illustrative range'),texto:L('Avisa a la tripulación y sigue el protocolo de a bordo. Si hay síntomas importantes, no esperes una respuesta del chat ni del enlace con la Tierra.','Alert your crew and follow the onboard protocol. If there are important symptoms, do not wait for a reply from the chat or the link to Earth.')};
  if (i.color === 'amarillo') return {titulo:L('Revisa el resultado y su contexto','Review the result and its context'),texto:L('El valor está fuera del rango ilustrativo verde. Consulta la guía y las condiciones de medición; una lectura aislada no establece un diagnóstico.','The value is outside the illustrative green range. Check the guide and the measurement conditions; a single reading does not establish a diagnosis.')};
  return {titulo:L('Lectura dentro del rango ilustrativo','Reading within the illustrative range'),texto:L('Conserva la medición y su contexto para revisar la evolución. Este resultado no descarta síntomas ni equivale a una evaluación completa de salud.','Keep the measurement and its context to follow the trend. This result does not rule out symptoms and is not a complete health evaluation.')};
}

function fuente(g) {
  const url=/^https:\/\//.test(g.url??'')?g.url:null;
  return `<section class="orientacion-fuente" aria-label="${L('Fuente y revisión de la orientación','Source and review of the guidance')}"><p><strong>${L('Guía local','Local guide')}:</strong> ${esc(g.titulo)} · ${esc(g.archivo)} · ${L('Versión','Version')} ${esc(g.version)}</p>
    <p><strong>${L('Estado','Status')}:</strong> ${esc(g.estado_revision)}.</p><p>${esc(g.autor_contenido)}</p>
    <p><strong>${L('Fuente de contexto','Context source')}:</strong> ${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(g.fuente)} ↗</a>`:esc(g.fuente)}. ${L('El enlace no acredita revisión clínica de esta adaptación.','The link does not certify clinical review of this adaptation.')}</p>
    <p>${L('Texto disponible sin internet con el servidor local activo. Abrir la fuente externa requiere conexión.','Text available without internet while the local server runs. Opening the external source requires a connection.')}</p></section>`;
}

function detalleMedicion(g) {
  const m=g.medicion;
  if(!m)return `<ol><li>${esc(g.como_medir)}</li><li>${L('Comprueba la unidad','Check the unit')} (${esc(g.unidad)}) ${L('y anota fecha, contexto y cualquier detalle relevante.','and note the date, context and any relevant detail.')}</li></ol>`;
  return `<p><strong>${L('Antes de empezar','Before you start')}:</strong> ${esc(m.preparacion)}</p><ol>${m.pasos.map(p=>`<li>${esc(p)}</li>`).join('')}</ol>
    <details><summary>${L('Errores frecuentes y si no obtengo el dato','Common mistakes and what if I cannot get the value')}</summary><p>${esc(m.errores)}</p><p>${esc(m.sin_equipo)}</p></details>
    <p class="orientacion-enlace"><a href="${esc(/^https:\/\//.test(m.fuente.url)?m.fuente.url:'#')}" target="_blank" rel="noopener noreferrer">${esc(m.fuente.nombre)} ↗</a> · ${L('Adaptación educativa del equipo.','Educational adaptation by the team.')}</p><p class="orientacion-enlace">${esc(m.alcance)}</p>`;
}

function detalleRegla(g) {
  const r=g.regla;
  if(!r)return '';
  const fila=(nombre,v)=>`<tr><th scope="row">${esc(nombre)}</th><td>${esc(v.verde?.join('–'))}</td><td>${esc(v.amarillo?.join('–'))}</td></tr>`;
  const componente={sistolica:L('sistólica','systolic'),diastolica:L('diastólica','diastolic')};
  return `<details class="orientacion-auditoria"><summary>${L('¿De dónde salen estos colores?','Where do these colors come from?')}</summary><p><strong>${L('Sin aprobación clínica.','No clinical approval.')}</strong> ${esc(r.validacion.nota)}</p>
    <div class="orientacion-tabla"><table><caption>${L('Configuración ilustrativa actual','Current illustrative configuration')} (${esc(g.unidad)}). ${L('Fuera del amarillo se muestra rojo.','Outside yellow, red is shown.')}</caption><thead><tr><th>${L('Dato','Value')}</th><th>${L('Verde','Green')}</th><th>${L('Amarillo (incluye verde)','Yellow (includes green)')}</th></tr></thead><tbody>${r.componentes?Object.entries(r.componentes).map(([n,v])=>fila(componente[n]??n,v)).join(''):fila(g.nombre,r)}</tbody></table></div>
    <p>${L('El registro se marca vencido tras','The record is marked outdated after')} ${esc(r.max_antiguedad_min)} ${L('minutos.','minutes.')} ${esc(r.validacion.vigencia)}</p><p>${esc(r.validacion.responsable)}. ${L('NASA HRP y OSD-575 no certifican esta configuración.','NASA HRP and OSD-575 do not certify this configuration.')}</p></details>`;
}

export function renderOrientacion(g,i,{urgente=false}={}) {
  if(urgente) return `<div class="orientacion-grid"><section class="orientacion-paso"><p class="rotulo">${L('Referencia local','Local reference')}</p><h3>${L('Señales descritas en la guía','Signs described in the guide')}</h3><p>${esc(g.senales)}</p></section>
    <section class="orientacion-paso"><p class="rotulo">${L('Escalamiento','Escalation')}</p><h3>${L('Cuándo avisar según el borrador','When to alert according to the draft')}</h3><p>${esc(g.cuando_avisar)}</p><p>${L('Ante síntomas importantes, prioriza avisar y seguir el protocolo de a bordo. No retrases la ayuda para completar un registro.','With important symptoms, prioritize alerting and following the onboard protocol. Do not delay help to complete a record.')}</p></section></div>${fuente(g)}`;
  const paso=siguientePaso(i);
  const valor=i?.valor==null?L('Sin dato','No data'):typeof i.valor==='number'?i.valor.toLocaleString(LOCALE):i.valor;
  const calidad={vigente:L('vigente','current'),vencido:L('vencido','outdated'),sospechoso:L('sospechoso','suspicious'),ausente:L('ausente','missing'),error:'error',contexto_pendiente:L('contexto pendiente','context pending')};
  return `<div class="orientacion-estado"><strong>${esc(g.nombre)}: ${esc(valor)} ${i?.valor==null?'':esc(i?.unidad)}</strong><span>${esc(calidad[i?.calidad]??i?.calidad??L('no disponible','not available'))} · ${i?.fecha?esc(new Date(i.fecha).toLocaleString(LOCALE)):L('sin fecha registrada','no date recorded')}</span></div>
    <div class="orientacion-grid">
      <section class="orientacion-paso"><p class="rotulo">01 / ${L('Medir','Measure')}</p><h3>${L('Cómo obtener el dato','How to get the value')}</h3><p><strong>${L('Equipo o entrada','Device or input')}:</strong> ${esc(g.equipo)}</p>
        ${detalleMedicion(g)}
        <button type="button" class="btn" data-orientacion-registrar="${esc(g.indicador)}">${L('Registrar medición','Log measurement')}</button></section>
      <section class="orientacion-paso"><p class="rotulo">02 / ${L('Comprender','Understand')}</p><h3>${L('Por qué importa','Why it matters')}</h3><p>${esc(g.por_que)}</p><details><summary>${L('Qué cambia en el espacio','What changes in space')}</summary><p>${esc(g.espacio)}</p></details>
        <p>${esc(i?.motivo??L('No se pudo consultar una medición actual de este indicador.','A current measurement of this indicator could not be checked.'))}</p></section>
      <section class="orientacion-paso orientacion-dato"><p class="rotulo">03 / ${L('Actuar','Act')}</p><h3>${esc(paso.titulo)}</h3><p>${esc(paso.texto)}</p>
        ${detalleRegla(g)}<button type="button" class="btn btn-peligro" data-abrir-urgente="${esc(g.indicador)}">${L('Consultar orientación urgente','Open urgent guidance')}</button>
        <details><summary>${L('Consultar la guía local ilustrativa','Read the illustrative local guide')}</summary><ol>${g.pasos_guia.map(p=>`<li>${esc(p)}</li>`).join('')}</ol></details></section>
      <section class="orientacion-paso"><p class="rotulo">04 / ${L('Pedir ayuda','Get help')}</p><h3>${L('Cuándo avisar','When to alert')}</h3><p>${esc(g.cuando_avisar)}</p><details><summary>${L('Señales descritas en la guía','Signs described in the guide')}</summary><p>${esc(g.senales)}</p></details>
        <p>${L('Si hay síntomas importantes, usa el protocolo de a bordo aunque el dato aparezca en rango.','If there are important symptoms, use the onboard protocol even if the value looks in range.')}</p></section>
    </div>
    ${fuente(g)}`;
}
