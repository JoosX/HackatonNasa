// Chat con el asistente de salud local (POST /api/chat).
// Código escrito con asistencia de IA (Claude); revisado por el equipo.

const MODOS = {
  ia_local: "IA local",
  respaldo_sin_ia: "Guías (sin IA)",
  sin_informacion: "Sin información",
};

const escapar = (t) => t.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Formato mínimo: **negrita** y saltos de línea; todo lo demás se escapa.
const formatear = (t) => escapar(t).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");

export function crearChat({ lista, formulario, entrada, boton, sugerencias, obtenerEstado }) {
  let ocupado = false;

  function agregar(rol, html, clase = "") {
    const li = document.createElement("li");
    li.className = `msg msg-${rol} ${clase}`.trim();
    li.innerHTML = html;
    lista.append(li);
    lista.scrollTop = lista.scrollHeight;
    return li;
  }

  async function preguntar(texto) {
    const pregunta = texto.trim();
    if (!pregunta || ocupado) return;
    ocupado = true;
    boton.disabled = true;
    boton.setAttribute("aria-busy", "true");
    agregar("yo", formatear(pregunta));
    const pensando = agregar("ia", '<span class="pensando">Consultando las guías…</span>');
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ astronauta_id: "A1", pregunta, estado: obtenerEstado() }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const fuentes = d.fuentes.length
        ? `<ul class="fuentes">${d.fuentes.map((f) => `<li>${escapar(f.guia)} · ${escapar(f.seccion)}</li>`).join("")}</ul>`
        : "";
      pensando.className = `msg msg-ia${d.alerta_roja ? " msg-alerta" : ""}`;
      // Las fuentes se muestran como lista; se quita la línea "Fuente:" que escribe el modelo.
      const texto = d.fuentes.length ? d.respuesta.replace(/\n*\s*(\d\)\s*)?Fuente:[^\n]*\s*$/i, "").trim() : d.respuesta;
      pensando.innerHTML = `${formatear(texto)}${fuentes}
        <p class="meta"><span class="chip-modo" data-modo="${d.modo}">${MODOS[d.modo] ?? d.modo}</span>
        <span>${Number(d.segundos).toLocaleString("es", { maximumFractionDigits: 1 })}&nbsp;s · sin internet</span></p>`;
    } catch (e) {
      pensando.className = "msg msg-ia msg-error";
      pensando.textContent = "No pude conectar con el asistente local. Revisa que el servidor esté encendido (uvicorn) y vuelve a preguntar.";
    } finally {
      ocupado = false;
      boton.disabled = false;
      boton.removeAttribute("aria-busy");
      lista.scrollTop = lista.scrollHeight;
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

  return { preguntar, agregar };
}
