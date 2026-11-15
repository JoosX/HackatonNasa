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
UMBRAL_VECTOR_SOLO = 0.68  # sin coincidencia de palabras, el vector debe ser así de alto
PESO_PALABRAS = 0.6        # peso de la coincidencia de palabras al ordenar (corrige "pecho" -> guía de piel)
UMBRAL_PALABRAS = 0.08

AVISO_ROJO = ("⚠️ Antes que nada: tienes al menos un indicador en alerta. Avisa ahora a la "
              "tripulación y sigue el protocolo de a bordo; no tienes que manejarlo solo.")
SIN_INFO = ("No tengo información sobre eso en mi biblioteca de guías, y prefiero no inventarte nada. "
            "Coméntalo con el oficial médico de la tripulación y guardo la pregunta para los médicos "
            "en Tierra cuando vuelva la señal.")

# La IA solo escribe la parte humana (empatía + explicación de sus datos). Los pasos y el "cuándo avisar"
# se copian tal cual de la guía de NASA: así no se pueden inventar y la fuente queda garantizada.
SISTEMA = """Eres ORI, el compañero de salud a bordo de una misión espacial larga. Hablas con un
astronauta que NO es médico. Tono: cálido, cercano y tranquilo, como un compañero de tripulación.
Habla de "tú", en español, con frases cortas y naturales.

Escribe SOLO dos o tres frases (máximo 55 palabras), sin listas ni viñetas:
- Primero, una frase empática sobre lo que pregunta, con tus propias palabras.
- Después, explica en palabras simples qué muestran SUS DATOS relacionados (si hay), usando el estado
  tal cual viene ("normal", "en precaución" o "en alerta") y copiando los números exactos.
  Si los datos dicen cuál es "su normal" o la tendencia (sube, baja), menciónalo: ayuda a entender el cambio.
- Si hay conversación previa, mantén la continuidad (no vuelvas a saludar ni repitas lo mismo).

No des pasos ni recomendaciones, no digas a quién avisar ni cuándo: eso lo agrega la app desde la guía.
No inventes datos, nombres ni conclusiones: por ejemplo, una llamarada solar es un evento en el Sol,
no significa que el astronauta recibió radiación. Sin corchetes ni etiquetas en mayúsculas."""

_cache: dict = {}


# ---------- Búsqueda ----------

