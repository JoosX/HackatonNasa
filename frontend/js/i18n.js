// Idioma de la app: español o inglés.
// Orden de elección: ?lang=en|es en el enlace > lo elegido antes en este navegador > inglés (por defecto,
// porque el jurado de Space Apps evalúa en inglés).
// El servidor recibe el idioma en una cookie (todas las peticiones lo llevan), así ORI, las guías y las reglas
// responden en el mismo idioma que la interfaz.
// Código escrito con asistencia de IA (Claude); revisado por el equipo.

const IDIOMAS = ["es", "en"];
const enNavegador = typeof window !== "undefined" && typeof document !== "undefined";   // en Node (pruebas): español
const delEnlace = enNavegador ? new URLSearchParams(location.search).get("lang") : null;
let guardado = null;
try { guardado = enNavegador ? localStorage.getItem("idioma") : null; } catch { /* sin almacenamiento */ }
const POR_DEFECTO = enNavegador ? "en" : "es";   // en Node (pruebas de Romario) se mantiene el español

export const IDIOMA = IDIOMAS.includes(delEnlace) ? delEnlace : IDIOMAS.includes(guardado) ? guardado : POR_DEFECTO;
export const EN = IDIOMA === "en";
export const LOCALE = EN ? "en-US" : "es";
/** Texto en el idioma activo: L("Hola", "Hello"). */
export const L = (es, en) => (EN ? en : es);

if (enNavegador) {
  try { localStorage.setItem("idioma", IDIOMA); } catch { /* sin almacenamiento */ }
  document.cookie = `idioma=${IDIOMA}; path=/; max-age=31536000; SameSite=Lax`;
  document.documentElement.lang = IDIOMA;
}

/** Cambia de idioma recargando la página (los datos viven en el servidor, no se pierde nada). */
export function cambiarIdioma(nuevo) {
  if (!IDIOMAS.includes(nuevo) || nuevo === IDIOMA) return;
  try { localStorage.setItem("idioma", nuevo); } catch { /* sin almacenamiento */ }
  document.cookie = `idioma=${nuevo}; path=/; max-age=31536000; SameSite=Lax`;
  const url = new URL(location.href);
  url.searchParams.set("lang", nuevo);
  location.href = url.toString();
}

