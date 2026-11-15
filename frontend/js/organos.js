// Datos compartidos por el cuerpo 2D y el 3D.
// Los nombres de órganos son el CONTRATO con el modelo de Blender y con P3.
// Código escrito con asistencia de IA (Claude); revisado por el equipo.

export const COLORES = { verde: "#4cb782", amarillo: "#e3a008", rojo: "#e5484d", "sin dato": "#6b6b6b" };   // código C&W de vuelo
const ORDEN = { "sin dato": 0, verde: 1, amarillo: 2, rojo: 3 };

// Qué muestra cada órgano. Textos breves basados en NASA HRP (ilustrativos; P6 los reemplaza por fichas.json).
export const ORGANOS = {
  corazon: {
    nombre: "Corazón", indicadores: ["pulso", "presion_arterial"],
    espacio: "Sin gravedad, la sangre se desplaza hacia el pecho y la cabeza; el corazón y los vasos se adaptan y la presión y el pulso pueden cambiar.",
    fuente: "NASA HRP – Cardiovascular Adaptations",
  },
  cerebro: {
    nombre: "Cerebro y ánimo", indicadores: ["animo", "estres", "sueno"],
    espacio: "El aislamiento, el encierro y los horarios irregulares afectan el sueño, el ánimo y la atención.",
    fuente: "NASA HRP – Behavioral Health; Sleep and Irregular Schedules",
  },
  pulmones: {
    nombre: "Pulmones", indicadores: ["oxigeno"],
    espacio: "El aire de la nave se recicla; niveles altos de CO₂ o bajos de oxígeno afectan la respiración y causan dolor de cabeza.",
    fuente: "NASA HRP – Hostile/Closed Environments; Hypoxia",
  },
  huesos: {
    nombre: "Huesos", indicadores: ["perdida_osea"],
    espacio: "Sin gravedad, los huesos pierden entre 1 y 1,5 % de densidad por mes si no hay ejercicio de resistencia.",
    fuente: "NASA – Risk of Spaceflight-Induced Bone Changes",
  },
  ojos: {
    nombre: "Ojos", indicadores: ["vision"],
    espacio: "El desplazamiento de líquidos hacia la cabeza puede cambiar la estructura del ojo (síndrome SANS).",
    fuente: "NASA HRP – SANS",
  },
  sangre: {
    nombre: "Sangre (glucosa)", indicadores: ["glucosa"],
    espacio: "La glucosa refleja energía y metabolismo; la dieta, el estrés y el sueño la alteran.",
    fuente: "NASA OSDR OSD-575 (Inspiration4, panel metabólico)",
  },
  radiacion: {
    nombre: "Radiación (clima espacial)", indicadores: ["radiacion"],
    espacio: "Las llamaradas y los eventos de partículas solares aumentan la dosis de radiación en pocas horas.",
    fuente: "NASA DONKI (CCMC / NASA GSFC)",
  },
  piel: {
    nombre: "Piel y temperatura", indicadores: ["temperatura"],
    espacio: "Las erupciones en la piel son el evento médico más común en la Estación Espacial (1,12 por año de vuelo).",
    fuente: "Crucian et al. 2016",
  },
};

export const NOMBRES_INDICADORES = {
  pulso: "Pulso", presion_arterial: "Presión arterial", animo: "Ánimo", estres: "Estrés",
  sueno: "Sueño", oxigeno: "Oxígeno", perdida_osea: "Pérdida ósea", vision: "Visión",
  glucosa: "Glucosa", temperatura: "Temperatura", radiacion: "Clima espacial",
};

