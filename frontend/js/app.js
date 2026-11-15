// Copiloto de salud: une visor 3D + HUD, signos vitales, ficha con tendencias, chat y conexión con la Tierra.
// Código escrito con asistencia de IA (Claude); revisado por el equipo.

import {
  ORGANOS, COLORES, NOMBRES_INDICADORES, cargarEstado, cargarFichas, colorOrgano, indicador,
  antiguedadTexto, historial, sparkline, valorNumerico, fijarSeries, serieReal,
} from "./organos.js";
import { crearChat, avatarORI } from "./chat.js";
import { crearHud } from "./hud.js";

const $ = (s) => document.querySelector(s);
const reducir = matchMedia("(prefers-reduced-motion: reduce)").matches;
const CORTO = { presion_arterial: "Presión", temperatura: "Temp.", radiacion: "Radiación" };   // rótulos de la tira de instrumentos
const SIGNOS = ["pulso", "presion_arterial", "oxigeno", "glucosa", "temperatura", "sueno", "animo", "radiacion"];
const ETIQUETA_ESTADO = { verde: "Normal", amarillo: "Precaución", rojo: "Alerta", "sin dato": "Sin dato" };
const PREGUNTAS = [
  ["como_medir", "Cómo medir a bordo"], ["por_que", "Por qué importa"], ["efecto_espacio", "Efecto del espacio"],
  ["a_quien_avisar", "Cuándo avisar"], ["prevencion", "Prevención"],
];

let estado, inicial, fichas = {}, reglas = {}, nasa = null, clima = null;
let visor = null, hud = null, chat = null, seleccionado = null, conectado = true, enCola = 0, primeraVez = true;

const escapar = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const numero = (v) => (typeof v === "number" ? v.toLocaleString("es", { maximumFractionDigits: 1 }) : escapar(v));
const nombreOrgano = (o) => fichas[o]?.nombre ?? ORGANOS[o].nombre;

async function json(url) {
  try { const r = await fetch(url, { signal: AbortSignal.timeout(1500) }); return r.ok ? r.json() : null; } catch { return null; }
}

// ---------- Signos vitales (con mini tendencia y conteo al cargar) ----------
function pintarSignos() {
  $("#signos").innerHTML = SIGNOS.map((n) => {
    const i = indicador(estado, n);
    if (!i) return "";
    const organo = Object.keys(ORGANOS).find((o) => ORGANOS[o].indicadores.includes(n));
    const c = COLORES[i.color];
    return `<li><button class="signo" type="button" data-organo="${organo}" style="--c:${c}"
        aria-pressed="${organo === seleccionado}" aria-label="${NOMBRES_INDICADORES[n]}: ${i.valor} ${i.unidad}, ${ETIQUETA_ESTADO[i.color]}">
      <span class="etiqueta"><span class="punto-estado" aria-hidden="true"></span><span>${CORTO[n] ?? NOMBRES_INDICADORES[n]}</span></span>
      <span class="valor">${n === "radiacion"
        ? escapar(String(i.valor).split(" hace ")[0])
        : `<span data-valor="${escapar(i.valor)}">${numero(i.valor)}</span><small>${escapar(i.unidad)}</small>`}</span>
      <span class="pie-signo"><span class="edad">${n === "radiacion" && String(i.valor).includes(" hace ") ? "evento hace " + escapar(String(i.valor).split(" hace ")[1]) : antiguedadTexto(i.antiguedad_min)}</span>${sparkline(historial(estado, n), c)}</span>
    </button></li>`;
  }).join("");
  if (primeraVez && !reducir) contar();
  primeraVez = false;
}