def _normalizar(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    palabras = re.findall(r"[a-z0-9]+", texto)
    vacias = {"de", "la", "el", "en", "y", "a", "que", "los", "las", "un", "una", "por", "con",
              "para", "es", "me", "mi", "se", "lo", "del", "al", "o", "si", "no", "como", "mas"}
    salida = [REEMPLAZO.get(p, p) for p in palabras if p not in vacias and len(p) > 2]
    # Sinónimos: conectan cómo habla el astronauta con las palabras de las guías.
    salida += [s for p in salida for s in SINONIMOS.get(p, ())]
    # Raíz de 5 letras: "estresado" ~ "estrés", "respiración" ~ "respirar".
    return [p[:5] for p in salida]


# "sangra" no debe llevar a "glucosa en sangre": no hay guía de sangrados.
REEMPLAZO = {"sangra": "hemorragia", "sangrado": "hemorragia", "sangrar": "hemorragia", "sangrando": "hemorragia"}

SINONIMOS = {
    # sueño y cansancio
    "dormir": ("sueno",), "duermo": ("sueno",), "dormi": ("sueno",), "dormido": ("sueno",), "insomnio": ("sueno",),
    "cansado": ("fatiga", "sueno"), "cansada": ("fatiga", "sueno"), "cansancio": ("fatiga",), "agotado": ("fatiga",), "agotada": ("fatiga",),
    # corazón y presión
    "corazon": ("pulso",), "latidos": ("pulso",), "palpitaciones": ("pulso",), "pecho": ("pecho", "pulso", "presion"),
    "tension": ("presion",), "mareo": ("mareo", "presion"), "mareado": ("mareo", "presion"), "mareada": ("mareo", "presion"),
    "mareos": ("mareo", "presion"), "desmayo": ("desmayo", "presion"),
    # cabeza y visión
    "cabeza": ("cabeza",), "migrana": ("cabeza",), "jaqueca": ("cabeza",), "borroso": ("vision",), "ojos": ("vision",), "vista": ("vision",),
    # respiración y aire
    "respirar": ("aire", "oxigeno"), "respiro": ("aire", "oxigeno"), "respiracion": ("aire", "oxigeno"),
    "ahogo": ("aire", "oxigeno"), "ahogado": ("aire", "oxigeno"), "ahogada": ("aire", "oxigeno"), "asfixia": ("aire", "oxigeno"),
    # ánimo y estrés
    "estresado": ("estres",), "estresada": ("estres",), "ansiedad": ("estres",), "ansioso": ("estres",), "ansiosa": ("estres",),
    "nervioso": ("estres",), "nerviosa": ("estres",), "triste": ("animo",), "deprimido": ("animo",), "deprimida": ("animo",),
    "solo": ("animo", "aislamiento"), "sola": ("animo", "aislamiento"), "aislado": ("aislamiento", "animo"),
    # temperatura, piel, náuseas, comida
    "frio": ("temperatura",), "escalofrios": ("escalofrios", "fiebre"), "calor": ("temperatura", "fiebre"),
    "sarpullido": ("erupcion", "piel"), "picazon": ("pica", "piel"), "ronchas": ("erupcion", "piel"),
    "vomito": ("vomitos", "nauseas"), "vomitar": ("vomitos", "nauseas"),
    "hambre": ("comidas", "glucosa"), "comer": ("comidas", "glucosa"), "azucar": ("glucosa",), "apetito": ("comidas",),
    # huesos y radiación
    "espalda": ("espalda", "huesos"), "hueso": ("huesos",), "golpe": ("golpe", "huesos"), "fractura": ("fractura", "huesos"),
    "solar": ("radiacion", "tormenta"), "radiacion": ("radiacion",), "llamarada": ("radiacion", "solar"),
    "llamaradas": ("radiacion", "solar"), "dosimetro": ("dosimetro", "radiacion"), "espacial": ("radiacion",),
}

# ---------- Intenciones que no necesitan buscar en las guías ----------

def _texto_plano(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in t if unicodedata.category(c) != "Mn")))


INTENCIONES = [
    ("saludo", r"^(hola|holi|buenas|buenos dias|buenas tardes|buenas noches|hey|que tal|saludos)\b"),
    ("gracias", r"^(gracias|muchas gracias|ok gracias|perfecto|genial|vale gracias|listo)\b"),
    ("ayuda", r"(que puedes hacer|en que me ayudas|como funcionas|como funciona|quien eres|que eres|ayuda$|^ayuda)"),
    ("estado", r"(como estoy|mi estado|como estan mis|como va mi salud|resumen|mis signos|mis datos|estoy bien|que tengo mal)"),
    ("colores", r"(que significa|que quiere decir).*(color|amarillo|rojo|verde|semaforo)|^semaforo"),
]

PALABRAS_SINTOMA = r"(duele|dolor|siento|tengo|sangr|tos|mare|fiebre|vomit|picazon|hinch|golpe|herida|quemadura|nausea)"