// Estado de demostración (mismo formato que GET /api/estado de P4).
export const ESTADO_DEMO = {
  astronauta_id: "A1",
  indicadores: [
    { indicador: "pulso", valor: 96, unidad: "lpm", color: "verde", antiguedad_min: 12 },
    { indicador: "presion_arterial", valor: "142/92", unidad: "mmHg", color: "amarillo", antiguedad_min: 12 },
    { indicador: "sueno", valor: 4.5, unidad: "h", color: "amarillo", antiguedad_min: 480 },
    { indicador: "animo", valor: 2, unidad: "/5", color: "amarillo", antiguedad_min: 30 },
    { indicador: "estres", valor: 3, unidad: "/5", color: "verde", antiguedad_min: 30 },
    { indicador: "oxigeno", valor: 97, unidad: "%", color: "verde", antiguedad_min: 12 },
    { indicador: "glucosa", valor: 103, unidad: "mg/dL", color: "amarillo", antiguedad_min: 90 },
    { indicador: "temperatura", valor: 36.8, unidad: "°C", color: "verde", antiguedad_min: 60 },
    { indicador: "perdida_osea", valor: "-1,1", unidad: "%/mes", color: "amarillo", antiguedad_min: 10080 },
    { indicador: "vision", valor: "sin cambios", unidad: "", color: "verde", antiguedad_min: 4320 },
  ],
};

// Fichas de P6 (data/fichas.json vía /api/fichas). Si no hay backend, se usan los textos de ORGANOS.
export async function cargarFichas() {
  try {
    const r = await fetch("/api/fichas", { signal: AbortSignal.timeout(1500) });
    if (r.ok) return (await r.json()).fichas;
  } catch (_) { /* sin backend */ }
  return Object.fromEntries(Object.entries(ORGANOS).map(([k, o]) => [k, {
    nombre: o.nombre, indicadores: o.indicadores, efecto_espacio: o.espacio, fuente: o.fuente }]));
}

// Intenta leer el estado real de la API (P4); si no está, usa el de demostración.
export async function cargarEstado(id = "A1") {
  try {
    const r = await fetch(`/api/estado/${id}`, { signal: AbortSignal.timeout(1500) });
    if (r.ok) return await r.json();
  } catch (_) { /* sin backend: modo demo */ }
  const respaldo = structuredClone(ESTADO_DEMO);
  respaldo.indicadores.forEach(i => Object.assign(i, { valor: null, color: 'sin dato', origen: 'registro_manual', calidad: 'error', historial: [], antiguedad_min: null, motivo: 'No se pudieron cargar los registros del servidor local.' }));
  return { ...respaldo, origen: 'error' };
}

export function indicador(estado, nombre) {
  return estado.indicadores.find((i) => i.indicador === nombre);
}

// Color de un órgano = el peor color de sus indicadores.
export function colorOrgano(estado, organo) {
  if (!estado.modo_demo && ORGANOS[organo].indicadores.some(n => indicador(estado,n)?.calidad)) {
    const datos = ORGANOS[organo].indicadores.map(n => indicador(estado,n)).map(i => i?.origen === 'demo' ? null : i);
    if (datos.some(i => i?.color === 'rojo')) return 'rojo';
    if (datos.some(i => i?.color === 'amarillo')) return 'amarillo';
    return datos.every(i => i?.calidad === 'vigente' && i.color === 'verde') ? 'verde' : 'sin dato';
  }
  let peor = "sin dato";
  for (const n of ORGANOS[organo].indicadores) {
    const c = indicador(estado, n)?.color ?? "sin dato";
    if (ORDEN[c] > ORDEN[peor]) peor = c;
  }
  return peor;
}

// Regla simple de demostración para el control de pulso (el motor real de reglas es de P4).
export function colorPulso(lpm) {
  if (lpm >= 50 && lpm <= 100) return "verde";
  if (lpm >= 40 && lpm <= 120) return "amarillo";
  return "rojo";
}

