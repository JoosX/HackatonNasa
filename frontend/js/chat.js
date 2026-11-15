// Chat con ORI, el compañero de salud a bordo (POST /api/chat).
// Código escrito con asistencia de IA (Claude); revisado por el equipo.
import { L, LOCALE } from "./i18n.js";
import * as voz from "./voz.js";

const MODOS = {
  ia_local: L("IA local", "Local AI"),
  ia_nube: L("Gemini · solo demo en línea", "Gemini · online demo only"),
  respaldo_sin_ia: L("Guías (sin IA)", "Guides (no AI)"),
  sin_informacion: L("Sin guía", "No guide"),
  resumen: L("Resumen de tus datos", "Summary of your data"),
  conversacion: "ORI",
  protocolo: L("Protocolo · sin IA", "Protocol · no AI"),
  emergencia: L("Emergencia · sin IA", "Emergency · no AI"),
  emergencia_companero: L("Emergencia · sin IA", "Emergency · no AI"),
};

// Avatar de ORI: casco con visor, ojos que parpadean, antena de estado y línea de pulso.
// Estados por clase: .pensando (escanea), .alerta (visor rojo), .habla (pulso activo).
export function avatarORI(tam = 32, extra = "") {
  return `<svg class="ori ${extra}" width="${tam}" height="${tam}" viewBox="0 0 40 40" aria-hidden="true">
    <line x1="20" y1="1.5" x2="20" y2="5" class="ori-mastil"/>
    <circle cx="20" cy="2.2" r="1.6" class="ori-antena"/>
    <circle cx="20" cy="21" r="16" class="ori-casco"/>
    <rect x="8.5" y="12.5" width="23" height="14" rx="7" class="ori-visor"/>
    <g class="ori-ojos"><rect x="14" y="16.5" width="3.4" height="5.6" rx="1.7"/><rect x="22.6" y="16.5" width="3.4" height="5.6" rx="1.7"/></g>
    <rect x="11" y="18.6" width="5" height="1.6" rx=".8" class="ori-escaneo"/>
    <path d="M13 31.5h4l1.6-2.6 2.2 4.6 1.6-2.4H27" class="ori-pulso"/>
  </svg>`;
}

const escapar = (t) => t.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const enLinea = (t) => escapar(t).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|\s)\*(\S.*?\S)\*(?=\s|[.,!?]|$)/g, "$1<em>$2</em>");

// Convierte el texto en bloques: párrafos y listas ("- " o "* "). Cada bloque aparece con un leve retraso.
function bloques(texto) {
  const salida = [];
  let lista = null, tipo = "ul";
  const cerrar = () => { if (lista) { salida.push(`<${tipo}>${lista.join("")}</${tipo}>`); lista = null; } };
  for (const linea of texto.split("\n")) {
    const l = linea.trim();
    const item = l.match(/^([-*•]|\d+[.)])\s+(.*)/);
    if (item) {
      const t = /^\d/.test(item[1]) ? "ol" : "ul";   // pasos numerados = lista ordenada
      if (lista && t !== tipo) cerrar();
      tipo = t;
      const conIcono = /^(🟢|🟡|🔴)/u.test(item[2]);   // el círculo de color ya hace de viñeta
      (lista ??= []).push(`<li${conIcono ? ' class="sin-marca"' : ""}>${enLinea(item[2])}</li>`);
      continue;
    }
    cerrar();
    if (/^\*\*[^*]+\*\*$/.test(l)) salida.push(`<p class="titulo-bloque">${enLinea(l)}</p>`);   // "**Qué hacer**"
    else if (l) salida.push(`<p>${enLinea(l)}</p>`);
  }
  cerrar();
  return salida.map((b, i) => b.replace(/^<(p|ul|ol)( class="([^"]*)")?>/, (_, e, __, c) =>
    `<${e} class="aparece${c ? " " + c : ""}" style="--d:${i * 90}ms">`)).join("");
}

// Motor de IA: "local" (Ollama, sin internet) o "nube" (Gemini). La elección se recuerda en este navegador.
const CLAVE_MOTOR = "ori-motor-ia";
let motor = null;
function leerMotor() { try { return localStorage.getItem(CLAVE_MOTOR); } catch { return null; } }
function guardarMotor(m) { try { localStorage.setItem(CLAVE_MOTOR, m); } catch { /* sin almacenamiento: solo esta sesión */ } }
export function motorElegido() { return motor; }

