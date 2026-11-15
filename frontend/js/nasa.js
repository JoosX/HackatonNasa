import { ANALITOS, esNumero, puntosSerie, comparar, csvSerie } from "./nasa-datos.js";

const FUENTE = "https://osdr.nasa.gov/bio/repo/data/studies/OSD-575";
const ARCHIVO = "LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv";
const escapar = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const numero = v => esNumero(v) ? v.toLocaleString("es", { maximumFractionDigits: 3 }) : "Sin dato";
const opcion = (valor, texto, elegido) => `<option value="${escapar(valor)}"${valor === elegido ? " selected" : ""}>${escapar(texto)}</option>`;

function grafica(puntos, unidad, rango) {
  const validos = puntos.filter(p => esNumero(p.valor) && esNumero(p.dia));
  if (!validos.length) return '<p class="nasa-error">No hay valores numéricos para esta selección.</p>';
  const banda = Array.isArray(rango) && rango.length === 2 && rango.every(esNumero) && rango[0] <= rango[1];
  const W = 900, H = 280, iz = 65, de = 30, ar = 28, ab = 50;
  const dias = puntos.map(p => p.dia).filter(esNumero);
  const t0 = Math.min(...dias, 0), t1 = Math.max(...dias, 3);
  const vals = [...validos.map(p => p.valor), ...(banda ? rango : [])];
  const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * .16 || Math.abs(hi) * .1 || 1;
  const min = lo - pad, max = hi + pad;
  const X = v => iz + (v - t0) / (t1 - t0) * (W - iz - de);
  const Y = v => ar + (max - v) / (max - min) * (H - ar - ab);
  // Un dato ausente corta el trazo. Las distancias X representan días, no categorías equidistantes.
  let d = "", tramo = false;
  for (const p of puntos) {
    if (!esNumero(p.valor) || !esNumero(p.dia)) { tramo = false; continue; }
    d += `${tramo ? "L" : "M"}${X(p.dia).toFixed(2)},${Y(p.valor).toFixed(2)} `;
    tramo = true;
  }
  // Etiquetas alternadas verticalmente para las muestras cercanas al lanzamiento/regreso.
  const etiquetas = puntos.filter(p => esNumero(p.dia)).map((p, i) => `<line x1="${X(p.dia)}" x2="${X(p.dia)}" y1="${H-ab}" y2="${H-ab+5}" stroke="#555"/>
    <text x="${X(p.dia)}" y="${H-ab+20+(i%2)*17}" text-anchor="middle">${escapar(p.momento)}</text>`).join("");
  const rejilla = [0, .5, 1].map(k => {
    const v = min + (max - min) * k;
    return `<line x1="${iz}" x2="${W-de}" y1="${Y(v)}" y2="${Y(v)}" stroke="#262626"/><text x="${iz-10}" y="${Y(v)+4}" text-anchor="end">${numero(v)}</text>`;
  }).join("");
  return `<figure class="nasa-chart"><figcaption><span>Mediciones publicadas · ${escapar(unidad)}</span><span>${banda ? "Banda gris: referencia del laboratorio" : "Sin rango de referencia publicado"}</span></figcaption>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="nasaGraficaTitulo nasaGraficaDesc">
      <title id="nasaGraficaTitulo">Evolución histórica de las muestras seleccionadas</title>
      <desc id="nasaGraficaDesc">Eje horizontal proporcional al tiempo. Valores exactos en la tabla siguiente. La franja vertical indica los tres días de vuelo; no hay muestras durante el vuelo en este panel.</desc>
      ${banda ? `<rect x="${iz}" y="${Y(rango[1])}" width="${W-iz-de}" height="${Y(rango[0])-Y(rango[1])}" fill="#ffffff0c"/>` : ""}
      ${rejilla}<rect x="${X(0)}" y="${ar}" width="${Math.max(2, X(3)-X(0))}" height="${H-ar-ab}" fill="#bdbdbd22"/>
      <path d="${d}" fill="none" stroke="#d4d4d4" stroke-width="2"/>
      ${validos.map(p => `<circle cx="${X(p.dia)}" cy="${Y(p.valor)}" r="4" fill="${p.fase === 'Antes del vuelo' ? '#ffffff' : '#91c8ff'}"><title>${escapar(p.momento)}: ${numero(p.valor)} ${escapar(unidad)}</title></circle>`).join("")}
      ${etiquetas}</svg>
    <p>L−: días antes del lanzamiento. R+: días después del regreso. Franja vertical: vuelo de 3 días. Los segmentos solo unen muestras; no son mediciones continuas.</p></figure>`;
}

