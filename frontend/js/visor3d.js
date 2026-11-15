// Visor 3D del cuerpo: modelo realista BodyParts3D (CC BY 4.0) con respaldo simple.
// Uso: const visor = await crearVisor(contenedor, { onSeleccion, onHover });
//      visor.aplicarEstado(estado); visor.seleccionar("corazon");
// Código escrito con asistencia de IA (Claude); revisado por el equipo.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { ORGANOS, COLORES, colorOrgano, indicador } from "./organos.js";

const BRILLO = { verde: 0.06, amarillo: 0.3, rojo: 0.75, "sin dato": 0 };
const FACTOR = { sangre: 0.4, huesos: 0.6 };
const MATERIAL = {
  corazon:  { color: 0xb3172a, roughness: 0.45 },
  pulmones: { color: 0xe89aa5, roughness: 0.7 },
  cerebro:  { color: 0xf0b1bd, roughness: 0.75 },
  ojos:     { color: 0xf4f4f4, roughness: 0.25 },
  huesos:   { color: 0xeee5cf, roughness: 0.6, transparent: true, opacity: 0.42, depthWrite: false },
  sangre:   { color: 0xc0202a, roughness: 0.45 },
};
const ESCALA = 1.5;   // el modelo mide 1,72 m

export function webglDisponible() {
  try { return !!document.createElement("canvas").getContext("webgl2"); } catch { return false; }
}

