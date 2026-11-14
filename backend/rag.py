"""Asistente de salud con RAG local.

Flujo de una pregunta:
  1. Buscar los fragmentos de guías más parecidos a la pregunta
     (vectores con Ollama; si no hay, búsqueda por palabras).
  2. Juntar esos fragmentos con el estado actual del astronauta
     (lo calcula el motor de reglas de P4).
  3. Pedirle al modelo local que redacte la respuesta citando la guía.

Reglas de seguridad:
  - Las ALERTAS no las decide la IA: si el estado trae un indicador en rojo,
    el aviso a la tripulación se agrega siempre, con texto fijo.
  - Si no hay guías relevantes, se responde "no tengo información" en vez
    de inventar.
  - Si Ollama no está disponible, se devuelven los fragmentos encontrados
    (modo respaldo): el astronauta igual recibe la guía.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import json
import math
import re
import unicodedata

import ollama_cliente
from guias import RAIZ, cargar_fragmentos

INDICE = RAIZ / "data" / "indice_guias.json"
K = 3                      # fragmentos que se pasan al modelo
UMBRAL_VECTOR = 0.45       # similitud mínima (solo búsqueda por vectores pura)
UMBRAL_VECTOR_SOLO = 0.70  # sin coincidencia de palabras, el vector debe ser así de alto
UMBRAL_PALABRAS = 0.08

AVISO_ROJO = ("⚠️ Tienes al menos un indicador en ROJO. Avisa ahora a la tripulación "
              "y sigue el protocolo de a bordo.")
SIN_INFO = ("No tengo información sobre eso en mi biblioteca de guías. Avisa al oficial "
            "médico de la tripulación y guarda la pregunta para los médicos en Tierra "
            "cuando vuelva la señal.")

SISTEMA = """Eres el asistente de salud a bordo de una misión espacial larga. Hablas con un
astronauta que NO es médico, a veces sin conexión con la Tierra.

Reglas obligatorias:
- Responde SOLO con la información de las GUÍAS que se te entregan y con los DATOS del astronauta.
- No diagnostiques enfermedades ni indiques medicamentos o dosis.
- Si las guías no cubren la pregunta, dilo claramente.
- Usa frases cortas y simples, en español.
- Estructura: 1) qué muestran sus datos, 2) qué hacer ahora (pasos), 3) cuándo avisar a la tripulación.
- Termina con "Fuente:" y el nombre de la guía o guías usadas.
- Usa EXACTAMENTE el color que trae cada dato (VERDE, AMARILLO, ROJO). Nunca cambies un color:
  si un dato es VERDE, di que está en rango normal.
- No inventes ni recalcules números: copia los valores y cantidades tal como aparecen en los DATOS.
- Menciona solo los datos relacionados con la pregunta.
- Si la pregunta describe una señal de alerta grave de la guía (por ejemplo, dolor muy fuerte,
  cambios en la visión, dolor de pecho, falta de aire, desmayo), el PRIMER paso es avisar de
  inmediato a la tripulación.