TEXTO_INTENCION = {
    "saludo": "¡Hola! Soy **ORI**, tu compañero de salud a bordo 👋\n"
              "Estoy aquí para acompañarte, incluso cuando no hay señal con la Tierra. "
              "Puedes preguntarme **¿cómo estoy?**, contarme qué sientes (por ejemplo, *me duele la cabeza*) "
              "o pedirme que te explique un indicador. ¿Cómo te sientes hoy?",
    "gracias": "¡Con gusto! 😊 Cuídate mucho. Si algo cambia o te sientes peor, aquí sigo, "
               "y recuerda que la tripulación siempre está contigo.",
    "ayuda": "¡Claro! Te puedo ayudar en tres cosas, todo sin internet:\n"
             "- **Ver cómo estás**: pregúntame *¿cómo estoy?* y te resumo tus datos.\n"
             "- **Orientarte si te sientes mal**: cuéntame qué sientes y te digo qué hacer y cuándo avisar.\n"
             "- **Explicarte un indicador**: presión, pulso, oxígeno, glucosa, sueño, ánimo, radiación…\n"
             "Solo uso las guías de salud guardadas en la nave y siempre te muestro de dónde saco cada consejo. "
             "No reemplazo al médico, pero te acompaño mientras tanto.",
    "colores": "Uso el mismo código que las alarmas de la nave, para que lo leas de un vistazo:\n"
               "- 🟢 **Normal**: todo en orden.\n"
               "- 🟡 **Precaución**: algo se salió de lo habitual. Repite la medición y sigue el consejo.\n"
               "- 🔴 **Alerta**: avisa a la tripulación y sigue el protocolo de a bordo.\n"
               "Cada órgano del cuerpo toma el color de su indicador más alterado.",
}


def _reglas() -> dict:
    if "reglas" not in _cache:
        datos = json.loads((RAIZ / "data" / "reglas.json").read_text(encoding="utf-8"))
        _cache["reglas"] = {r["indicador"]: r for r in datos["indicadores"]}
    return _cache["reglas"]


def resumen_estado(estado: dict | None) -> tuple[str, list[dict]]:
    """Resumen determinista (sin IA) de los indicadores fuera de rango, con la acción de reglas.json."""
    if not estado or not estado.get("indicadores"):
        return "Todavía no tengo mediciones tuyas. Cuando registres tus signos vitales, te cuento cómo vas. 🙂", []
    reglas = _reglas()
    orden = {"rojo": 0, "amarillo": 1}
    fuera = sorted((i for i in estado["indicadores"] if i.get("color") in orden), key=lambda i: orden[i["color"]])
    if not fuera:
        return "¡Buenas noticias! 🟢 Todos tus indicadores están **normales**. Sigue así con tu rutina de sueño, ejercicio y mediciones.", []
    lineas, fuentes, vistas = [], [], set()
    for i in fuera:
        r = reglas.get(i["indicador"]) or {"nombre": i.get("nombre", i["indicador"]),
                                            "accion": {i["color"]: i.get("accion", "")}, "guia": "radiacion.md",
                                            "fuente": "NASA DONKI (clima espacial)"}
        nombre = r.get("nombre", i["indicador"])
        etiqueta = "ALERTA" if i["color"] == "rojo" else "PRECAUCIÓN"
        accion = r.get("accion", {}).get(i["color"], "")
        icono = "🔴" if i["color"] == "rojo" else "🟡"
        lineas.append(f"- {icono} **{nombre}: {i.get('valor')} {i.get('unidad', '')}** ({etiqueta.lower()}). {accion}")
        if r.get("guia") and r["guia"] not in vistas:
            vistas.add(r["guia"])
            fuentes.append({"guia": r.get("fuente", r["guia"]), "seccion": "Cuándo avisar", "fuente": r.get("fuente", ""),
                            "url": "", "version": "", "relevancia": 1.0})
    verdes = sum(1 for i in estado["indicadores"] if i.get("color") == "verde")
    hay_alerta = any(i["color"] == "rojo" for i in fuera)
    intro = ("Te cuento cómo vas. Hay algo que necesita atención **ahora**:" if hay_alerta else
             f"Te cuento cómo vas: la mayoría va bien ({verdes} en normal), pero "
             f"{'hay algo' if len(fuera) == 1 else f'hay {len(fuera)} cosas'} que conviene vigilar:")
    cierre = ("Avisa a la tripulación ya; no tienes que manejarlo solo." if hay_alerta else
              "Nada de esto es para alarmarse, pero vale la pena cuidarlo hoy. ¿Quieres que veamos alguno en detalle?")
    texto = intro + "\n" + "\n".join(lineas) + "\n\n" + cierre
    return texto, fuentes


CIERRES = ["Aquí sigo si me necesitas.", "Vamos paso a paso; cualquier cosa me cuentas.",
           "Cuídate mucho, estoy aquí para lo que necesites.", "Tranquilo, lo vamos viendo juntos."]