export function crearExploradorNasa({ datos }) {
  const dialogo = document.querySelector("#nasaExplorador");
  const contenido = document.querySelector("#nasaContenido");
  if (!dialogo || !contenido) return;
  let tripulante = Object.keys(datos?.tripulantes ?? {}).sort()[0];
  let analito = "glucosa", antes = "L-3", despues = "R+1";
  const ids = Object.keys(datos?.tripulantes ?? {}).sort();
  const disponible = ids.length && Array.isArray(datos?.momentos) && datos.momentos.length;
  const botones = document.querySelectorAll("[data-nasa-open]");
  for (const boton of botones) boton.disabled = false;

  function pintar() {
    if (!disponible) {
      contenido.innerHTML = '<p class="nasa-error">No se pudo cargar OSD-575 desde el servidor local. Cierra esta ventana y recarga la página para reintentar. El panel y ORI siguen disponibles.</p>';
      return;
    }
    const opciones = Object.keys(ANALITOS).filter(a => datos.tripulantes[tripulante]?.[a]);
    if (!opciones.includes(analito)) analito = opciones[0];
    if (!analito) { contenido.innerHTML = '<p class="nasa-error">Este tripulante no contiene los analitos esperados.</p>'; return; }
    const info = ANALITOS[analito], serie = datos.tripulantes[tripulante][analito];
    const puntos = puntosSerie(datos, tripulante, analito), cambio = comparar(serie, antes, despues);
    const signo = cambio && cambio.diferencia > 0 ? "+" : "";
    const opcionesMomento = fase => puntos.filter(p => p.momento.startsWith(fase)).map(p => opcion(p.momento, `${p.momento} · ${numero(p.valor)}`, fase === 'L-' ? antes : despues)).join("");
    contenido.innerHTML = `<section class="nasa-intro"><div class="nasa-etiquetas"><span>Datos reales publicados</span><span>4 tripulantes · septiembre 2021</span><span>Misión de 3 días</span></div>
      <p>Análisis de suero de Inspiration4, publicados en NASA OSDR. Esta vista explora evidencia histórica y no cambia los indicadores del astronauta de la pantalla principal.</p></section>
      <div class="nasa-controles"><label>Tripulante del estudio<select id="nasaTripulante">${ids.map(id => opcion(id, id, tripulante)).join("")}</select></label>
      <label>Analito del panel metabólico<select id="nasaAnalito">${opciones.map(a => opcion(a, ANALITOS[a].nombre, analito)).join("")}</select></label></div>
      <p class="nasa-descripcion">${escapar(info.descripcion)}</p>
      <div class="nasa-controles"><label>Muestra antes del lanzamiento<select id="nasaAntes">${opcionesMomento('L-')}</select></label>
      <label>Muestra después del regreso<select id="nasaDespues">${opcionesMomento('R+')}</select></label></div>
      <div id="nasaResumen" aria-live="polite"><p class="sr-only">${escapar(tripulante)}: ${escapar(info.nombre)}, comparación ${escapar(antes)} con ${escapar(despues)}.</p>
      <dl class="nasa-estadisticas"><div><dt>${escapar(antes)} · Antes</dt><dd>${numero(serie.valores?.[antes])} <small>${escapar(serie.unidad)}</small></dd></div>
      <div><dt>${escapar(despues)} · Después</dt><dd>${numero(serie.valores?.[despues])} <small>${escapar(serie.unidad)}</small></dd></div>
      <div><dt>Diferencia entre muestras</dt><dd>${cambio ? signo + numero(cambio.diferencia) : "No comparable"} <small>${cambio ? escapar(serie.unidad) : "falta una medición"}</small></dd></div></dl></div>
      <p class="nasa-limites">Una diferencia no demuestra un efecto causado por el vuelo. Son cuatro personas, sin muestras durante el vuelo en este panel. El rango del laboratorio no es el «normal personal» ni valida reglas para otros astronautas. No se infiere una causa para valores inusuales.</p>
      ${grafica(puntos, serie.unidad, serie.rango)}
      <div class="nasa-tabla"><table><caption>${escapar(info.nombre)} · ${escapar(tripulante)} · valores del archivo</caption><thead><tr><th scope="col">Muestra</th><th scope="col">Etapa</th><th scope="col">Valor (${escapar(serie.unidad)})</th></tr></thead>
      <tbody>${puntos.map(p => `<tr><th scope="row">${escapar(p.momento)}</th><td>${p.fase}</td><td>${numero(p.valor)}</td></tr>`).join("")}</tbody></table></div>
      <section class="nasa-procedencia" aria-label="Procedencia de los datos"><p><strong>Fuente:</strong> NASA OSDR OSD-575 · Comprehensive Metabolic Panel. Identificadores del estudio C001–C004; no se asignan nombres a las personas.</p>
      <p>Archivo de origen: <span translate="no">${ARCHIVO}</span>. El CSV está incluido en el repositorio y convertido por <span translate="no">scripts/convertir_osd575.py</span>. Una celda ausente se muestra como «Sin dato», nunca como cero.</p>
      <p>Referencia del laboratorio para esta serie: ${Array.isArray(serie.rango) && serie.rango.length === 2 && serie.rango.every(esNumero) ? serie.rango.map(numero).join(' – ') + ' ' + escapar(serie.unidad) : 'No disponible'}.</p>
      <div class="botones"><a class="btn" href="${FUENTE}" target="_blank" rel="noopener noreferrer">Abrir estudio NASA ↗</a><button type="button" class="btn" id="nasaDescargar">Exportar esta serie CSV</button></div>
      <p>La exploración y exportación funcionan sin internet con el servidor local activo. Abrir el estudio externo requiere conexión.</p></section>`;
  }

  // Delegación: el acceso dentro de la ficha se vuelve a crear al elegir un órgano.
  document.addEventListener("click", ev => {
    if (!ev.target.closest("[data-nasa-open]")) return;
    pintar();
    if (!dialogo.open) dialogo.showModal();
  });
  contenido.addEventListener("change", ev => {
    const claves = { nasaTripulante: "tripulante", nasaAnalito: "analito", nasaAntes: "antes", nasaDespues: "despues" };
    const id = ev.target.id, clave = claves[id];
    if (!clave) return;
    if (clave === "tripulante") tripulante = ev.target.value;
    if (clave === "analito") analito = ev.target.value;
    if (clave === "antes") antes = ev.target.value;
    if (clave === "despues") despues = ev.target.value;
    pintar();
    document.getElementById(id)?.focus({ preventScroll: true });
  });
  contenido.addEventListener("click", ev => {
    if (!ev.target.closest("#nasaDescargar")) return;
    const url = URL.createObjectURL(new Blob(["\uFEFF", csvSerie(datos, tripulante, analito)], { type: "text/csv;charset=utf-8" }));
    const enlace = document.createElement("a");
    enlace.href = url; enlace.download = `OSD-575_${tripulante}_${analito}.csv`;
    enlace.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}
