const $ = s => document.querySelector(s);
const dialogo = $('#registroDialogo'), form = $('#registroForm');
const indicador = $('#registroIndicador'), valor = $('#registroValor'), fecha = $('#registroFecha');
const guardar = $('#registroGuardar'), mensaje = $('#registroMensaje'), filtro = $('#historialFiltro');
const unidades = { pulso: 'lpm', presion_arterial: 'mmHg', oxigeno: '%', glucosa: 'mg/dL', temperatura: '°C', sueno: 'h', animo: '/5', estres: '/5' };
const contextos = { sin_especificar: 'Sin especificar', reposo: 'En reposo', despues_ejercicio: 'Después de ejercicio', ayunas: 'En ayunas', despues_comida: 'Después de comer', otro: 'Otro' };
const escapar = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
const numero = v => Number(v).toLocaleString('es', { maximumFractionDigits: 6 });
let offset = 0, total = 0, ocupado = false, consulta = 0, pendiente = null;
const limite = 20;

function horaLocal() {
  const ahora = new Date();
  return new Date(ahora.getTime() - ahora.getTimezoneOffset() * 60000).toISOString().slice(0,16);
}

function prepararIndicador() {
  const presion = indicador.value === 'presion_arterial', escala = ['animo','estres'].includes(indicador.value);
  $('#registroValorEtiqueta').textContent = presion ? 'Sistólica (mmHg)' : `Valor (${unidades[indicador.value]})`;
  $('#registroDiastolicaGrupo').hidden = !presion;
  $('#registroDiastolica').required = presion;
  $('#registroDiastolica').disabled = !presion;
  $('#registroEscala').hidden = !escala;
  valor.step = escala ? '1' : 'any';
  valor.removeAttribute('min'); valor.removeAttribute('max');
  if (indicador.value !== 'temperatura') valor.min = escala ? '1' : '0';
  if (escala) valor.max = '5';
  if (indicador.value === 'oxigeno') valor.max = '100';
  if (indicador.value === 'sueno') valor.max = '24';
}

async function api(url, options = {}) {
  const r = await fetch(url, { ...options, signal: AbortSignal.timeout(8000) });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    const texto = Array.isArray(d.detail) ? d.detail.map(e => e.msg).join(' · ') : d.detail;
    throw new Error(texto || `Error del servidor (${r.status}).`);
  }
  return r.json();
}

function informar(texto, error = false) {
  mensaje.textContent = texto; mensaje.dataset.error = String(error);
}

async function cargarHistorial() {
  const actual = ++consulta;
  $('#historialEstado').textContent = 'Cargando registros locales…';
  $('#historialTabla').innerHTML = '';
  $('#historialAnterior').disabled = true; $('#historialSiguiente').disabled = true;
  try {
    const params = new URLSearchParams({ limite, offset });
    if (filtro.value) params.set('indicador', filtro.value);
    const d = await api(`/api/historial/A1?${params}`);
    if (actual !== consulta) return;
    total = d.total;
    $('#historialEstado').textContent = total ? `${total} ${total === 1 ? 'medición' : 'mediciones'} en este filtro. Almacenamiento local en esta máquina.` : 'Todavía no hay mediciones en este filtro.';
    $('#historialTabla').innerHTML = d.mediciones.length ? `<table><caption class="sr-only">Historial manual del tripulante A1</caption><thead><tr><th scope="col">Fecha local</th><th scope="col">Indicador</th><th scope="col">Valor</th><th scope="col">Contexto</th><th scope="col">Notas</th></tr></thead><tbody>${d.mediciones.map(m => `<tr><td><time datetime="${escapar(m.fecha)}">${escapar(new Date(m.fecha).toLocaleString('es'))}</time></td><th scope="row">${escapar(m.nombre)}</th><td>${numero(m.valor)}${m.diastolica == null ? '' : '/' + numero(m.diastolica)} ${escapar(m.unidad)}</td><td>${escapar(contextos[m.contexto] ?? m.contexto)}</td><td>${escapar(m.nota || '—')}</td></tr>`).join('')}</tbody></table>` : '';
    $('#historialPagina').textContent = total ? `${offset + 1}–${Math.min(offset + limite,total)} de ${total}` : '0 registros';
    $('#historialAnterior').disabled = offset === 0;
    $('#historialSiguiente').disabled = offset + limite >= total;
  } catch (e) {
    if (actual !== consulta) return;
    $('#historialEstado').textContent = `No se pudo leer el historial. ${e.message} Pulsa Actualizar historial para reintentar.`;
    $('#historialPagina').textContent = '';
  }
}

for (const o of indicador.options) filtro.add(new Option(o.textContent, o.value));
prepararIndicador();
$('#abrirRegistro').addEventListener('click', () => {
  if (!fecha.value) fecha.value = horaLocal();
  fecha.max = horaLocal();
  dialogo.showModal(); cargarHistorial();
});
indicador.addEventListener('change', prepararIndicador);
filtro.addEventListener('change', () => { offset = 0; cargarHistorial(); });
$('#historialRecargar').addEventListener('click', () => { offset = 0; cargarHistorial(); });
$('#historialAnterior').addEventListener('click', () => { offset = Math.max(0, offset - limite); cargarHistorial(); });
$('#historialSiguiente').addEventListener('click', () => { if(offset + limite < total) { offset += limite; cargarHistorial(); } });

form.addEventListener('submit', async ev => {
  ev.preventDefault();
  fecha.max = horaLocal();
  if (ocupado || !form.reportValidity()) return;
  const d = new FormData(form), cuando = new Date(d.get('fecha'));
  if (!Number.isFinite(cuando.getTime()) || cuando.getTime() > Date.now()) { informar('Revisa la fecha: no puede estar en el futuro.', true); return; }
  const cuerpo = { astronauta_id: 'A1', indicador: d.get('indicador'), valor: Number(d.get('valor')), fecha: cuando.toISOString(), contexto: d.get('contexto'), nota: d.get('nota').trim() };
  if (cuerpo.indicador === 'presion_arterial') cuerpo.diastolica = Number(d.get('diastolica'));
  if (cuerpo.diastolica != null && (cuerpo.diastolica <= 0 || cuerpo.valor <= cuerpo.diastolica)) { informar('Revisa la presión: sistólica debe ser mayor que diastólica y ambas positivas.', true); return; }
  // Un reintento idéntico conserva su ID: un timeout no duplica la medición.
  const firma = JSON.stringify(cuerpo);
  if (!pendiente || pendiente.firma !== firma) pendiente = { firma, id: crypto.randomUUID() };
  ocupado = true; guardar.disabled = true; guardar.setAttribute('aria-busy','true');
  for (const campo of form.elements) campo.disabled = true;
  informar('Guardando en esta máquina…');
  try {
    await api('/api/mediciones', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ ...cuerpo, id: pendiente.id }) });
    pendiente = null;
    informar('Medición guardada. Permanecerá disponible al cerrar la aplicación.');
    document.dispatchEvent(new CustomEvent('apelogic:medicion-guardada', { detail: { indicador: cuerpo.indicador } }));
    valor.value = ''; $('#registroDiastolica').value = ''; form.elements.nota.value = ''; fecha.value = horaLocal();
    offset = 0; filtro.value = cuerpo.indicador; await cargarHistorial();
  } catch (e) {
    informar(`No se pudo confirmar el guardado. ${e.message} Conservamos el formulario para que puedas reintentar.`, true);
  } finally {
    ocupado = false;
    for (const campo of form.elements) campo.disabled = false;
    guardar.removeAttribute('aria-busy'); prepararIndicador();
  }
});