/** Conecta los botones Local / Gemini con lo que el servidor tiene disponible (GET /api/ia/estado). */
export async function iniciarSelectorMotor(grupo) {
  if (!grupo) return;
  const botones = [...grupo.querySelectorAll("[data-motor]")];
  let estado = null;
  try { const r = await fetch("/api/ia/estado", { signal: AbortSignal.timeout(4000) }); estado = r.ok ? await r.json() : null; } catch { /* sin servidor */ }
  const hay = { local: !!estado?.ollama, nube: !!estado?.nube };
  if (!hay.local && !hay.nube) { grupo.hidden = true; return; }   // sin IA: ORI usa las guías (modo respaldo)
  let aviso = grupo.querySelector(".motor-aviso");
  if (!aviso) { aviso = document.createElement("span"); aviso.className = "motor-aviso"; grupo.append(aviso); }
  const marcar = (m) => {
    motor = m;
    botones.forEach((b) => b.setAttribute("aria-checked", String(b.dataset.motor === m)));
    aviso.textContent = m === "nube"
      ? L("En la nave ORI usa la IA local, sin internet", "On the spacecraft ORI uses local AI, no internet")
      : L("Sin internet, como en la nave", "No internet, as on the spacecraft");
  };
  botones.forEach((b) => {
    b.disabled = !hay[b.dataset.motor];
    if (b.disabled) b.title += L(" · no disponible en este servidor", " · not available on this server");
    b.addEventListener("click", () => { if (!b.disabled) { marcar(b.dataset.motor); guardarMotor(b.dataset.motor); } });
  });
  const guardado = leerMotor();
  marcar(hay[guardado] ? guardado : hay.local ? "local" : "nube");
}