def _seccion(archivo: str, nombre: str) -> str:
    return next((f["texto"] for f in _fragmentos() if f["archivo"] == archivo and f["seccion"] == nombre), "")


def _pasos_de_la_guia(archivo: str, maximo: int = 4) -> list[str]:
    texto = _seccion(archivo, "Qué hacer")
    return [l.lstrip("-•* ").strip() for l in texto.splitlines() if l.strip().startswith(("-", "•", "*"))][:maximo]


def _cuando_avisar(archivo: str) -> list[str]:
    texto = _seccion(archivo, "Cuándo avisar")
    partes = re.split(r"(?=(?:Amarillo|Rojo):)", texto)
    salida = []
    for p in partes:
        p = p.strip()
        if p.startswith("Amarillo:"):
            salida.append("🟡 **Precaución**: " + p[len("Amarillo:"):].strip())
        elif p.startswith("Rojo:"):
            salida.append("🔴 **Alerta, avisa de inmediato**: " + p[len("Rojo:"):].strip())
    return salida


def explicar(texto_ia: str, archivo: str, pregunta: str) -> str:
    """Respuesta a un '¿por qué?': la explicación de la guía, sin repetir los pasos ya dados."""
    partes = [texto_ia.strip()]
    for seccion, titulo in (("Qué pasa en el espacio", "Por qué pasa en el espacio"), ("Por qué importa", "Por qué importa")):
        texto = _seccion(archivo, seccion)
        if texto:
            partes.append(f"**{titulo}:**\n{texto}")
    partes.append("Si quieres, te repito qué hacer ahora o cuándo avisar.")
    return "\n\n".join(p for p in partes if p)


def componer(texto_ia: str, archivo: str, pregunta: str, secundaria: str | None = None) -> str:
    """Respuesta final: la parte humana (IA) + pasos y avisos copiados de la(s) guía(s) de NASA."""
    if secundaria:
        pasos = _pasos_de_la_guia(archivo, 3) + _pasos_de_la_guia(secundaria, 2)
        avisos = _cuando_avisar(archivo) + _cuando_avisar(secundaria)
    else:
        pasos, avisos = _pasos_de_la_guia(archivo), _cuando_avisar(archivo)
    partes = [texto_ia.strip()]
    if pasos:
        partes.append("**Lo que te propongo ahora:**\n" + "\n".join(f"- {p}" for p in pasos))
    if avisos:
        partes.append("**Cuándo avisar a la tripulación:**\n" + "\n".join(f"- {a}" for a in avisos))
    partes.append(CIERRES[sum(map(ord, pregunta)) % len(CIERRES)])
    return "\n\n".join(p for p in partes if p)


def _anclar_pasos(encontrados: list[tuple[float, dict]]) -> list[tuple[float, dict]]:
    """Asegura que el modelo reciba 'Qué hacer' y 'Cuándo avisar' de la guía principal (de ahí salen los pasos)."""
    if not encontrados:
        return encontrados
    principal = encontrados[0][1]["archivo"]
    tiene = {(f["archivo"], f["seccion"]) for _, f in encontrados}
    extra = [(0.0, f) for f in _fragmentos() if f["archivo"] == principal
             and f["seccion"] in ("Qué hacer", "Cuándo avisar") and (f["archivo"], f["seccion"]) not in tiene]
    # Se mantiene la guía principal arriba; se quita un fragmento de otra guía si hace falta espacio.
    mezcla = [e for e in encontrados if e[1]["archivo"] == principal] + extra + [e for e in encontrados if e[1]["archivo"] != principal]
    return mezcla[:K + 1]


def _estado_relevante(estado: dict | None, archivos: set[str]) -> str | None:
    """Solo los indicadores cuya guía apareció en la búsqueda (evita que el modelo hable de otros datos)."""
    if not estado:
        return None
    guia_de = {n: r.get("guia") for n, r in _reglas().items()}
    guia_de["radiacion"] = "radiacion.md"
    filtrado = [i for i in estado.get("indicadores", []) if guia_de.get(i.get("indicador")) in archivos]
    if not filtrado:
        return None
    notas = estado.get("notas", []) if "sueno_fatiga.md" in archivos or "animo_estres.md" in archivos else []
    texto, _ = resumir_estado({"indicadores": filtrado, "notas": notas})
    return texto