// Textos fijos de index.html en inglés: [selector, propiedad, texto]. La página está escrita en español.
const PAGINA_EN = [
  ["meta[name=description]", "content", "Local health assistant for astronauts: traffic-light monitoring, 3D body and an assistant that works without a link to Earth."],
  ["title", "text", "Health copilot · Prototype"],
  [".saltar", "text", "Skip to the assistant"],
  [".marca .nombre", "text", "Health copilot"],
  [".marca .sub", "text", "Prototype · NASA Space Apps 2026"],
  [".mision div:nth-child(1) dt", "text", "Crew member"],
  [".mision div:nth-child(1) dd", "text", "A1 · Cmdr."],
  [".mision div:nth-child(2) dt", "text", "Mission elapsed time"],
  [".mision div:nth-child(3) dt", "text", "Delay to Earth"],
  ["#btnRegistrar", "text", "+ Log measurement"],
  ["#abrirUrgente", "text", "Urgent guidance"],
  ["#abrirUrgente", "title", "Step-by-step walkthrough: works without the server, AI or Earth"],
  ["#cw", "aria-label", "Caution and warning summary"],
  ["#t-visor", "text", "Astronaut health status"],
  [".hud-rotulo span:first-child", "text", "Body · 3D view"],
  ["#guia .rotulo", "text", "Getting started"],
  ["#guia li:nth-child(1)", "html", "<b>Tap an organ</b> or a label to see how it is doing and what it means."],
  ["#guia li:nth-child(2)", "html", "<b>Log your vitals</b> with the <span class=\"tecla\">+ Log measurement</span> button."],
  ["#guia li:nth-child(3)", "html", "<b>Tell ORI</b> how you feel: it tells you what to do, even without internet."],
  ["#guiaCerrar", "text", "Got it"],
  ["#sinWebgl", "text", "This device has no WebGL. Use the organ list in the panel or open the page in Chrome or Chromium."],
  [".herramientas", "aria-label", "Body view"],
  [".grupo-capas:nth-child(1)", "aria-label", "Layers"],
  ["[data-capa=piel]", "text", "Skin"],
  ["[data-capa=huesos]", "text", "Skeleton"],
  ["[data-capa=sangre]", "text", "Vessels"],
  ["[data-capa=organos]", "text", "Organs"],
  [".grupo-capas:nth-child(2)", "aria-label", "Controls"],
  ["#btnEtiquetas", "text", "Labels"],
  ["#btnGirar", "text", "Rotate"],
  ["#btnCentrar", "text", "Center"],
  [".ayuda", "text", "Drag to rotate · scroll to zoom · tap an organ"],
  ["#signos", "aria-label", "Vital signs"],
  ["#ficha", "aria-label", "Organ details"],
  ["#t-chat", "text", "ORI · health companion"],
  ["#oriEstado", "text", "Online · no internet needed"],
  ["#motorIA", "aria-label", "AI engine"],
  ["[data-motor=local]", "title", "Local AI (Ollama): works without internet, as on the spacecraft"],
  ["[data-motor=nube]", "title", "Gemini (Google AI Studio): over the internet, for the online demo"],
  ["[data-motor=nube]", "text", "Gemini · demo only"],
  ["[data-motor=local]", "text", "Local · onboard"],
  ["#btnTierra", "title", "Send the summary to the doctors on Earth"],
  ["#btnTierra", "aria-label", "Send the summary to Earth"],
  ["#btnTierra span", "text", "Summary to Earth"],
  ["#btnSilencio", "aria-label", "Mute voice and alarms"],
  ["#btnSilencio", "title", "Voice and alarms on"],
  ["#btnMic", "aria-label", "Talk to ORI"],
  ["#btnMic", "title", "Talk to ORI (your voice is transcribed on this computer)"],
  ["#btnAmpliar", "aria-label", "Expand the conversation"],
  ["#btnAmpliar", "title", "Expand (Esc to go back)"],
  ["#btnAmpliar .txt-ampliar", "text", "Expand"],
  ["#btnAbajo", "text", "↓ Latest message"],
  ["#sugerencias", "aria-label", "Suggested questions"],
  ["#sugerencias button:nth-child(1)", "pregunta", "My chest hurts"],
  ["#sugerencias button:nth-child(1)", "text", "My chest hurts"],
  ["#sugerencias button:nth-child(2)", "pregunta", "My crewmate fainted and is not responding"],
  ["#sugerencias button:nth-child(2)", "text", "My crewmate fainted"],
  ["#sugerencias button:nth-child(3)", "pregunta", "How am I doing?"],
  ["#sugerencias button:nth-child(3)", "text", "How am I doing?"],
  ["#sugerencias button:nth-child(4)", "pregunta", "I have a headache and slept 4 hours, what should I do?"],
  ["#sugerencias button:nth-child(4)", "text", "I have a headache"],
  ["#sugerencias button:nth-child(5)", "pregunta", "I have been feeling down for several days"],
  ["#sugerencias button:nth-child(5)", "text", "Feeling down"],
  ["#sugerencias button:nth-child(6)", "pregunta", "What can you do?"],
  ["#sugerencias button:nth-child(6)", "text", "What can you do?"],
  ["label[for=pregunta]", "text", "Type your question"],
  ["#pregunta", "placeholder", "Tell ORI how you feel…"],
  ["#enviar", "text", "Send"],
  [".pista-teclado", "text", "Enter sends · Shift + Enter, new line"],
  [".demo summary", "text", "Demo controls"],
  ["label[for=pulso]", "first", "Pulse "],
  ["#btnEmergencia", "text", "Simulate emergency"],
  ["#btnTormenta", "text", "Solar storm"],
  ["#btnReiniciar", "text", "Reset data"],
  ["#orientacionDialogo .dialogo-cabecera .rotulo", "text", "Onboard library · no need to wait for the AI"],
  ["#orientacionTitulo", "text", "Measure, understand and act"],
  ["#orientacionDialogo .dialogo-cabecera .btn", "text", "Close ×"],
  ["#orientacionDialogo .dialogo-cabecera .btn", "aria-label", "Close guidance"],
  ["#orientacionUrgente h3", "text", "Ask your crew for help now"],
  ["#orientacionUrgente p", "text", "Activate the mission protocol. Do not wait for the chat or for Earth. Educational walkthrough for adults; medical review pending."],
  [".campo-orientacion", "first", "Indicator or topic"],
  ["#orientacionSelector option[value=pulso]", "text", "Pulse / heart"],
  ["#orientacionSelector option[value=presion_arterial]", "text", "Blood pressure"],
  ["#orientacionSelector option[value=oxigeno]", "text", "Oxygen / breathing"],
  ["#orientacionSelector option[value=glucosa]", "text", "Glucose"],
  ["#orientacionSelector option[value=temperatura]", "text", "Temperature"],
  ["#orientacionSelector option[value=sueno]", "text", "Sleep"],
  ["#orientacionSelector option[value=animo]", "text", "Mood"],
  ["#orientacionSelector option[value=estres]", "text", "Stress"],
  ["#orientacionRevision", "text", "Illustrative team content · Requires clinical review · Symptoms matter even if a value looks in range."],
  ["#dlgRegistro .rotulo", "text", "Onboard database"],
  ["#t-registro", "text", "Log measurement"],
  ["label[for=regIndicador]", "text", "What did you measure?"],
  ["#regComoMedir", "text", "How do I take this measurement? →"],
  ["label[for=regValor]", "text", "Value"],
  ["label[for=regContexto]", "text", "In what situation did you take it?"],
  ["#regContexto option[value='']", "text", "Not specified"],
  ["#regContexto option[value=reposo]", "text", "At rest"],
  ["#regContexto option[value=despues_ejercicio]", "text", "After exercise"],
  ["#regContexto option[value=ayunas]", "text", "Fasting"],
  ["#regContexto option[value=despues_comida]", "text", "After eating"],
  ["#regContexto option[value=otro]", "text", "Other situation"],
  ["#regCancelar", "text", "Cancel"],
  ["#regGuardar", "text", "Save"],
  [".pie", "text", "Prototype TRL 3–4 · does not diagnose · illustrative ranges. Anatomy: BodyParts3D, © The Database Center for Life Science, CC BY 4.0. Data: NASA OSDR OSD-575, NASA DONKI (space weather) and NASA Human Research Program. Viewer: Three.js (MIT)."],
];