export function crearChat({ lista, formulario, entrada, boton, sugerencias, obtenerEstado, obtenerConexion, estadoORI, alEmergencia }) {
  let ocupado = false;
  const textos = new WeakMap();   // mensaje -> texto original (para leerlo en voz alta)
  const fijarEstado = (estado, texto) => estadoORI?.(estado, texto);

  function mensajeORI(html, clase = "") {
    const li = document.createElement("li");
    li.className = `msg msg-ia ${clase}`.trim();
    li.innerHTML = `${avatarORI(28)}<div class="burbuja"><p class="quien">ORI</p><div class="cuerpo">${html}</div></div>`;
    lista.append(li);
    lista.scrollTop = lista.scrollHeight;
    return li;
  }

  function mensajeTuyo(texto) {
    const li = document.createElement("li");
    li.className = "msg msg-yo";
    li.innerHTML = `<div class="burbuja"><p class="quien">${L("Tú", "You")}</p><div class="cuerpo"><p>${enLinea(texto)}</p></div></div>`;
    lista.append(li);
    lista.scrollTop = lista.scrollHeight;
  }

  async function preguntar(texto) {
    const pregunta = texto.trim();
    if (!pregunta || ocupado) return;
    ocupado = true;
    boton.disabled = true;
    boton.setAttribute("aria-busy", "true");
    mensajeTuyo(pregunta);
    const li = mensajeORI(`<p class="pensando">${L("Revisando tus datos y las guías", "Checking your data and the guides")}<span class="puntos"><i></i><i></i><i></i></span></p>`, "esperando");
    li.querySelector(".ori").classList.add("pensando");
    fijarEstado("pensando", L("Revisando las guías…", "Checking the guides…"));
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ astronauta_id: "A1", pregunta, estado: obtenerEstado(), conectado: obtenerConexion?.() ?? true, motor: motorElegido() }),
        signal: AbortSignal.timeout(90000),   // si la IA tarda demasiado, se avisa en vez de esperar sin fin
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      // Las fuentes se muestran aparte; se quita una línea "Fuente:" si el modelo la escribió.
      const texto = d.respuesta.replace(/\n*\s*(\d\)\s*)?(Fuente|Source):[^\n]*\s*$/i, "").trim();
      const fuentes = d.fuentes.length
        ? `<details class="fuentes aparece" style="--d:${(texto.split("\n").length) * 90}ms"><summary>${L(`Basado en ${d.fuentes.length} guía${d.fuentes.length > 1 ? "s" : ""} de a bordo`, `Based on ${d.fuentes.length} onboard guide${d.fuentes.length > 1 ? "s" : ""}`)}</summary>
            <ul>${d.fuentes.map((f) => `<li>${escapar(f.guia)} · ${escapar(f.seccion)}</li>`).join("")}</ul></details>`
        : "";
      li.className = `msg msg-ia${d.alerta_roja ? " msg-alerta" : ""}`;
      const av = li.querySelector(".ori");
      av.classList.remove("pensando");
      av.classList.toggle("alerta", !!d.alerta_roja);
      av.classList.add("habla");
      setTimeout(() => av.classList.remove("habla"), 2400);
      const recorrido = /^(protocolo|emergencia)/.test(d.modo)
        ? `<button type="button" class="btn btn-peligro btn-recorrido aparece" data-abrir-urgente="pulso">${L("Abrir recorrido paso a paso (¿responde? ¿respira?)", "Open step-by-step walkthrough (responding? breathing?)")}</button>` : "";
      li.querySelector(".cuerpo").innerHTML = `${bloques(texto)}${recorrido}${fuentes}
        <p class="meta"><button type="button" class="btn-leer" aria-label="${L("Leer en voz alta", "Read aloud")}" title="${L("Leer en voz alta", "Read aloud")}">🔊</button>
        <span class="chip-modo" data-modo="${d.modo}">${MODOS[d.modo] ?? d.modo}</span>
        <span>${Number(d.segundos).toLocaleString(LOCALE, { maximumFractionDigits: 1 })}&nbsp;s · ${L("sin internet", "no internet")}</span></p>`;
      fijarEstado(d.alerta_roja ? "alerta" : "listo", d.alerta_roja ? L("Hay una alerta activa", "A warning is active") : L("En línea · sin internet", "Online · no internet needed"));
      textos.set(li, texto);
      if (/^(protocolo|emergencia)/.test(d.modo)) {
        alEmergencia?.();                                   // en una emergencia, el chat se amplía
        voz.alertar(voz.resumenEmergencia(texto));          // alarma y, en voz alta, qué pasa y a quién llamar
      }
    } catch (e) {
      li.className = "msg msg-ia msg-error";
      li.querySelector(".ori").classList.remove("pensando");
      li.querySelector(".cuerpo").innerHTML = `<p>${e.name === "TimeoutError"
        ? L("Perdón, me tardé demasiado en pensar. ¿Me lo preguntas otra vez? La segunda vez suelo ser más rápido.", "Sorry, I took too long to think. Could you ask me again? I'm usually faster the second time.")
        : L("Uy, no logro conectarme con mi sistema local. Revisa que el servidor esté encendido y vuelve a intentarlo.", "Oops, I can't reach my local system. Check that the server is running and try again.")}</p>`;
      fijarEstado("listo", L("Sin respuesta del sistema", "No response from the system"));
    } finally {
      ocupado = false;
      boton.disabled = false;
      boton.removeAttribute("aria-busy");
      // Mostrar el COMIENZO de la respuesta de ORI (no el final), para leerla de arriba abajo.
      lista.scrollTop = Math.max(0, li.offsetTop - lista.offsetTop - 8);
    }
  }

  // El cuadro de texto crece con lo que escribes (hasta 5 líneas). Enter envía; Shift+Enter, nueva línea.
  const crecer = () => {
    entrada.style.height = "auto";
    const alto = entrada.scrollHeight + 2;   // + borde
    entrada.style.height = `${Math.min(alto, 132)}px`;
    entrada.style.overflowY = alto > 132 ? "auto" : "hidden";
  };
  entrada.addEventListener("input", crecer);
  entrada.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); formulario.requestSubmit(); }
  });
  formulario.addEventListener("submit", () => requestAnimationFrame(crecer));

  // Botón "↓ Último mensaje" cuando subiste a leer algo anterior.
  const abajo = document.getElementById("btnAbajo");
  const revisarAbajo = () => { if (abajo) abajo.hidden = lista.scrollHeight - lista.scrollTop - lista.clientHeight < 80; };
  lista.addEventListener("scroll", revisarAbajo, { passive: true });
  new MutationObserver(revisarAbajo).observe(lista, { childList: true, subtree: true });
  abajo?.addEventListener("click", () => lista.scrollTo({ top: lista.scrollHeight, behavior: "smooth" }));

  formulario.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const t = entrada.value;
    entrada.value = "";
    preguntar(t);
  });
  sugerencias?.addEventListener("click", (ev) => {
    const b = ev.target.closest("button[data-pregunta]");
    if (b) preguntar(b.dataset.pregunta);
  });

  // Mensaje de bienvenida.
  mensajeORI(bloques(L("¡Hola! Soy **ORI**, tu compañero de salud a bordo.\n"
    + "Puedo decirte **cómo estás**, orientarte si te sientes mal y explicarte tus indicadores. "
    + "Funciono sin internet y te muestro de qué guía de NASA saco cada consejo.\nCuéntame, ¿cómo te sientes hoy?",
    "Hi! I'm **ORI**, your onboard health companion.\n"
    + "I can tell you **how you're doing**, guide you if you feel unwell and explain your indicators. "
    + "I work without internet and show you which NASA guide each piece of advice comes from.\nTell me, how are you feeling today?")));

  // Leer en voz alta una respuesta (botón 🔊 de cada mensaje).
  lista.addEventListener("click", (ev) => {
    const b = ev.target.closest(".btn-leer");
    if (!b) return;
    const li = b.closest("li");
    if (!voz.hablar(textos.get(li) ?? li.querySelector(".cuerpo").innerText, { forzar: true })) {
      b.title = L("Este equipo no tiene voces instaladas", "This device has no voices installed");
    }
  });

  // Micrófono: clic para grabar, clic para enviar. Whisper transcribe en el servidor local.
  const mic = document.getElementById("btnMic");
  let grabacion = null;
  voz.micDisponible().then((si) => { if (mic) mic.hidden = !si; });
  voz.comprobarVozServidor();   // saber pronto si ORI tiene voz propia (Piper) en este servidor
  mic?.addEventListener("click", async () => {
    if (ocupado) return;
    if (!grabacion) {
      try {
        grabacion = await voz.grabar();
      } catch {
        fijarEstado("listo", L("No hay permiso para usar el micrófono", "Microphone permission denied"));
        return;
      }
      voz.callar();
      mic.setAttribute("aria-pressed", "true");
      mic.classList.add("grabando");
      fijarEstado("pensando", L("Escuchando… toca el micrófono para enviar", "Listening… tap the microphone to send"));
      grabacion.fin.then(() => { if (mic.classList.contains("grabando")) mic.click(); });   // tope de 30 s
      return;
    }
    const g = grabacion;
    grabacion = null;
    mic.classList.remove("grabando");
    mic.setAttribute("aria-pressed", "false");
    mic.disabled = true;
    fijarEstado("pensando", L("Transcribiendo tu voz en esta computadora…", "Transcribing your voice on this computer…"));
    try {
      const textoVoz = (await voz.transcribir(await g.detener())).trim();
      if (textoVoz) preguntar(textoVoz);
      else fijarEstado("listo", L("No te escuché bien, ¿lo repites?", "I didn't catch that, could you repeat it?"));
    } catch (e) {
      fijarEstado("listo", e.message || L("No se pudo transcribir", "Could not transcribe"));
    } finally {
      mic.disabled = false;
    }
  });

  // ORI comenta por iniciativa propia (al registrar una medición o si aparece una alerta).
  function decir(texto, alerta = false) {
    const li = mensajeORI(bloques(texto), alerta ? "msg-alerta" : "");
    textos.set(li, texto);
    if (alerta) voz.alertar(texto.split(/\n/)[0]);   // alarma y la primera frase en voz alta
    const av = li.querySelector(".ori");
    av.classList.toggle("alerta", alerta);
    av.classList.add("habla");
    setTimeout(() => av.classList.remove("habla"), 2400);
  }

  return { preguntar, decir };
}