def detectar_intencion(pregunta: str) -> str | None:
    t = _texto_plano(pregunta)
    for nombre, patron in INTENCIONES:
        if re.search(patron, t):
            # Un saludo con un síntoma ("hola, me duele la cabeza") va a las guías.
            if nombre in ("saludo", "gracias") and re.search(PALABRAS_SINTOMA, t):
                continue
            return nombre
    return None


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
    """Mejores fragmentos por palabras (misma puntuación que la búsqueda híbrida)."""
    puntajes = sorted(buscar_por_palabras_todos(pregunta, frags), key=lambda x: -x[0])
    return [p for p in puntajes[:K] if p[0] >= UMBRAL_PALABRAS]


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
            ((_coseno(v, f["vector"]) + PESO_PALABRAS * kw.get(id(f), 0.0), f) for f in frags),
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
    titulos = [set(_normalizar(f["guia"])) for f in frags]
    n = len(docs)
    idf = {t: math.log((n + 1) / (1 + sum(t in d for d in docs))) + 1 for t in q}
    total = sum(idf.values())
    return [((sum(idf[t] for t in q if t in d) + sum(idf[t] for t in q if t in ti)) / (2 * total), f)
            for d, ti, f in zip(docs, titulos, frags)]


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
        m = ind.get("antiguedad_min")
        edad = "" if m is None else (f" (última medición: hace {m} min)" if m < 60 else f" (última medición: hace {round(m / 60)} h)" if m < 2880 else f" (última medición: hace {round(m / 1440)} días)")
        palabra = {"verde": "normal", "amarillo": "en precaución", "rojo": "en alerta"}.get(color, "sin dato")
        nombre = _reglas().get(ind.get("indicador"), {}).get("nombre", ind.get("nombre", ind.get("indicador")))
        if ind.get("motivo"):
            edad = f" ({ind['motivo'].rstrip('.')})"
        extra = ""
        if ind.get("normal") is not None and ind.get("desviacion_pct") is not None and abs(ind["desviacion_pct"]) >= 10:
            extra += f", su normal es {ind['normal']:g} ({ind['desviacion_pct']:+d} %)"
        if ind.get("sospechoso"):
            extra += ", valor sospechoso: hay que repetir la medición"
        if ind.get("vencido"):
            extra += ", medición vieja: hay que medir de nuevo"
        lineas.append(f"- {nombre}: {ind.get('valor')} {ind.get('unidad', '')}, {palabra}{tend}{extra}{edad}")
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


SEGUIMIENTO = r"^(y |y$|por que|porque|que mas|algo mas|explica|explicame|entonces|eso|y eso|como asi|en serio|de verdad|cuanto|cuando|ok y|vale y|pero)"


def _es_seguimiento(pregunta: str) -> bool:
    t = _texto_plano(pregunta)
    return len(t.split()) <= 6 and bool(re.search(SEGUIMIENTO, t))


