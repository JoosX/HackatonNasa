// HUD sobre el visor 3D: etiquetas anatómicas con línea guía y tarjeta al pasar el mouse.
// Código escrito con asistencia de IA (Claude); revisado por el equipo.

import { ORGANOS, COLORES, NOMBRES_INDICADORES, colorOrgano, indicador, historial, sparkline, antiguedadTexto } from "./organos.js";

const NS = "http://www.w3.org/2000/svg";
const ESTADO_TXT = { verde: "Normal", amarillo: "Precaución", rojo: "Alerta", "sin dato": "Sin dato" };
const ORDEN = ["cerebro", "ojos", "pulmones", "corazon", "sangre", "huesos", "piel"];
const escapar = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v) => (typeof v === "number" ? v.toLocaleString("es", { maximumFractionDigits: 1 }) : escapar(v));

export function crearHud({ contenedor, obtenerEstado, obtenerFichas, onSeleccion }) {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "hud-lineas");
  svg.setAttribute("aria-hidden", "true");
  const capaEtiquetas = document.createElement("div");
  capaEtiquetas.className = "hud-etiquetas";
  capaEtiquetas.setAttribute("aria-label", "Órganos");
  const tarjeta = document.createElement("div");
  tarjeta.className = "hud-tarjeta";
  tarjeta.setAttribute("role", "tooltip");
  tarjeta.hidden = true;
  contenedor.append(svg, capaEtiquetas, tarjeta);

  const lineas = {}, etiquetas = {};
  for (const o of ORDEN) {
    const g = document.createElementNS(NS, "g");
    g.innerHTML = `<polyline fill="none" stroke-width="1"/><circle r="3.5"/><circle r="8" fill="none" stroke-width="1" class="anillo"/>`;
    svg.append(g);
    lineas[o] = g;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "hud-etiqueta";
    b.dataset.organo = o;
    capaEtiquetas.append(b);
    etiquetas[o] = b;
  }
  const guiaHover = document.createElementNS(NS, "g");
  guiaHover.setAttribute("class", "hud-guia");
  guiaHover.innerHTML = `<polyline fill="none" stroke-width="1.2"/><circle r="5" class="retícula"/><circle r="13" fill="none" class="pulso-reticula"/>`;
  svg.append(guiaHover);

  let mostrarEtiquetas = true, seleccionado = null, hover = null, punto = null;
  let pos = { x: 0, y: 0 }, objetivo = { x: 0, y: 0 }, tamTarjeta = { tw: 270, th: 170 };

  function textoEtiqueta(o) {
    const e = obtenerEstado();
    const f = obtenerFichas()[o];
    const c = colorOrgano(e, o);
    const principal = (f?.indicadores ?? ORGANOS[o].indicadores).map((n) => indicador(e, n)).find(Boolean);
    const dato = principal ? `${num(principal.valor)}<small>${escapar(principal.unidad)}</small>` : "";
    etiquetas[o].style.setProperty("--c", COLORES[c]);
    etiquetas[o].dataset.estado = c;
    etiquetas[o].setAttribute("aria-label", `${f?.nombre ?? ORGANOS[o].nombre}: ${ESTADO_TXT[c]}`);
    etiquetas[o].innerHTML = `<span class="punto-estado" aria-hidden="true"></span>
      <span class="hud-nombre">${escapar(ORGANOS[o].nombre.split(" (")[0])}</span><span class="hud-dato">${dato}</span>`;
    if (etiquetas[o].offsetWidth) etiquetas[o]._ancho = etiquetas[o].offsetWidth;   // se mide una vez, no en cada cuadro
  }

  // Coloca etiquetas en dos columnas sin superponerse y dibuja la línea guía hasta el órgano.
  function marco(proyectar) {
    const w = contenedor.clientWidth, h = contenedor.clientHeight;
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    const compacto = w < 640;
    capaEtiquetas.hidden = !mostrarEtiquetas || compacto;
    const columnas = { izq: [], der: [] };
    const centrales = [];
    for (const o of ORDEN) {
      const p = mostrarEtiquetas && !compacto ? proyectar(o) : null;
      const g = lineas[o];
      if (!p || !p.delante) { g.style.display = "none"; etiquetas[o].style.display = "none"; continue; }
      g.style.display = ""; etiquetas[o].style.display = "";
      // Los órganos cerca del eje del cuerpo se reparten para equilibrar ambos lados.
      if (Math.abs(p.x - w / 2) < w * 0.06) centrales.push({ o, p });
      else (p.x < w / 2 ? columnas.izq : columnas.der).push({ o, p });
    }
    centrales.sort((a, b) => a.p.y - b.p.y);
    for (const it of centrales) (columnas.izq.length <= columnas.der.length ? columnas.izq : columnas.der).push(it);
    capaEtiquetas.classList.toggle("con-hover", !!hover);
    svg.classList.toggle("con-hover", !!hover);
    for (const [lado, lista] of Object.entries(columnas)) {
      lista.sort((a, b) => a.p.y - b.p.y);
      const alto = 40, margen = 18;
      let y = margen;
      for (const it of lista) { it.y = Math.max(y, Math.min(h - alto - 50, it.p.y - alto / 2)); y = it.y + alto + 8; }
      for (let k = lista.length - 2; k >= 0; k--) lista[k].y = Math.min(lista[k].y, lista[k + 1].y - alto - 8);
      for (const { o, p, y: ly } of lista) {
        const b = etiquetas[o];
        if (!b._ancho && b.offsetWidth) b._ancho = b.offsetWidth;
        const bw = b._ancho || 150;
        const x = lado === "izq" ? margen : w - margen - bw;
        b.style.transform = `translate(${x}px, ${ly}px)`;
        const bordeX = lado === "izq" ? x + bw : x;
        const codoX = bordeX + (lado === "izq" ? 22 : -22);
        const cy = ly + alto / 2;
        const g = lineas[o];
        const c = COLORES[b.dataset.estado] ?? COLORES["sin dato"];
        const activo = o === seleccionado || o === hover;
        g.setAttribute("class", `hud-linea${activo ? " activa" : ""}${seleccionado && !activo ? " tenue" : ""}`);
        g.style.setProperty("--c", c);
        g.children[0].setAttribute("points", `${bordeX},${cy} ${codoX},${cy} ${p.x},${p.y}`);
        for (const ci of [g.children[1], g.children[2]]) { ci.setAttribute("cx", p.x); ci.setAttribute("cy", p.y); }
        b.classList.toggle("activa", activo);
        b.classList.toggle("tenue", !!seleccionado && !activo);
      }
    }
    // Tarjeta del hover: sigue al puntero con suavidad y una línea la une al punto tocado.
    if (hover && punto) {
      pos.x += (objetivo.x - pos.x) * 0.35;
      pos.y += (objetivo.y - pos.y) * 0.35;
      tarjeta.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
      const { tw, th } = tamTarjeta;
      const ax = objetivo.lado === "der" ? pos.x : pos.x + tw;
      guiaHover.style.display = "";
      guiaHover.children[0].setAttribute("points", `${punto.x},${punto.y} ${ax},${pos.y + 22} ${ax},${pos.y + th - 12}`);
      for (const ci of [guiaHover.children[1], guiaHover.children[2]]) { ci.setAttribute("cx", punto.x); ci.setAttribute("cy", punto.y); }
    } else {
      guiaHover.style.display = "none";
    }
  }

  function contenidoTarjeta(o) {
    const e = obtenerEstado();
    const f = obtenerFichas()[o] ?? {};
    const c = colorOrgano(e, o);
    const filas = (f.indicadores ?? ORGANOS[o].indicadores).map((n) => {
      const i = indicador(e, n);
      if (!i) return "";
      return `<li style="--c:${COLORES[i.color]}">
        <span class="t-ind">${NOMBRES_INDICADORES[n]}<small>${antiguedadTexto(i.antiguedad_min)}</small></span>
        ${sparkline(historial(e, n), COLORES[i.color], 64, 20)}
        <b>${num(i.valor)}<small>${escapar(i.unidad)}</small></b></li>`;
    }).join("");
    tarjeta.style.setProperty("--c", COLORES[c]);
    tarjeta.innerHTML = `<p class="t-cab"><span class="punto-estado"></span>${escapar(f.nombre ?? ORGANOS[o].nombre)}
        <span class="t-estado">${ESTADO_TXT[c]}</span></p>
      <ul class="t-filas">${filas}</ul>
      ${f.efecto_espacio ? `<p class="t-espacio">${escapar(f.efecto_espacio)}</p>` : ""}
      <p class="t-pista">Clic para ver la ficha completa</p>`;
    tarjeta.hidden = false;
    tamTarjeta = { tw: tarjeta.offsetWidth || 270, th: tarjeta.offsetHeight || 170 };
  }

  capaEtiquetas.addEventListener("click", (ev) => {
    const b = ev.target.closest(".hud-etiqueta");
    if (b) onSeleccion(b.dataset.organo);
  });

  return {
    marco,
    actualizar() { ORDEN.forEach(textoEtiqueta); if (hover) contenidoTarjeta(hover); },
    seleccionar(o) { seleccionado = o; },
    etiquetas(v) { mostrarEtiquetas = v; },
    // Llamado por el visor al pasar el mouse sobre un órgano.
    hover(o, p) {
      const cambio = o !== hover;
      hover = o; punto = p;
      if (!o || !p) { tarjeta.hidden = true; return; }
      if (cambio) { contenidoTarjeta(o); tarjeta.hidden = false; tarjeta.classList.remove("entra"); void tarjeta.offsetWidth; tarjeta.classList.add("entra"); }
      const w = contenedor.clientWidth, h = contenedor.clientHeight;
      const { tw, th } = tamTarjeta;
      const lado = p.x < w / 2 ? "der" : "izq";
      objetivo = {
        lado,
        x: lado === "der" ? Math.min(p.x + 70, w - tw - 12) : Math.max(p.x - 70 - tw, 12),
        y: Math.max(12, Math.min(p.y - th / 2, h - th - 56)),
      };
      if (cambio) pos = { ...objetivo };
    },
  };
}