export async function crearVisor(contenedor, { onSeleccion = () => {}, onHover = () => {}, onFrame = () => {} } = {}) {
  const reducir = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.domElement.setAttribute("aria-hidden", "true");
  contenedor.prepend(renderer.domElement);

  const escena = new THREE.Scene();
  const camara = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  const controles = new OrbitControls(camara, renderer.domElement);
  controles.enableDamping = true;
  controles.minDistance = 1.6;
  controles.maxDistance = 9;
  controles.autoRotate = !reducir && !location.search.includes("quieto");
  controles.autoRotateSpeed = 0.9;
  controles.addEventListener("start", () => (controles.autoRotate = false));

  escena.add(new THREE.AmbientLight(0xffffff, 0.7));
  const luz = new THREE.DirectionalLight(0xffffff, 1.4); luz.position.set(3, 5, 4); escena.add(luz);
  const luz2 = new THREE.DirectionalLight(0xffffff, 0.45); luz2.position.set(-4, 2, -3); escena.add(luz2);

  // Plataforma holográfica.
  const base = new THREE.Mesh(new THREE.CircleGeometry(1.1, 64),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.025 }));
  base.rotation.x = -Math.PI / 2; base.position.y = -0.98; escena.add(base);
  const anillos = [0.85, 1.05, 1.25].map((r) => {
    const a = new THREE.Mesh(new THREE.TorusGeometry(r, 0.003, 4, 128),
      new THREE.MeshBasicMaterial({ color: 0x9a9a9a, transparent: true, opacity: 0.35 }));
    a.rotation.x = Math.PI / 2; a.position.y = -0.97; escena.add(a); return a;
  });
  const escaneo = new THREE.Mesh(new THREE.TorusGeometry(0.6, 0.003, 4, 128),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 }));
  escaneo.rotation.x = Math.PI / 2; escaneo.visible = !reducir; escena.add(escaneo);

  const cuerpo = new THREE.Group(); escena.add(cuerpo);
  const grupos = {}, materiales = {}, clicables = [];
  let corazon = null, estado = null, seleccionado = null, hover = null;

  const grupo = (n) => { const g = new THREE.Group(); g.name = n; cuerpo.add(g); grupos[n] = g; materiales[n] ??= []; return g; };
  const mat = (n, o) => {
    const m = new THREE.MeshStandardMaterial({ metalness: 0.05, ...o });
    m.userData.opBase = m.opacity;
    (materiales[n] ??= []).push(m);   // el material puede crearse antes que su grupo
    return m;
  };

  function agregar(nombre, geo, material, pos) {
    if (!grupos[nombre]) grupo(nombre);
    const m = new THREE.Mesh(geo, material);
    if (pos) m.position.copy(pos);
    m.userData.organo = nombre;
    grupos[nombre].add(m);
    if (nombre !== "piel") clicables.push(m);
    return m;
  }

  function materialPiel() {
    const m = mat("piel", { color: 0xd9dee2, transparent: true, opacity: 0.075, depthWrite: false, roughness: 0.5 });
    m.userData.holograma = true; return m;
  }

  async function cargarModelo() {
    const gltf = await new GLTFLoader().loadAsync("modelos/cuerpo.glb");
    const mallas = [];
    gltf.scene.traverse((o) => { if (o.isMesh && ORGANOS[o.name]) mallas.push(o); });
    if (!mallas.length) throw new Error("modelo sin órganos del contrato");
    for (const o of mallas) {
      o.updateWorldMatrix(true, false);
      const geo = o.geometry.clone().applyMatrix4(o.matrixWorld).scale(ESCALA, ESCALA, ESCALA);
      geo.computeBoundingBox();
      const centro = geo.boundingBox.getCenter(new THREE.Vector3());
      geo.translate(-centro.x, -centro.y, -centro.z);
      geo.computeVertexNormals();
      if (o.name === "piel") {
        agregar("piel", geo, materialPiel(), centro).renderOrder = 10;
        const alambre = mat("piel", { color: 0xbfc5ca, wireframe: true, transparent: true, opacity: 0.03, depthWrite: false });
        alambre.userData.holograma = true;
        agregar("piel", geo, alambre, centro).renderOrder = 11;
      } else {
        const m = agregar(o.name, geo, mat(o.name, MATERIAL[o.name]), centro);
        if (o.name === "corazon") corazon = m;
      }
    }
    cuerpo.position.y = -0.97;
    return "realista";
  }

  // Respaldo mínimo si el .glb no carga.
  function construirSimple() {
    const piel = materialPiel();
    const cap = (a, b, r) => {
      const va = new THREE.Vector3(...a), vb = new THREE.Vector3(...b);
      const g = new THREE.CapsuleGeometry(r, va.distanceTo(vb), 6, 16);
      const m = agregar("piel", g, piel, va.clone().add(vb).multiplyScalar(0.5));
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), vb.clone().sub(va).normalize());
    };
    agregar("piel", new THREE.SphereGeometry(0.15, 24, 16), piel, new THREE.Vector3(0, 1.5, 0));
    cap([0, 1.25, 0], [0, 0.75, 0], 0.2);
    for (const s of [-1, 1]) { cap([0.24 * s, 1.28, 0], [0.34 * s, 0.6, 0], 0.05); cap([0.1 * s, 0.6, 0], [0.12 * s, -0.95, 0], 0.07); }
    agregar("cerebro", new THREE.SphereGeometry(0.1, 24, 16), mat("cerebro", MATERIAL.cerebro), new THREE.Vector3(0, 1.53, 0));
    for (const s of [-1, 1]) agregar("ojos", new THREE.SphereGeometry(0.02, 12, 8), mat("ojos", MATERIAL.ojos), new THREE.Vector3(0.05 * s, 1.5, 0.13));
    for (const s of [-1, 1]) agregar("pulmones", new THREE.SphereGeometry(0.09, 20, 14), mat("pulmones", MATERIAL.pulmones), new THREE.Vector3(0.09 * s, 1.1, 0.02)).scale.set(1, 1.6, 0.9);
    corazon = agregar("corazon", new THREE.SphereGeometry(0.06, 20, 14), mat("corazon", MATERIAL.corazon), new THREE.Vector3(0.03, 1.05, 0.08));
    agregar("huesos", new THREE.CylinderGeometry(0.02, 0.02, 0.9, 8), mat("huesos", MATERIAL.huesos), new THREE.Vector3(0, 0.9, -0.06));
    agregar("sangre", new THREE.CylinderGeometry(0.01, 0.01, 1.6, 6), mat("sangre", MATERIAL.sangre), new THREE.Vector3(0.04, 0.3, 0.05));
    return "simple";
  }

  let tipo;
  try { tipo = await cargarModelo(); }
  catch (e) { console.warn("Modelo realista no disponible, uso el simple:", e); tipo = construirSimple(); }
  camara.position.set(0, 0.55, 4.9);
  controles.target.set(0, 0.32, 0);

  // ---------- Estado y resaltado ----------
  function pintar() {
    if (!estado) return;
    for (const nombre of Object.keys(materiales)) {
      const c = colorOrgano(estado, nombre);
      const color = new THREE.Color(COLORES[c]);
      const activo = nombre === hover || nombre === seleccionado;
      for (const m of materiales[nombre]) {
        if (nombre === "piel") {
          m.color.copy(new THREE.Color(0xd9dee2).lerp(color, 0.18));
          m.opacity = m.userData.opBase * (activo ? 2 : 1);
          continue;
        }
        m.emissive.copy(color);
        m.userData.base = BRILLO[c] * (FACTOR[nombre] ?? 1);
        m.userData.rojo = c === "rojo";
        m.emissiveIntensity = activo ? Math.max(0.9, m.userData.base) : m.userData.base;
        m.transparent = true;
        m.opacity = seleccionado && nombre !== seleccionado ? 0.22 : m.userData.opBase;
      }
    }
  }

  // ---------- Anclas anatómicas (para etiquetas con línea guía) ----------
  // Centro de cada órgano; piel, huesos y sangre usan un punto visible representativo.
  const AJUSTE = { piel: [0.36, 0.0, 0.06], huesos: [0.16, -0.62, 0.02], sangre: [-0.17, -0.28, 0.06] };
  const anclas = {};
  cuerpo.updateMatrixWorld(true);
  for (const [n, g] of Object.entries(grupos)) {
    const caja = new THREE.Box3().setFromObject(g);
    const c = caja.getCenter(new THREE.Vector3());
    if (AJUSTE[n]) c.set(...AJUSTE[n]).add(new THREE.Vector3(0, tipo === "realista" ? 0.65 : 0.75, 0));
    anclas[n] = c;
  }
  const tmp = new THREE.Vector3();
  function proyectar(v) {
    tmp.copy(v).project(camara);
    return { x: (tmp.x * 0.5 + 0.5) * contenedor.clientWidth, y: (-tmp.y * 0.5 + 0.5) * contenedor.clientHeight, delante: tmp.z < 1 };
  }

  // ---------- Interacción con el puntero ----------
  const ray = new THREE.Raycaster(), p = new THREE.Vector2();
  const visibles = (lista) => lista.filter((m) => grupos[m.userData.organo]?.visible);
  function golpe(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    p.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(p, camara);
    const interno = ray.intersectObjects(visibles(clicables), false)[0];
    if (interno) return { organo: interno.object.userData.organo, punto: interno.point };
    const piel = grupos.piel?.visible ? ray.intersectObjects(grupos.piel.children, false)[0] : null;
    return piel ? { organo: "piel", punto: piel.point } : null;
  }
  renderer.domElement.addEventListener("pointermove", (ev) => {
    const g = golpe(ev);
    const h = g?.organo ?? null;
    if (h !== hover) { hover = h; pintar(); }
    renderer.domElement.style.cursor = h ? "pointer" : "grab";
    onHover(h, g ? proyectar(g.punto) : null);
  });
  renderer.domElement.addEventListener("pointerleave", () => { hover = null; pintar(); onHover(null, null); });
  let abajo = null;
  renderer.domElement.addEventListener("pointerdown", (ev) => (abajo = [ev.clientX, ev.clientY]));
  renderer.domElement.addEventListener("pointerup", (ev) => {
    if (!abajo || Math.hypot(ev.clientX - abajo[0], ev.clientY - abajo[1]) > 5) return;   // fue un arrastre
    onSeleccion(golpe(ev)?.organo ?? null);
  });

  // ---------- Cámara que enfoca un órgano ----------
  const VISTA_GENERAL = { pos: new THREE.Vector3(0, 0.55, 4.9), obj: new THREE.Vector3(0, 0.32, 0) };
  let vuelo = null;
  function volar(objetivo, distancia) {
    const dir = camara.position.clone().sub(controles.target).normalize();
    const pos = objetivo.clone().add(dir.multiplyScalar(distancia));
    vuelo = { t0: performance.now(), dur: reducir ? 1 : 800, desdeP: camara.position.clone(), desdeO: controles.target.clone(), haciaP: pos, haciaO: objetivo.clone() };
  }
  const suave = (x) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);

  // ---------- Animación ----------
  function ajustar() {
    const { clientWidth: w, clientHeight: h } = contenedor;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camara.aspect = w / h; camara.updateProjectionMatrix();
  }
  new ResizeObserver(ajustar).observe(contenedor);
  ajustar();

  const reloj = new THREE.Clock();
  const latido = (f) => Math.exp(-(((f - 0.12) / 0.05) ** 2)) + 0.6 * Math.exp(-(((f - 0.34) / 0.05) ** 2));
  renderer.setAnimationLoop(() => {
    const t = reloj.getElapsedTime();
    const p = estado && indicador(estado, 'pulso');
    const lpm = p && (!p.calidad || p.calidad === 'vigente') ? Number(p.valor) : 0;
    if (corazon) {
      const s = lpm > 0 ? 1 + (reducir ? 0.04 : 0.1) * latido((t * lpm / 60) % 1) : 1;
      corazon.scale.set(s, s, s);
    }
    if (!reducir) {
      for (const [n, mats] of Object.entries(materiales)) {
        if (n === "piel" || n === hover || n === seleccionado) continue;
        for (const m of mats) if (m.userData.rojo) m.emissiveIntensity = 0.5 + 0.35 * (0.5 + 0.5 * Math.sin(t * 5));
      }
      const f = (t * 0.35) % 1;
      escaneo.position.y = -0.95 + f * 2.6;
      escaneo.material.opacity = 0.25 * Math.sin(f * Math.PI);
      
    }
    if (vuelo) {
      const k = Math.min(1, (performance.now() - vuelo.t0) / vuelo.dur), e = suave(k);
      camara.position.lerpVectors(vuelo.desdeP, vuelo.haciaP, e);
      controles.target.lerpVectors(vuelo.desdeO, vuelo.haciaO, e);
      if (k === 1) vuelo = null;
    }
    controles.update();
    renderer.render(escena, camara);
    onFrame((organo) => (anclas[organo] && grupos[organo]?.visible !== false ? proyectar(anclas[organo]) : null));
  });

  const CAPAS = { piel: ["piel"], huesos: ["huesos"], sangre: ["sangre"], organos: ["corazon", "pulmones", "cerebro", "ojos"] };
  return {
    tipo,
    aplicarEstado(e) { estado = e; pintar(); },
    seleccionar(n) { seleccionado = n; pintar(); },
    girar(activo) { controles.autoRotate = activo && !reducir; return controles.autoRotate; },
    get girando() { return controles.autoRotate; },
    capa(nombre, visible) { for (const n of CAPAS[nombre] ?? []) if (grupos[n]) grupos[n].visible = visible; },
    // Enfoca un órgano (o vuelve a la vista general con null).
    enfocar(n) {
      controles.autoRotate = false;
      if (!n || !anclas[n]) { vuelo = null; volar(VISTA_GENERAL.obj, VISTA_GENERAL.pos.distanceTo(VISTA_GENERAL.obj)); return; }
      const cerca = { cerebro: 1.3, ojos: 1.2, corazon: 1.5, pulmones: 1.8, sangre: 3.2, huesos: 3.4, piel: 3.6 };
      volar(anclas[n], cerca[n] ?? 2.5);
    },
  };
}
