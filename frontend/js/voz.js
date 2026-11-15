// Voz de ORI, todo sin internet:
//  - alarma: tono generado por el navegador (Web Audio), sin archivos de sonido;
//  - lectura en voz alta: voz natural de ORI generada en el servidor local con Piper (suena igual en
//    cualquier equipo); si no está, las voces del sistema operativo (speechSynthesis);
//  - micrófono: el audio se graba en el navegador y se transcribe con Whisper en el servidor local
//    (no se usa el reconocimiento de voz de Chrome porque envía el audio a internet).
// Código escrito con asistencia de IA (Claude); revisado por el equipo.
import { EN } from "./i18n.js";

const enNavegador = typeof window !== "undefined";
let silencio = false;
try { silencio = enNavegador && localStorage.getItem("voz-silencio") === "1"; } catch { /* sin almacenamiento */ }

export const estaSilenciado = () => silencio;
export function silenciar(si) {
  silencio = si;
  try { localStorage.setItem("voz-silencio", si ? "1" : "0"); } catch { /* sin almacenamiento */ }
  if (si) callar();
}

// ---------- Texto para leer: sin markdown, emojis ni símbolos ----------
export function textoParaVoz(texto) {
  return String(texto ?? "")
    .replace(/\*\*|__|[*_`]/g, "")
    .replace(/[«»"]/g, "")
    .replace(/\p{Extended_Pictographic}|️/gu, "")
    .replace(/^\s*(\d+[.)]|[-•])\s+/gm, "")          // viñetas y números de lista
    .replace(/\s*\n+\s*/g, ". ")
    .replace(/(\.\s*){2,}/g, ". ")
    .replace(/:\s*\./g, ":")
    .replace(/\s{2,}/g, " ")
    .trim();
}

// En una emergencia no se lee todo: la primera frase y el bloque "a quién llamar / pide ayuda".
const LLAMAR = /^\*\*(Llama a alguien ahora|Pide ayuda ya|Call someone now|Get help now)\*\*/;
export function resumenEmergencia(texto) {
  const partes = String(texto ?? "").split(/\n{2,}/);
  const llamar = partes.find((p) => LLAMAR.test(p.trim()));
  return textoParaVoz([partes[0], llamar].filter(Boolean).join("\n"));
}

// ---------- Lectura en voz alta ----------
// Primero la voz del servidor (Piper, sin internet); si no está instalada, la del navegador.
let vozServidor = null;   // null = no se sabe todavía; true / false después de preguntar
export async function comprobarVozServidor() {
  if (vozServidor !== null || !enNavegador) return vozServidor;
  try {
    const r = await fetch("/api/voz/estado", { signal: AbortSignal.timeout(3000) });
    vozServidor = r.ok && !!(await r.json()).habla;
  } catch { vozServidor = false; }
  return vozServidor;
}

export function vozDisponible() {
  return enNavegador && (vozServidor === true || "speechSynthesis" in window);
}

let audio = null, turno = 0;
async function hablarServidor(texto, miTurno) {
  const r = await fetch("/api/voz/hablar", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto }), signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error("sin voz");
  const url = URL.createObjectURL(await r.blob());
  if (miTurno !== turno) { URL.revokeObjectURL(url); return; }   // se pidió otra frase o silencio mientras tanto
  audio = new Audio(url);
  audio.onended = () => URL.revokeObjectURL(url);
  await audio.play();
}

function hablarNavegador(limpio) {
  if (!("speechSynthesis" in window)) return false;
  const u = new SpeechSynthesisUtterance(limpio);
  u.lang = EN ? "en-US" : "es-ES";
  const v = elegirVoz();
  if (v) u.voice = v;
  window.speechSynthesis.speak(u);
  return true;
}

function elegirVoz() {
  const voces = window.speechSynthesis.getVoices();
  const lengua = EN ? "en" : "es";
  return voces.find((v) => v.lang?.toLowerCase().startsWith(lengua) && v.localService)
    ?? voces.find((v) => v.lang?.toLowerCase().startsWith(lengua)) ?? null;
}

export function callar() {
  turno += 1;
  if (audio) { audio.pause(); audio = null; }
  if (enNavegador && "speechSynthesis" in window) window.speechSynthesis.cancel();
}

/** Lee un texto con la voz de ORI. Devuelve false si no hay voz en este equipo o está silenciado. */
export function hablar(texto, { forzar = false } = {}) {
  if (!enNavegador || (silencio && !forzar)) return false;
  const limpio = textoParaVoz(texto).slice(0, 1200);
  if (!limpio) return false;
  callar();
  const miTurno = turno;
  if (vozServidor === false) return hablarNavegador(limpio);
  comprobarVozServidor()
    .then((si) => (si ? hablarServidor(limpio, miTurno) : Promise.reject(new Error("sin voz"))))
    .catch(() => { if (miTurno === turno) hablarNavegador(limpio); });   // respaldo: voces del navegador
  return true;
}

// ---------- Alarma (Web Audio: tres pitidos, sin archivos) ----------
let ctx = null;
export function alarma() {
  if (!enNavegador || silencio) return;
  try {
    ctx ??= new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === "suspended") ctx.resume();
    const t0 = ctx.currentTime + 0.02;
    for (let k = 0; k < 3; k++) {
      const osc = ctx.createOscillator(), vol = ctx.createGain();
      osc.type = "square";
      osc.frequency.value = k === 2 ? 1046 : 880;
      vol.gain.setValueAtTime(0.0001, t0 + k * 0.28);
      vol.gain.exponentialRampToValueAtTime(0.18, t0 + k * 0.28 + 0.02);
      vol.gain.exponentialRampToValueAtTime(0.0001, t0 + k * 0.28 + 0.2);
      osc.connect(vol).connect(ctx.destination);
      osc.start(t0 + k * 0.28);
      osc.stop(t0 + k * 0.28 + 0.22);
    }
  } catch { /* sin audio */ }
}

/** Alerta completa: alarma y, después, la frase hablada. */
export function alertar(texto) {
  if (silencio) return;
  alarma();
  setTimeout(() => hablar(texto), 950);
}

// ---------- Micrófono: grabar y transcribir con Whisper local ----------
export async function micDisponible() {
  if (!enNavegador || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return false;
  try {
    const r = await fetch("/api/voz/estado", { signal: AbortSignal.timeout(3000) });
    return r.ok && (await r.json()).disponible;
  } catch { return false; }
}

/** Empieza a grabar. Devuelve un objeto con detener() -> Promise<Blob>. */
export async function grabar({ maxSegundos = 30 } = {}) {
  const flujo = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  const tipo = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm", "audio/mp4"].find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
  const rec = new MediaRecorder(flujo, tipo ? { mimeType: tipo } : undefined);
  const trozos = [];
  rec.ondataavailable = (e) => { if (e.data.size) trozos.push(e.data); };
  const fin = new Promise((ok) => { rec.onstop = () => { flujo.getTracks().forEach((t) => t.stop()); ok(new Blob(trozos, { type: rec.mimeType })); }; });
  rec.start();
  const tope = setTimeout(() => rec.state === "recording" && rec.stop(), maxSegundos * 1000);
  return { detener: () => { clearTimeout(tope); if (rec.state === "recording") rec.stop(); return fin; }, fin };
}

export async function transcribir(blob) {
  const r = await fetch("/api/voz", { method: "POST", body: blob, headers: { "Content-Type": blob.type || "application/octet-stream" },
    signal: AbortSignal.timeout(60000) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || "error");
  return d.texto ?? "";
}