// Conteo de los números una sola vez al cargar (momento "en vivo").
function contar() {
  for (const el of document.querySelectorAll("[data-valor]")) {
    const texto = el.dataset.valor;
    const partes = texto.split("/").map(Number);
    if (partes.some((x) => !Number.isFinite(x))) continue;
    const dec = texto.includes(".") ? 1 : 0;
    const t0 = performance.now(), dur = 900;
    const paso = (t) => {
      const k = Math.min(1, (t - t0) / dur), e = 1 - (1 - k) ** 3;
      el.textContent = partes.map((x) => (x * e).toLocaleString("es", { minimumFractionDigits: dec, maximumFractionDigits: dec })).join("/");
      if (k < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  }
}

// ---------- Gráfica de tendencia con banda normal ----------
function grafica({ serie, etiquetas, verde, color, titulo, nota }) {
  const valores = serie.filter((v) => v != null);
  if (valores.length < 2) return "";
  const W = 320, H = 120, iz = 30, de = 8, ar = 10, ab = 22;
  const lo = Math.min(...valores, verde?.[0] ?? Infinity), hi = Math.max(...valores, verde?.[1] ?? -Infinity);
  const pad = (hi - lo) * 0.15 || 1, min = lo - pad, max = hi + pad;
  const X = (k) => iz + (k / (serie.length - 1)) * (W - iz - de);
  const Y = (v) => ar + (1 - (v - min) / (max - min)) * (H - ar - ab);
  const pts = serie.map((v, k) => (v == null ? null : [X(k), Y(v), v])).filter(Boolean);
  const d = pts.map(([x, y], k) => `${k ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const banda = verde ? `<rect x="${iz}" y="${Y(Math.min(verde[1], max))}" width="${W - iz - de}" height="${Math.max(0, Y(Math.max(verde[0], min)) - Y(Math.min(verde[1], max)))}" class="g-banda"/>` : "";
  const ejes = [min + pad, max - pad].map((v) => `<text x="${iz - 6}" y="${Y(v) + 3}" text-anchor="end">${numero(Math.round(v * 10) / 10)}</text>`).join("");
  const xs = etiquetas.map((t, k) => (k % Math.ceil(etiquetas.length / 7) === 0 || k === etiquetas.length - 1 ? `<text x="${X(k)}" y="${H - 6}" text-anchor="middle">${escapar(t)}</text>` : "")).join("");
  const puntos = pts.map(([x, y, v]) => `<circle cx="${x}" cy="${y}" r="3"><title>${numero(v)}</title></circle>`).join("");
  return `<figure class="grafica" style="--c:${color}">
    <figcaption><span>${escapar(titulo)}</span>${verde ? '<span class="g-ley"><i></i>rango normal</span>' : ""}</figcaption>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escapar(titulo)}">${banda}${ejes}${xs}<path d="${d}" class="g-linea" pathLength="1"/>${puntos}</svg>
    ${nota ? `<p class="g-nota">${nota}</p>` : ""}</figure>`;
}

// Línea de tiempo de eventos solares reales (NASA DONKI): altura y color según intensidad.
function lineaClima() {
  if (!clima?.eventos?.length) return "";
  const W = 320, H = 110, iz = 8, de = 8, base = 82;
  const t0 = new Date(clima.desde + "T00:00Z").getTime(), t1 = new Date(clima.hasta + "T23:59Z").getTime();
  const X = (t) => iz + ((t - t0) / (t1 - t0)) * (W - iz - de);
  const marcas = clima.eventos.map((e) => {
    const t = new Date((e.pico || e.inicio).slice(0, 16) + "Z").getTime();
    if (!Number.isFinite(t)) return "";
    const clase = String(e.clase || "");
    let alto = 14, color = "#6b6b6b";
    if (e.tipo === "particulas") { alto = 64; color = COLORES.rojo; }
    else if (e.tipo === "tormenta_geomagnetica") { alto = 10 + 6 * (e.kp || 4); color = "#bdbdbd"; }
    else if (clase.startsWith("X")) { alto = 60; color = COLORES.rojo; }
    else if (clase.startsWith("M")) { alto = 26 + 3 * parseFloat(clase.slice(1) || 1); color = COLORES.amarillo; }
    const x = X(t);
    const forma = e.tipo === "tormenta_geomagnetica"
      ? `<rect x="${x - 3}" y="${base - alto}" width="6" height="${alto}" fill="none" stroke="${color}"/>`
      : `<rect x="${x - 1.5}" y="${base - alto}" width="3" height="${alto}" fill="${color}"/>`;
    return `<g>${forma}<title>${escapar(clase)} · ${escapar((e.pico || e.inicio).replace("T", " ").replace("Z", " UTC"))}</title></g>`;
  }).join("");
  const dias = [0, 10, 20, 30].map((d) => { const t = t0 + (d / 30) * (t1 - t0); return `<text x="${X(t)}" y="${H - 8}" text-anchor="middle">${new Date(t).toLocaleDateString("es", { day: "numeric", month: "short", timeZone: "UTC" })}</text>`; }).join("");
  const sync = clima.sincronizado ? new Date(clima.sincronizado.replace("Z", ":00Z")).toLocaleString("es", { dateStyle: "medium", timeStyle: "short" }) : "—";
  return `<figure class="grafica" style="--c:${COLORES.amarillo}">
    <figcaption><span>Eventos solares · últimos 30 días</span><span class="g-ley">NASA DONKI</span></figcaption>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Eventos solares de los últimos 30 días">
      <line x1="${iz}" y1="${base}" x2="${W - de}" y2="${base}" stroke="#3a3a3a"/>${marcas}${dias}</svg>
    <p class="g-nota">${escapar(clima.motivo || "")} Barras: llamaradas (ámbar = clase M, rojo = clase X), rojo alto = partículas solares, contorno = tormenta geomagnética. Sincronizado: ${escapar(sync)}. Se actualiza cuando vuelve la señal con la Tierra.</p></figure>`;
}

// Etiquetas del eje X a partir de las fechas reales de cada medición.
function etiquetasDe(n) {
  const s = serieReal(n);
  if (!s.length) return ["-6 d", "-5", "-4", "-3", "-2", "-1", "hoy"];
  const hoy = new Date().toDateString();
  return s.map((p) => { const d = new Date(p.ts); return d.toDateString() === hoy ? "hoy" : d.toLocaleDateString("es", { weekday: "short" }); });
}

function rangoVerde(n) {
  const r = reglas[n];
  return r?.verde ?? r?.componentes?.sistolica?.verde ?? null;
}

function graficasDe(organo) {
  if (organo === "radiacion") return lineaClima();
  const ind = (fichas[organo]?.indicadores ?? ORGANOS[organo].indicadores).find((n) => indicador(estado, n) && valorNumerico(indicador(estado, n).valor) != null);
  let html = "";
  if (ind) {
    const i = indicador(estado, ind);
    html += grafica({
      serie: historial(estado, ind), etiquetas: etiquetasDe(ind), verde: rangoVerde(ind),
      color: COLORES[i.color], titulo: `${NOMBRES_INDICADORES[ind]} · últimos 7 días${ind === "presion_arterial" ? " (sistólica)" : ""}`,
      nota: serieReal(ind).length
        ? `${serieReal(ind).length} mediciones guardadas a bordo.${i.normal != null ? ` Tu normal: ${numero(i.normal)} ${escapar(i.unidad)}${i.desviacion_pct ? ` · hoy ${i.desviacion_pct > 0 ? "+" : ""}${i.desviacion_pct} %` : ""}.` : ""}`
        : "Historial de demostración (sin conexión con la base de datos).",
    });
  }
  // Datos reales de NASA para la glucosa: el "normal" de un tripulante de Inspiration4.
  const real = nasa?.tripulantes?.C003?.glucosa;
  if (organo === "sangre" && real) {
    html += grafica({
      serie: nasa.momentos.map((m) => real.valores[m]), etiquetas: nasa.momentos, verde: real.rango, color: COLORES.amarillo,
      titulo: "Glucosa real · tripulante C003 de Inspiration4",
      nota: `Dato real de <span translate="no">NASA OSDR OSD-575</span>. L = días antes del lanzamiento, R = días después del regreso. El valor de R+45 sale muy bajo en 3 de 4 tripulantes: probablemente un problema de la muestra, por eso la app pide repetir mediciones sospechosas.`,
    });
  }
  return html;
}

// ---------- Ficha del órgano ----------
function pintarFicha() {
  const caja = $("#ficha");
  caja.classList.toggle("abierta", !!seleccionado);
  if (!seleccionado) {
    const alertas = Object.keys(ORGANOS).filter((o) => colorOrgano(estado, o) !== "verde");
    caja.innerHTML = `<p class="rotulo">Estado general</p>
      <h2>${alertas.length ? `${alertas.length} ${alertas.length === 1 ? "sistema requiere" : "sistemas requieren"} atención` : "Todo en rango normal"}</h2>
      <p class="resumen">Cada sistema toma el color de su indicador más alterado. Elige uno en el cuerpo, en las etiquetas o aquí.</p>
      <ul class="organos">${Object.keys(ORGANOS).map((o) => {
        const c = colorOrgano(estado, o);
        return `<li><button type="button" data-organo="${o}" style="--c:${COLORES[c]}">
          <span class="punto-estado" aria-hidden="true"></span>${escapar(nombreOrgano(o))}
          <span class="sr-only">: ${ETIQUETA_ESTADO[c]}</span></button></li>`;
      }).join("")}</ul>`;
    return;
  }
  const f = fichas[seleccionado] ?? {};
  const c = colorOrgano(estado, seleccionado);
  const datos = (f.indicadores ?? ORGANOS[seleccionado].indicadores).map((n) => {
    const i = indicador(estado, n);
    if (!i) return `<li><span>${NOMBRES_INDICADORES[n] ?? n}</span><span class="num">sin dato</span></li>`;
    return `<li style="--c:${COLORES[i.color]}"><span>${NOMBRES_INDICADORES[n]}<span class="edad">${antiguedadTexto(i.antiguedad_min)}</span></span>
      <span class="num">${numero(i.valor)} ${escapar(i.unidad)}</span></li>`;
  }).join("");
  const preguntas = PREGUNTAS.filter(([k]) => f[k]).map(([k, t]) => `<div><h3>${t}</h3><p>${escapar(f[k])}</p></div>`).join("");
  caja.innerHTML = `<p class="rotulo">Sistema seleccionado</p>
    <h2><span class="punto-estado" style="--c:${COLORES[c]}" aria-hidden="true"></span>${escapar(nombreOrgano(seleccionado))}
      <span class="chip chip-estado" style="--c:${COLORES[c]}">${ETIQUETA_ESTADO[c]}</span></h2>
    <ul class="datos">${datos}</ul>
    ${c === "rojo" ? '<p class="aviso-rojo">Avisa a la tripulación y sigue el protocolo de a bordo.</p>' : ""}
    ${graficasDe(seleccionado)}
    <div class="preguntas">${preguntas}</div>
    <p class="fuente">Fuente: ${escapar(f.fuente ?? ORGANOS[seleccionado].fuente)}</p>
    <div class="botones">${(f.indicadores ?? ORGANOS[seleccionado].indicadores).some((n) => reglas[n] && !reglas[n].categorias) ? `<button type="button" class="btn btn-primario" data-registrar="${(f.indicadores ?? ORGANOS[seleccionado].indicadores).find((n) => reglas[n] && !reglas[n].categorias)}">Registrar medición</button>` : ""}<button type="button" class="btn" data-preguntar="${seleccionado}">Preguntar a ORI</button>
      <button type="button" class="btn" data-organo="">Ver todos</button></div>`;
  caja.scrollTop = 0;
}

function seleccionar(organo) {
  seleccionado = organo || null;
  visor?.seleccionar(seleccionado);
  visor?.enfocar(seleccionado);
  hud?.seleccionar(seleccionado);
  if (visor) $("#btnGirar").setAttribute("aria-pressed", String(visor.girando));
  pintarSignos();
  pintarFicha();
  const url = new URL(location.href);
  seleccionado ? url.searchParams.set("organo", seleccionado) : url.searchParams.delete("organo");
  history.replaceState(null, "", url);
}

function refrescar() {
  visor?.aplicarEstado(estado);
  hud?.actualizar();
  pintarSignos();
  pintarFicha();
  const lpm = Number(indicador(estado, "pulso")?.valor) || 70;
  $("#pulso").value = lpm;
  $("#vPulso").textContent = `${lpm} lpm`;
  // Resumen de Precaución y Alerta (C&W), como el panel de alarmas de la nave.
  const cuenta = { rojo: 0, amarillo: 0 };
  for (const i of estado.indicadores) if (cuenta[i.color] != null) cuenta[i.color] += 1;
  $("#cw").innerHTML = `<span class="cw-rojo${cuenta.rojo ? " activo" : " cw-off"}">${cuenta.rojo} alerta${cuenta.rojo === 1 ? "" : "s"}</span>
    <span class="${cuenta.amarillo ? "cw-amarillo" : "cw-off"}">${cuenta.amarillo} ${cuenta.amarillo === 1 ? "precaución" : "precauciones"}</span>`;
  const rojos = cuenta.rojo > 0;
  $("#rotuloEstado").textContent = rojos ? "Alerta" : cuenta.amarillo ? "Precaución" : "Normal";
  $("#rotuloEstado").style.color = COLORES[rojos ? "rojo" : cuenta.amarillo ? "amarillo" : "verde"];
  $("#lienzo").classList.toggle("en-alerta", rojos);
}

// ---------- Base de datos: estado, historial y registro de mediciones ----------
async function recargarDatos() {
  const [e, h] = await Promise.all([json("/api/estado/A1"), json("/api/historial/A1")]);
  if (e) estado = e;
  fijarSeries(h);
  refrescar();
}

const PALABRA = { verde: "normal", amarillo: "en precaución", rojo: "en alerta" };
async function registrar(indicadorNombre, valor, { comentar = true, contexto = null } = {}) {
  const r = await fetch("/api/mediciones", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ astronauta_id: "A1", indicador: indicadorNombre, valor: String(valor), contexto: contexto || null }),
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || "No se pudo guardar la medición.");
  estado = d.estado;
  fijarSeries(await json("/api/historial/A1"));
  refrescar();
  const res = d.resultado;
  if (comentar) {
    const dato = `${res.nombre.toLowerCase()}: **${res.valor} ${res.unidad}**`.trim();
    const texto = res.sospechoso
      ? `Anoté tu ${dato}, pero es un valor muy inusual. ${res.mensaje}`
      : res.color === "sin dato" ? `Anoté tu ${dato}. ${res.mensaje}`
      : res.color === "verde" ? `Anoté tu ${dato}. Está normal 👍 Sigue así.`
      : res.color === "amarillo" ? `Anoté tu ${dato}, ${PALABRA.amarillo}. ${res.mensaje}\n¿Quieres que te explique qué puede estar pasando? Pregúntame *¿por qué?*`
      : `Anoté tu ${dato} y está ${PALABRA.rojo}. ${res.mensaje} No tienes que manejarlo solo: escríbeme *¿qué hago?* y te guío paso a paso.`;
    chat.decir(texto, res.color === "rojo" && !res.sospechoso);
  }
  return res;
}

function fijar(nombre, valor, color) {
  const i = indicador(estado, nombre);
  if (i) Object.assign(i, { valor, color, antiguedad_min: 0 });
}

// ---------- Reloj de misión ----------
function reloj() {
  const inicio = Date.now() - (180 * 86400 + 4 * 3600 + 12 * 60) * 1000;   // día 180 de misión (demo)
  const pinta = () => {
    const s = Math.floor((Date.now() - inicio) / 1000);
    const d = Math.floor(s / 86400), h = Math.floor(s / 3600) % 24, m = Math.floor(s / 60) % 60, ss = s % 60;
    $("#met").textContent = `${d} d ${[h, m, ss].map((x) => String(x).padStart(2, "0")).join(":")}`;
  };
  pinta();
  setInterval(pinta, 1000);
}

// ---------- Conexión con la Tierra ----------
const RETRASO_MARTE_MIN = 14;   // en la demo 1 minuto = 1 segundo

function pintarSenal() {
  $("#btnSenal").setAttribute("aria-pressed", String(conectado));
  $("#txtSenal").textContent = conectado ? "Enlace con la Tierra" : "Sin enlace · modo autónomo";
  document.documentElement.classList.toggle("sin-senal", !conectado);
}

function enviarTierra() {
  const caja = $("#estadoTierra");
  if (!conectado) {
    enCola += 1;
    caja.textContent = `Resumen en cola (${enCola}). Se enviará solo cuando vuelva la señal.`;
    return;
  }
  const n = Math.max(enCola, 1);
  enCola = 0;
  caja.innerHTML = `Enviando ${n === 1 ? "resumen" : `${n} resúmenes`} · llega en ${RETRASO_MARTE_MIN} min (demo: ${RETRASO_MARTE_MIN} s)…
    <div class="barra-envio" role="progressbar" aria-label="Envío a la Tierra"><i></i></div>`;
  caja.querySelector("i").animate([{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], { duration: RETRASO_MARTE_MIN * 1000, fill: "forwards" })
    .finished.then(() => { caja.textContent = "Resumen recibido en la Tierra. La respuesta tardará otro tanto; mientras, sigue las indicaciones de a bordo."; setTimeout(() => { caja.textContent = ""; }, 12000); });
}

// ---------- Formulario "Registrar medición" ----------
const EJEMPLO = { pulso: "72", presion_arterial: "120/80", oxigeno: "98", glucosa: "90", temperatura: "36.6", sueno: "7", animo: "4", estres: "2" };
function iniciarRegistro() {
  const dlg = $("#dlgRegistro"), sel = $("#regIndicador"), val = $("#regValor"), ayuda = $("#regAyuda"), res = $("#regResultado");
  sel.innerHTML = Object.keys(EJEMPLO).filter((n) => reglas[n]).map((n) => `<option value="${n}">${escapar(reglas[n].nombre)}${reglas[n].unidad ? ` (${escapar(reglas[n].unidad)})` : ""}</option>`).join("");
  const organoDe = (n) => Object.keys(ORGANOS).find((o) => ORGANOS[o].indicadores.includes(n));
  const pintarAyuda = () => {
    const n = sel.value, r = reglas[n];
    val.placeholder = `Ej.: ${EJEMPLO[n]}…`;
    val.inputMode = n === "presion_arterial" ? "text" : "decimal";
    $("#regComoMedir").dataset.orientacion = n;   // abre la guía de medición de ese indicador
    const rango = r?.verde ? `${r.verde[0]}–${r.verde[1]}` : `${r.componentes.sistolica.verde.join("–")} / ${r.componentes.diastolica.verde.join("–")}`;
    ayuda.innerHTML = `<span class="rango">Rango ilustrativo verde: ${rango} ${escapar(r?.unidad ?? "")}</span>`
      + (n === "glucosa" ? "<br>El rango es de ayunas: indica abajo si comiste antes de medir." : "");
    res.textContent = "";
  };
  sel.addEventListener("change", pintarAyuda);
  window.abrirRegistro = (n) => {
    if (n && reglas[n]) sel.value = n;
    pintarAyuda(); val.value = ""; res.textContent = ""; $("#regContexto").value = "";
    dlg.showModal(); val.focus();
  };
  $("#btnRegistrar").addEventListener("click", () => window.abrirRegistro(seleccionado ? (fichas[seleccionado]?.indicadores ?? [])[0] : null));
  $("#regCancelar").addEventListener("click", () => dlg.close());
  $("#formRegistro").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const boton = $("#regGuardar");
    boton.disabled = true; boton.textContent = "Guardando…";
    try {
      const r = await registrar(sel.value, val.value, { contexto: $("#regContexto").value });
      dlg.close();
      seleccionar(organoDe(r.indicador));
    } catch (e) {
      res.textContent = e.message;
      val.focus();
    } finally {
      boton.disabled = false; boton.textContent = "Guardar";
    }
  });
}

// ---------- Guía de primeros pasos (se muestra una vez) ----------
function iniciarGuia() {
  const guia = $("#guia");
  let visto = false;
  try { visto = localStorage.getItem("guia-vista") === "1"; } catch { /* sin almacenamiento */ }
  guia.hidden = visto || location.search.includes("quieto");
  $("#guiaCerrar").addEventListener("click", () => {
    guia.hidden = true;
    try { localStorage.setItem("guia-vista", "1"); } catch { /* sin almacenamiento */ }
  });
}

// ---------- Inicio ----------
async function iniciar() {
  const [e, f, r, n, c, h] = await Promise.all([cargarEstado(), cargarFichas(), json("/api/reglas"), json("/api/nasa/osd575"), json("/api/clima-espacial"), json("/api/historial/A1")]);
  estado = e; fichas = f; nasa = n; clima = c;
  fijarSeries(h);
  reglas = Object.fromEntries((r?.indicadores ?? []).map((x) => [x.indicador, x]));
  inicial = structuredClone(estado);

  $("#oriGrande").innerHTML = avatarORI(40);
  // Modo conversación: el chat ocupa media pantalla (o toda en móvil). Esc vuelve.
  const btnAmpliar = $("#btnAmpliar");
  function ampliarChat(si) {
    document.body.classList.toggle("chat-amplio", si);
    btnAmpliar.setAttribute("aria-pressed", String(si));
    btnAmpliar.setAttribute("aria-label", si ? "Reducir la conversación" : "Ampliar la conversación");
    btnAmpliar.querySelector(".txt-ampliar").textContent = si ? "Reducir" : "Ampliar";
  }
  btnAmpliar.addEventListener("click", () => ampliarChat(!document.body.classList.contains("chat-amplio")));
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && document.body.classList.contains("chat-amplio") && !document.querySelector("dialog[open]")) ampliarChat(false);
  });

  chat = crearChat({
    lista: $("#mensajes"), formulario: $("#formChat"), entrada: $("#pregunta"), boton: $("#enviar"),
    sugerencias: $("#sugerencias"), obtenerEstado: () => estado, obtenerConexion: () => conectado, alEmergencia: () => ampliarChat(true),
    estadoORI: (e, texto) => {
      const av = $("#oriGrande .ori");
      av.classList.toggle("pensando", e === "pensando");
      av.classList.toggle("alerta", e === "alerta");
      $("#oriEstado").textContent = texto;
      $("#oriEstado").dataset.estado = e;
    },
  });

  const lienzo = $("#lienzo");
  const { webglDisponible, crearVisor } = await import("./visor3d.js");
  if (webglDisponible()) {
    hud = crearHud({ contenedor: lienzo, obtenerEstado: () => estado, obtenerFichas: () => fichas, onSeleccion: seleccionar });
    try {
      visor = await crearVisor(lienzo, {
        onSeleccion: seleccionar,
        onHover: (o, p) => hud.hover(o, p),
        onFrame: (proyectar) => {
          // Atajo para capturas y demo: #hover-corazon simula el mouse sobre un órgano.
          const h = location.hash.match(/^#hover-(\w+)/)?.[1];
          if (h && ORGANOS[h]) { const p = proyectar(h); if (p) hud.hover(h, { x: p.x - 10, y: p.y }); }
          hud.marco(proyectar);
        },
      });
    } catch (err) { console.error(err); $("#sinWebgl").hidden = false; }
  } else {
    $("#sinWebgl").hidden = false;
    $(".herramientas").hidden = true;
  }

  document.body.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-organo]");
    if (b) seleccionar(b.dataset.organo);
    const reg = ev.target.closest("[data-registrar]");
    if (reg) window.abrirRegistro?.(reg.dataset.registrar);
    const p = ev.target.closest("[data-preguntar]");
    if (p) {
      chat.preguntar(`¿Cómo está mi ${nombreOrgano(p.dataset.preguntar).toLowerCase()} y qué debo hacer?`);
      $("#chat").focus({ preventScroll: false });
    }
    const c = ev.target.closest("[data-capa]");
    if (c && visor) {
      const activo = c.getAttribute("aria-pressed") !== "true";
      c.setAttribute("aria-pressed", String(activo));
      visor.capa(c.dataset.capa, activo);
    }
  });
  $("#btnEtiquetas").addEventListener("click", (ev) => {
    const activo = ev.currentTarget.getAttribute("aria-pressed") !== "true";
    ev.currentTarget.setAttribute("aria-pressed", String(activo));
    hud?.etiquetas(activo);
  });
  $("#btnGirar").addEventListener("click", (ev) => {
    if (!visor) return;
    const activo = visor.girar(ev.currentTarget.getAttribute("aria-pressed") !== "true");
    ev.currentTarget.setAttribute("aria-pressed", String(activo));
  });
  $("#btnCentrar").addEventListener("click", () => seleccionar(null));

  $("#btnSenal").addEventListener("click", () => { conectado = !conectado; pintarSenal(); if (conectado && enCola) enviarTierra(); });
  $("#btnTierra").addEventListener("click", enviarTierra);
  $("#pulso").addEventListener("input", (ev) => { $("#vPulso").textContent = `${ev.target.value} lpm`; });
  $("#pulso").addEventListener("change", (ev) => registrar("pulso", ev.target.value));
  $("#btnEmergencia").addEventListener("click", async () => {
    await registrar("pulso", 148, { comentar: false });
    await registrar("oxigeno", 88, { comentar: false });
    await registrar("animo", 1, { comentar: false });
    seleccionar("corazon");
    chat.decir("Estoy contigo. Detecté **3 indicadores en alerta**: pulso 148 lpm, oxígeno 88 % y ánimo 1/5. Es posible que notes el corazón acelerado, falta de aire o mareo.\n**Avisa ahora a un compañero o al oficial médico** para que no estés solo.\nEscríbeme *¿qué hago?* y te guío paso a paso.", true);
  });
  $("#btnTormenta").addEventListener("click", () => {
    const i = indicador(estado, "radiacion");
    if (i) Object.assign(i, { valor: "SEP · ahora", color: "rojo", antiguedad_min: 0, motivo: "Evento de partículas solares (simulado).", accion: "Ve al área protegida de la nave según el protocolo y revisa tu dosímetro." });
    refrescar(); seleccionar("radiacion");
  });
  $("#btnReiniciar").addEventListener("click", async () => {
    const r = await fetch("/api/demo/reiniciar", { method: "POST" }).catch(() => null);
    if (r?.ok) { estado = await r.json(); fijarSeries(await json("/api/historial/A1")); } else { estado = structuredClone(inicial); }
    refrescar(); seleccionar(null);
  });
  iniciarRegistro();
  iniciarGuia();
  // Actualización en vivo (sensor simulado o registros desde otro equipo): cada 15 s si la pestaña está visible.
  setInterval(async () => {
    if (document.hidden) return;
    const e = await json("/api/estado/A1");
    if (!e || JSON.stringify(e.indicadores.map((i) => [i.indicador, i.valor])) === JSON.stringify(estado.indicadores.map((i) => [i.indicador, i.valor]))) return;
    const rojosAntes = new Set(estado.indicadores.filter((i) => i.color === "rojo").map((i) => i.indicador));
    estado = e; fijarSeries(await json("/api/historial/A1")); refrescar();
    const nuevos = e.indicadores.filter((i) => i.color === "rojo" && !rojosAntes.has(i.indicador));
    if (nuevos.length) chat.decir(`Ojo: tu **${NOMBRES_INDICADORES[nuevos[0].indicador] ?? nuevos[0].indicador}** acaba de pasar a alerta (${nuevos[0].valor} ${nuevos[0].unidad}). Estoy aquí contigo.\n**Avisa ahora a un compañero o al oficial médico** para que no estés solo.\nEscríbeme *¿qué hago?* y te guío paso a paso.`, true);
  }, 15000);

  reloj();
  pintarSenal();
  refrescar();
  seleccionar(new URLSearchParams(location.search).get("organo"));
  if (visor) {
    const gira = visor.girar(!new URLSearchParams(location.search).get("organo") && !location.search.includes("quieto"));
    $("#btnGirar").setAttribute("aria-pressed", String(gira));
  }
  if (location.hash === "#emergencia") $("#btnEmergencia").click();
  if (location.hash === "#sinsenal") $("#btnSenal").click();
  // Atajo para la demo: #preguntar=texto hace la pregunta al cargar.
  const auto = location.hash.match(/^#preguntar=(.+)/);
  if (auto) chat.preguntar(decodeURIComponent(auto[1]));
  document.documentElement.classList.add("listo");
}

iniciar();