- Háblale de "tú"."""

_cache: dict = {}


# ---------- Búsqueda ----------

def _normalizar(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    palabras = re.findall(r"[a-z0-9]+", texto)
    vacias = {"de", "la", "el", "en", "y", "a", "que", "los", "las", "un", "una", "por", "con",
              "para", "es", "me", "mi", "se", "lo", "del", "al", "o", "si", "no", "como", "mas"}
    salida = [p for p in palabras if p not in vacias and len(p) > 2]
    # Sinónimos simples para el modo sin modelo (la búsqueda por vectores no los necesita).
    return salida + [SINONIMOS[p] for p in salida if p in SINONIMOS]


SINONIMOS = {
    "dormir": "sueno", "duermo": "sueno", "dormi": "sueno", "dormido": "sueno",
    "insomnio": "sueno", "cansado": "fatiga", "cansancio": "fatiga",
    "corazon": "pulso", "latidos": "pulso", "palpitaciones": "pulso",
    "tension": "presion", "mareo": "presion", "cabeza": "cabeza", "migrana": "cabeza",
}


def _coseno(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0


def _fragmentos() -> list[dict]:
    """Usa el índice con vectores si existe; si no, las guías sin vectores."""
    if "frags" not in _cache:
        if INDICE.exists():
            _cache["frags"] = json.loads(INDICE.read_text(encoding="utf-8"))["fragmentos"]
        else:
            _cache["frags"] = cargar_fragmentos()
    return _cache["frags"]


def recargar() -> None:
    _cache.clear()


def buscar_por_vectores(pregunta: str, frags: list[dict]) -> list[tuple[float, dict]]:
    v = ollama_cliente.embeber([f"search_query: {pregunta}"])[0]
    puntajes = [(_coseno(v, f["vector"]), f) for f in frags]
    return [p for p in sorted(puntajes, key=lambda x: -x[0])[:K] if p[0] >= UMBRAL_VECTOR]


def buscar_por_palabras(pregunta: str, frags: list[dict]) -> list[tuple[float, dict]]:
    q = set(_normalizar(pregunta))
    if not q:
        return []
    docs = [set(_normalizar(f"{f['guia']} {f['seccion']} {f['texto']}")) for f in frags]
    n = len(docs)
    idf = {t: math.log((n + 1) / (1 + sum(t in d for d in docs))) + 1 for t in q}
    total = sum(idf.values())
    puntajes = [(sum(idf[t] for t in q if t in d) / total, f) for d, f in zip(docs, frags)]
    return [p for p in sorted(puntajes, key=lambda x: -x[0])[:K] if p[0] >= UMBRAL_PALABRAS]


def buscar(pregunta: str) -> tuple[list[tuple[float, dict]], str]:
    """Búsqueda híbrida.

    nomic-embed-text da puntajes parecidos en español a preguntas relacionadas y no
    relacionadas (~0.60 vs ~0.66), así que el vector solo ORDENA. Para decidir si hay
    algo relevante, se exige además coincidencia de palabras, o un vector muy alto.
    """
    frags = _fragmentos()
    por_palabras = buscar_por_palabras(pregunta, frags)
    if frags and "vector" in frags[0]:
        try:
            v = ollama_cliente.embeber([f"search_query: {pregunta}"])[0]
        except ollama_cliente.OllamaNoDisponible:
            return por_palabras, "palabras"
        kw = {id(f): s for s, f in buscar_por_palabras_todos(pregunta, frags)}
        combinados = sorted(
            ((_coseno(v, f["vector"]) + 0.3 * kw.get(id(f), 0.0), f) for f in frags),
            key=lambda x: -x[0],
        )[:K]
        mejor_vector = max(_coseno(v, f["vector"]) for f in frags)
        if por_palabras or mejor_vector >= UMBRAL_VECTOR_SOLO:
            return combinados, "híbrida"
        return [], "híbrida"
    return por_palabras, "palabras"


def buscar_por_palabras_todos(pregunta: str, frags: list[dict]) -> list[tuple[float, dict]]:
    """Puntaje por palabras de todos los fragmentos (sin cortar), para combinar."""
    q = set(_normalizar(pregunta))
    if not q:
        return []
    docs = [set(_normalizar(f"{f['guia']} {f['seccion']} {f['texto']}")) for f in frags]
    n = len(docs)
    idf = {t: math.log((n + 1) / (1 + sum(t in d for d in docs))) + 1 for t in q}
    total = sum(idf.values())
    return [(sum(idf[t] for t in q if t in d) / total, f) for d, f in zip(docs, frags)]


# ---------- Estado del astronauta ----------

def resumir_estado(estado: dict | None) -> tuple[str, bool]:
    """Texto con los datos actuales y si hay algún rojo."""
    if not estado:
        return "Sin datos recientes del astronauta.", False
    lineas, hay_rojo = [], False
    for ind in estado.get("indicadores", []):
        color = ind.get("color", "sin dato")
        hay_rojo |= color == "rojo"
        tend = f", tendencia {ind['tendencia']}" if ind.get("tendencia") else ""
        edad = f", medido hace {ind['antiguedad_min']} min" if "antiguedad_min" in ind else ""
        lineas.append(f"- {ind.get('indicador')}: {ind.get('valor')} {ind.get('unidad', '')} "
                      f"[{color.upper()}{tend}{edad}]")
    for nota in estado.get("notas", []):
        lineas.append(f"- {nota}")
    return "\n".join(lineas) or "Sin datos recientes del astronauta.", hay_rojo


# ---------- Respuesta ----------

def _fuentes(encontrados: list[tuple[float, dict]]) -> list[dict]:
    vistas, salida = set(), []
    for puntaje, f in encontrados:
        clave = (f["guia"], f["seccion"])
        if clave not in vistas:
            vistas.add(clave)
            salida.append({"guia": f["guia"], "seccion": f["seccion"], "fuente": f["fuente"],
                           "url": f["url"], "version": f["version"],
                           "relevancia": round(puntaje, 2)})
    return salida


def responder(pregunta: str, estado: dict | None = None) -> dict:
    encontrados, metodo = buscar(pregunta)
    texto_estado, hay_rojo = resumir_estado(estado)
    base = {"fuentes": _fuentes(encontrados), "datos_usados": texto_estado,
            "busqueda": metodo, "alerta_roja": hay_rojo}

    if not encontrados:
        respuesta = SIN_INFO
        if hay_rojo:
            respuesta = AVISO_ROJO + "\n\n" + respuesta
        return {**base, "respuesta": respuesta, "modo": "sin_informacion"}

    guias_txt = "\n\n".join(
        f"[GUÍA: {f['guia']} – {f['seccion']}]\n{f['texto']}" for _, f in encontrados
    )
    mensajes = [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": f"DATOS DEL ASTRONAUTA:\n{texto_estado}\n\n"
                                    f"GUÍAS:\n{guias_txt}\n\nPREGUNTA: {pregunta}"},
    ]
    try:
        respuesta, modo = ollama_cliente.chatear(mensajes), "ia_local"
    except ollama_cliente.OllamaNoDisponible:
        # Respaldo: sin modelo, se entregan los fragmentos tal cual.
        partes = [f"**{f['guia']} – {f['seccion']}**\n{f['texto']}" for _, f in encontrados]
        respuesta = ("(Asistente sin modelo de IA en este momento. Esto dicen las guías:)\n\n"
                     + "\n\n".join(partes))
        modo = "respaldo_sin_ia"

    if hay_rojo:
        respuesta = AVISO_ROJO + "\n\n" + respuesta
    return {**base, "respuesta": respuesta, "modo": modo}