def responder(pregunta: str, estado: dict | None = None, turnos: list[dict] | None = None) -> dict:
    turnos = turnos or []
    anterior = next((x["texto"] for x in reversed(turnos) if x["rol"] == "astronauta"), None)
    # Si es una pregunta de seguimiento, se busca con el tema de la pregunta anterior.
    consulta = f"{anterior} {pregunta}" if anterior and _es_seguimiento(pregunta) else pregunta
    texto_estado, hay_rojo = resumir_estado(estado)
    avisar = (lambda r: AVISO_ROJO + "\n\n" + r) if hay_rojo else (lambda r: r)

    # 1) Intenciones que no necesitan IA ni guías (rápidas y siempre iguales).
    intencion = detectar_intencion(pregunta)
    if intencion == "estado":
        texto, fuentes = resumen_estado(estado)
        return {"fuentes": fuentes, "datos_usados": texto_estado, "busqueda": "reglas", "alerta_roja": hay_rojo,
                "respuesta": avisar(texto), "modo": "resumen"}
    if intencion in TEXTO_INTENCION:
        return {"fuentes": [], "datos_usados": texto_estado, "busqueda": "intencion", "alerta_roja": hay_rojo,
                "respuesta": avisar(TEXTO_INTENCION[intencion]), "modo": "conversacion"}

    # 2) Búsqueda en las guías + IA local.
    encontrados, metodo = buscar(consulta)
    base = {"fuentes": _fuentes(encontrados), "datos_usados": texto_estado,
            "busqueda": metodo, "alerta_roja": hay_rojo}

    if not encontrados:
        respuesta = SIN_INFO
        # Ante un síntoma sin guía, igual se dice qué hacer mientras tanto (sin inventar tratamientos).
        if re.search(PALABRAS_SINTOMA, _texto_plano(pregunta)):
            respuesta += ("\n\nMientras tanto, te propongo esto:\n- Mide tus signos vitales y regístralos.\n"
                          "- Si empeora, o hay dolor fuerte, falta de aire, sangrado que no para o desmayo, "
                          "avisa de inmediato a la tripulación.\n- Anota cuándo empezó, así el reporte a la Tierra sale completo.\n\n"
                          "Cuídate, aquí sigo si me necesitas.")
        return {**base, "respuesta": avisar(respuesta), "modo": "sin_informacion"}

    encontrados = _anclar_pasos(encontrados)
    texto_estado = _estado_relevante(estado, {f["archivo"] for _, f in encontrados}) or texto_estado
    guias_txt = "\n\n".join(
        f"[GUÍA: {f['guia']} – {f['seccion']}]\n{f['texto']}" for _, f in encontrados
    )
    previos = []
    for x in turnos[-4:]:   # últimos turnos, para que la respuesta tenga continuidad
        previos.append({"role": "user" if x["rol"] == "astronauta" else "assistant", "content": x["texto"][:400]})
    mensajes = [
        {"role": "system", "content": SISTEMA},
        *previos,
        {"role": "user", "content": f"DATOS DEL ASTRONAUTA (relacionados con la pregunta):\n{texto_estado}\n\n"
                                    f"TEMA DE LA GUÍA: {encontrados[0][1]['guia']}\n\nPREGUNTA: {pregunta}"},
    ]
    principal = encontrados[0][1]["archivo"]
    try:
        humano, modo = ollama_cliente.chatear(mensajes), "ia_local"
    except ollama_cliente.OllamaNoDisponible:
        # Respaldo sin modelo: frase fija + lo que dice la guía (pasos y avisos), igual de útil.
        humano = (f"Te entiendo. Mi parte de IA no está disponible ahora, pero esto es lo que recomienda "
                  f"la guía «{encontrados[0][1]['guia']}».")
        modo = "respaldo_sin_ia"
    # ¿La pregunta mezcla dos temas? (p. ej., dolor de cabeza + poco sueño): segunda guía con buena coincidencia.
    q = set(_normalizar(pregunta))
    def toca(arch: str) -> bool:
        tit = set(_normalizar(next(f["guia"] for _, f in encontrados if f["archivo"] == arch)))
        cuerpo = set(_normalizar(" ".join(f["texto"] for f in _fragmentos() if f["archivo"] == arch)))
        return bool(q & tit) or len(q & cuerpo) >= 2
    otras = [f["archivo"] for _, f in encontrados if f["archivo"] != principal]
    secundaria = next((a for a in otras if toca(a)), None)
    pide_explicacion = consulta != pregunta and re.search(r"(por que|porque|explica|como asi)", _texto_plano(pregunta))
    respuesta = explicar(humano, principal, pregunta) if pide_explicacion else componer(humano, principal, pregunta, secundaria)
    if consulta != pregunta:
        base["seguimiento_de"] = anterior

    return {**base, "respuesta": avisar(respuesta), "modo": modo}