/** Traduce los textos fijos de la página y agrega el selector de idioma. */
export function traducirPagina() {
  if (EN) {
    for (const [sel, prop, texto] of PAGINA_EN) {
      for (const el of document.querySelectorAll(sel)) {
        if (prop === "text") el.textContent = texto;
        else if (prop === "html") el.innerHTML = texto;
        else if (prop === "pregunta") el.dataset.pregunta = texto;
        else if (prop === "first") { const n = [...el.childNodes].find((x) => x.nodeType === 3 && x.textContent.trim()); if (n) n.textContent = texto; }
        else el.setAttribute(prop, texto);
      }
    }
  }
  const barra = document.querySelector(".barra");
  if (barra && !document.querySelector(".idioma")) {
    const grupo = document.createElement("div");
    grupo.className = "idioma";
    grupo.setAttribute("role", "group");
    grupo.setAttribute("aria-label", L("Idioma", "Language"));
    grupo.innerHTML = IDIOMAS.map((i) => `<button type="button" data-idioma="${i}" aria-pressed="${i === IDIOMA}"
      title="${i === "es" ? "Español" : "English"}">${i.toUpperCase()}</button>`).join("");
    grupo.addEventListener("click", (ev) => { const b = ev.target.closest("[data-idioma]"); if (b) cambiarIdioma(b.dataset.idioma); });
    barra.append(grupo);
  }
}
