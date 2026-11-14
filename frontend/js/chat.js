// Chat con ORI, el compañero de salud a bordo (POST /api/chat).
// Código escrito con asistencia de IA (Claude); revisado por el equipo.

const MODOS = {
  ia_local: "IA local",
  respaldo_sin_ia: "Guías (sin IA)",
  sin_informacion: "Sin guía",
  resumen: "Resumen de tus datos",
  conversacion: "ORI",
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
  let lista = null;
  for (const linea of texto.split("\n")) {
    const l = linea.trim();
    const item = l.match(/^([-*•]|\d+[.)])\s+(.*)/);
    if (item) {
      const conIcono = /^(🟢|🟡|🔴)/u.test(item[2]);   // el círculo de color ya hace de viñeta
      (lista ??= []).push(`<li${conIcono ? ' class="sin-marca"' : ""}>${enLinea(item[2])}</li>`);
      continue;
    }
    if (lista) { salida.push(`<ul>${lista.join("")}</ul>`); lista = null; }
    if (l) salida.push(`<p>${enLinea(l)}</p>`);
  }
  if (lista) salida.push(`<ul>${lista.join("")}</ul>`);
  return salida.map((b, i) => b.replace(/^<(p|ul)>/, `<$1 class="aparece" style="--d:${i * 90}ms">`)).join("");
}

export function crearChat({ lista, formulario, entrada, boton, sugerencias, obtenerEstado, estadoORI }) {
  let ocupado = false;
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
    li.innerHTML = `<div class="burbuja"><p class="quien">Tú</p><div class="cuerpo"><p>${enLinea(texto)}</p></div></div>`;
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
    const li = mensajeORI('<p class="pensando">Revisando tus datos y las guías<span class="puntos"><i></i><i></i><i></i></span></p>', "esperando");
    li.querySelector(".ori").classList.add("pensando");
    fijarEstado("pensando", "Revisando las guías…");
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ astronauta_id: "A1", pregunta, estado: obtenerEstado() }),
        signal: AbortSignal.timeout(90000),   // si la IA tarda demasiado, se avisa en vez de esperar sin fin
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      // Las fuentes se muestran aparte; se quita una línea "Fuente:" si el modelo la escribió.
      const texto = d.respuesta.replace(/\n*\s*(\d\)\s*)?Fuente:[^\n]*\s*$/i, "").trim();
      const fuentes = d.fuentes.length
        ? `<details class="fuentes aparece" style="--d:${(texto.split("\n").length) * 90}ms"><summary>Basado en ${d.fuentes.length} guía${d.fuentes.length > 1 ? "s" : ""} de a bordo</summary>
            <ul>${d.fuentes.map((f) => `<li>${escapar(f.guia)} · ${escapar(f.seccion)}</li>`).join("")}</ul></details>`
        : "";
      li.className = `msg msg-ia${d.alerta_roja ? " msg-alerta" : ""}`;
      const av = li.querySelector(".ori");
      av.classList.remove("pensando");
      av.classList.toggle("alerta", !!d.alerta_roja);
      av.classList.add("habla");
      setTimeout(() => av.classList.remove("habla"), 2400);
      li.querySelector(".cuerpo").innerHTML = `${bloques(texto)}${fuentes}
        <p class="meta"><span class="chip-modo" data-modo="${d.modo}">${MODOS[d.modo] ?? d.modo}</span>
        <span>${Number(d.segundos).toLocaleString("es", { maximumFractionDigits: 1 })}&nbsp;s · sin internet</span></p>`;
      fijarEstado(d.alerta_roja ? "alerta" : "listo", d.alerta_roja ? "Hay una alerta activa" : "En línea · sin internet");
    } catch (e) {
      li.className = "msg msg-ia msg-error";
      li.querySelector(".ori").classList.remove("pensando");
      li.querySelector(".cuerpo").innerHTML = `<p>${e.name === "TimeoutError"
        ? "Perdón, me tardé demasiado en pensar. ¿Me lo preguntas otra vez? La segunda vez suelo ser más rápido."
        : "Uy, no logro conectarme con mi sistema local. Revisa que el servidor esté encendido y vuelve a intentarlo."}</p>`;
      fijarEstado("listo", "Sin respuesta del sistema");
    } finally {
      ocupado = false;
      boton.disabled = false;
      boton.removeAttribute("aria-busy");
      // Mostrar el COMIENZO de la respuesta de ORI (no el final), para leerla de arriba abajo.
      lista.scrollTop = Math.max(0, li.offsetTop - lista.offsetTop - 8);
    }
  }

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
  mensajeORI(bloques("¡Hola! Soy **ORI**, tu compañero de salud a bordo.\n"
    + "Puedo decirte **cómo estás**, orientarte si te sientes mal y explicarte tus indicadores. "
    + "Funciono sin internet y te muestro de qué guía de NASA saco cada consejo.\nCuéntame, ¿cómo te sientes hoy?"));

  return { preguntar };
}