// Valor numérico para graficar (la presión usa la sistólica).
export function valorNumerico(v) {
  const n = parseFloat(String(v).split("/")[0].replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

// Historial de DEMOSTRACIÓN de 7 días que termina en el valor actual (determinista, para las mini gráficas).
// P4 lo reemplaza por el historial real de SQLite.
const AMPLITUD = { pulso: 9, presion_arterial: 10, oxigeno: 1.2, glucosa: 9, temperatura: 0.25, sueno: 1.3, animo: 0.8, estres: 0.8, perdida_osea: 0.15 };
const DERIVA = { verde: 0, amarillo: 1, rojo: 2.2 };
export function historial(estado, nombre, dias = 7) {
  const i = indicador(estado, nombre);
  if (i?.calidad && !estado.modo_demo) return (i.historial ?? []).map(m => m.sospechoso ? null : m.valor);
  const actual = valorNumerico(i?.valor);
  if (actual == null) return [];
  const amp = AMPLITUD[nombre] ?? 1;
  const sube = ["sueno", "animo", "oxigeno"].includes(nombre) ? 1 : -1;   // de dónde viene la tendencia
  const deriva = DERIVA[i.color] ?? 0;
  let semilla = [...nombre].reduce((a, c) => a + c.charCodeAt(0), 0);
  const azar = () => ((semilla = (semilla * 9301 + 49297) % 233280) / 233280 - 0.5);
  const serie = Array.from({ length: dias }, (_, k) => {
    const pasos = dias - 1 - k;
    return actual + sube * deriva * amp * 0.35 * pasos + amp * 0.6 * azar() * (pasos ? 1 : 0);
  });
  serie[dias - 1] = actual;
  return serie;
}

// Mini gráfica SVG (línea + último punto).
export function sparkline(serie, color, ancho = 72, alto = 22) {
  if (serie.some(v => v == null)) return '';
  if (serie.length < 2) return "";
  const min = Math.min(...serie), max = Math.max(...serie), rango = max - min || 1;
  const pts = serie.map((v, k) => [(k / (serie.length - 1)) * (ancho - 4) + 2, alto - 3 - ((v - min) / rango) * (alto - 6)]);
  const d = pts.map(([x, y], k) => `${k ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const [ux, uy] = pts.at(-1);
  return `<svg class="spark" viewBox="0 0 ${ancho} ${alto}" width="${ancho}" height="${alto}" aria-hidden="true">
    <path d="${d}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" opacity=".9"/>
    <circle cx="${ux}" cy="${uy}" r="2.4" fill="${color}"/></svg>`;
}

export function antiguedadTexto(min) {
  if (min == null) return "";
  if (min < 60) return `hace ${min} min`;
  if (min < 1440) return `hace ${Math.round(min / 60)} h`;
  return `hace ${Math.round(min / 1440)} d`;
}

// Panel lateral compartido: muestra el órgano seleccionado.
export function pintarPanel(panel, estado, organo) {
  if (!organo) {
    panel.innerHTML = `<h2>Toca una parte del cuerpo</h2>
      <p class="sub">Cada órgano se pinta con el peor color de sus indicadores.</p>
      <ul class="leyenda">
        <li><span style="background:${COLORES.verde}"></span>Normal</li>
        <li><span style="background:${COLORES.amarillo}"></span>Atención</li>
        <li><span style="background:${COLORES.rojo}"></span>Alerta: avisa a la tripulación</li>
      </ul>`;
    return;
  }
  const o = ORGANOS[organo];
  const filas = o.indicadores.map((n) => {
    const i = indicador(estado, n);
    if (!i) return `<li><b>${NOMBRES_INDICADORES[n]}</b><span class="dato">sin dato</span></li>`;
    return `<li><b>${NOMBRES_INDICADORES[n]}</b>
      <span class="dato" style="color:${COLORES[i.color]}">${i.valor} ${i.unidad}</span>
      <small>${antiguedadTexto(i.antiguedad_min)}</small></li>`;
  }).join("");
  const c = colorOrgano(estado, organo);
  panel.innerHTML = `<h2><span class="punto" style="background:${COLORES[c]}"></span>${o.nombre}</h2>
    <ul class="datos">${filas}</ul>
    <h3>Efecto del espacio</h3><p>${o.espacio}</p>
    <p class="fuente">Fuente: ${o.fuente}</p>
    ${c === "rojo" ? '<p class="alerta">⚠️ Avisa a la tripulación y sigue el protocolo de a bordo.</p>' : ""}`;
}
