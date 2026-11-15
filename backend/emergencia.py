"""Protocolos de emergencia de ORI: qué está pasando, qué puedes sentir, a quién llamar y qué hacer.

Se usan cuando no hay tiempo para la IA: siempre responden igual, al instante y sin internet.
Cubren los tres casos del desafío ("a medio camino a Marte, tu compañero siente un dolor agudo
en el pecho y se desploma: ¿qué está pasando?, ¿qué deberían hacer?"):
  1. un compañero se desploma o tiene dolor de pecho,
  2. el astronauta siente algo grave (dolor de pecho, falta de aire, desmayo),
  3. uno o más indicadores del astronauta están en alerta (rojo).

El tono es el de ORI: cálido y tranquilo, sin respuestas secas; los pasos explican el porqué.
Contenido ilustrativo: debe validarlo personal médico.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import re

GUIA_COMPANERO = "emergencia_companero.md"

# --- Cómo reconocer cada caso (sobre el texto sin tildes y en minúsculas) ---
COMPANERO = (r"(se desmay|se desplom|perdio el conocimiento|inconscient|no respira|se esta muriendo|se muere|"
             r"convulsion|no responde(?! la tierra)|tuvo un desmayo|solo jadea|"
             r"(companer|tripulante|colega|comandante|piloto)\w* .*(pecho|se cayo|no se mueve|mal))")
SINTOMA_GRAVE = (r"(dolor (fuerte )?(de|en el) pecho|me duele (mucho )?el pecho|opresion en el pecho|presion en el pecho|"
                 r"no puedo respirar|me falta el aire|me cuesta respirar|falta de aire|me ahogo|me estoy ahogando|me voy a desmayar|me estoy desmayando|"
                 r"me desmayo|casi me desmayo|no siento el brazo|me duele el brazo izquierdo)")

# --- Qué significa cada indicador en alerta y qué se puede sentir (alto / bajo) ---
SENSACION = {
    "pulso": ("tu corazón está latiendo mucho más rápido de lo normal. Es posible que notes palpitaciones, "
              "el corazón golpeando en el pecho, mareo o que te falta el aire",
              "tu corazón está latiendo más lento de lo normal. Puedes sentir cansancio, mareo o que te vas a desmayar"),
    "presion_arterial": ("la sangre está empujando con mucha fuerza. A veces da dolor de cabeza, presión en la nuca "
                         "o visión borrosa, y a veces no se siente nada: por eso es tan útil medirla",
                         "la presión está baja. Puedes sentir mareo al moverte, debilidad o que la vista se oscurece"),
    "oxigeno": ("", "a tu sangre le está llegando menos oxígeno del que necesita. Puedes sentir falta de aire, "
                    "cansancio, dolor de cabeza o que te cuesta pensar con claridad"),
    "temperatura": ("tienes fiebre: tu cuerpo puede estar luchando contra algo. Es normal sentir escalofríos, "
                    "cansancio o dolor en el cuerpo",
                    "tu temperatura está baja. Puedes sentir frío intenso, temblores o torpeza"),
    "glucosa": ("tienes el azúcar en sangre alto. Puede dar mucha sed, cansancio o ganas de orinar seguido",
                "tienes el azúcar en sangre bajo. Puedes notar temblor, sudor, hambre repentina o confusión"),
    "sueno": ("", "llevas muy pocas horas de sueño. Es normal sentir cansancio, menos concentración y cometer más errores"),
    "animo": ("", "tu ánimo está muy bajo. Puedes sentir tristeza, desgana o ganas de aislarte, y no es debilidad: "
                  "la distancia y el encierro le pesan a cualquiera"),
    "estres": ("tu nivel de estrés está muy alto. Puede notarse como tensión, corazón acelerado o dificultad para pensar", ""),
}

# Lo primero que conviene hacer por cada indicador, con su porqué.
PRIMER_PASO = {
    "pulso": "Quédate quieto, sentado o sujeto: así tu corazón no tiene que trabajar más.",
    "presion_arterial": "Quédate en reposo y evita hacer fuerza: eso ayuda a que la presión no suba más.",
    "oxigeno": "Pide a la tripulación que revise el aire de la nave (CO₂ y oxígeno): si el problema es el aire, afecta a todos.",
    "temperatura": "Hidrátate y descansa: con fiebre el cuerpo pierde más agua de lo habitual.",
    "animo": "Busca ahora a alguien de confianza de la tripulación y cuéntale cómo estás: no tienes que cargar esto solo.",
    "estres": "Para un momento lo que estás haciendo; si puedes, deja la tarea a un compañero unos minutos.",
    "radiacion": "Ve al área protegida de la nave y quédate allí hasta que pase el evento.",
}

RESPIRAR = "Respira despacio: toma aire contando hasta 4 y suéltalo contando hasta 6. Calma el cuerpo y te ayuda a pensar."


def _plano(t: str) -> str:
    import rag
    return rag._texto_plano(t)


def es_companero(pregunta: str) -> bool:
    return bool(re.search(COMPANERO, _plano(pregunta)))


def es_sintoma_grave(pregunta: str) -> bool:
    return bool(re.search(SINTOMA_GRAVE, _plano(pregunta)))


def _num(valor) -> float | None:
    try:
        return float(str(valor).split("/")[0].replace(",", "."))
    except ValueError:
        return None


def _es_alto(indicador: dict, regla: dict) -> bool:
    verde = regla.get("verde") or regla.get("componentes", {}).get("sistolica", {}).get("verde")
    v = _num(indicador.get("valor"))
    return bool(verde and v is not None and v > verde[1])


def _rojos(estado: dict | None) -> list[dict]:
    return [i for i in (estado or {}).get("indicadores", []) if i.get("color") == "rojo"]


def _nombre(i: dict, reglas: dict) -> str:
    return reglas.get(i["indicador"], {}).get("nombre", i.get("nombre", i["indicador"]))


def _valor(i: dict) -> str:
    return f"{i['valor']} {i.get('unidad', '')}".strip()


def _fuente(archivo: str, seccion: str, fuente: str = "") -> dict:
    import rag
    titulo = next((f["guia"] for f in rag._fragmentos() if f["archivo"] == archivo), archivo)
    fuente = fuente or next((f.get("fuente", "") for f in rag._fragmentos() if f["archivo"] == archivo), "")
    return {"guia": titulo, "seccion": seccion, "fuente": fuente, "url": "", "version": "", "relevancia": 1.0}


def _bloque_enlace(conectado: bool, companero: bool = False) -> str:
    if conectado:
        return ("📡 **Hay enlace con la Tierra:** cuando la situación esté estable, enviaré el resumen a los médicos "
                "de la Tierra. No esperes su respuesta para empezar a actuar.")
    quien = "Tú y la tripulación son" if companero else "La tripulación y el oficial médico de a bordo son"
    return (f"📡 **Sin enlace con la Tierra:** está bien, no los necesitas para dar los primeros pasos. {quien} "
            "el equipo que puede ayudar ahora. Anota la hora y lo que vaya pasando: guardo el resumen y lo envío "
            "solo en cuanto vuelva la señal.")


def _numerar(pasos: list[str]) -> str:
    vistos, unicos = set(), []
    for p in pasos:
        if p and p not in vistos:
            vistos.add(p)
            unicos.append(p)
    return "\n".join(f"{k}. {p}" for k, p in enumerate(unicos, 1))


def _que_pasa_con_tus_datos(rojos: list[dict], reglas: dict) -> list[str]:
    lineas = []
    for i in rojos[:3]:
        regla = reglas.get(i["indicador"], {})
        alto, bajo = SENSACION.get(i["indicador"], ("", ""))
        texto = alto if _es_alto(i, regla) else bajo
        texto = texto or alto or bajo
        n = i.get("normal")
        normal = f" (tu normal es {round(n) if n is not None and abs(n) >= 20 else n})" if n is not None else ""
        if i["indicador"] == "radiacion":
            texto = "hay un evento de clima espacial. La radiación no se siente en el momento: por eso hay que protegerse antes"
        if not texto:
            texto = "este valor está fuera de su rango seguro"
        lineas.append(f"- **{_nombre(i, reglas)}: {_valor(i)}**{normal}: {texto}.")
    return lineas


def protocolo_alerta(estado: dict | None, conectado: bool) -> tuple[str, list[dict]]:
    """Indicadores propios en rojo: qué pasa, qué puedes sentir, a quién llamar y qué hacer."""
    import rag
    reglas = rag._reglas()
    rojos = _rojos(estado)
    datos = " y ".join(f"{_nombre(i, reglas).lower()} en {_valor(i)}" for i in rojos[:2])
    partes = ["Estoy aquí contigo. Sé que ver una alerta asusta, pero no estás solo y lo vamos a hacer juntos, "
              "paso a paso."]
    partes.append("**Qué está pasando**\n" + "\n".join(_que_pasa_con_tus_datos(rojos, reglas)))
    partes.append(f"**Llama a alguien ahora**\nDi en voz alta o por el intercomunicador: *«Necesito ayuda médica: "
                  f"tengo {datos}»*. Pide que venga el oficial médico de la tripulación y que alguien se quede contigo.")

    pasos, fuentes, vistas = [], [], set()
    for i in rojos[:2]:
        pasos.append(PRIMER_PASO.get(i["indicador"], ""))
    pasos.append(RESPIRAR)
    medir = ""
    for i in rojos[:2]:
        regla = reglas.get(i["indicador"]) or {"guia": "radiacion.md", "fuente": "NASA DONKI (clima espacial)"}
        guia = regla.get("guia")
        if not guia or guia in vistas:
            continue
        vistas.add(guia)
        if not medir:
            medir = rag._seccion(guia, "Cómo medir a bordo").strip()
        fuentes.append(_fuente(guia, "Qué hacer · Cómo medir · Cuándo avisar", regla.get("fuente", "")))
    vuelve = ("**Cuando ya estés acompañado, vuelve a medir** con el botón «+ Registrar medición» "
              "(nunca esperes una medición para pedir ayuda)")
    pasos.append(f"{vuelve}. {'Para que el dato sea fiable: ' + medir[0].lower() + medir[1:] if medir else ''}".strip())
    partes.append("**Qué hacer mientras llega la ayuda**\n" + _numerar(pasos))
    partes.append(_bloque_enlace(conectado))
    partes.append("🚨 Si aparece **dolor de pecho, falta de aire, confusión o desmayo**, avisa de inmediato y sigan "
                  "el protocolo de emergencia de a bordo.")
    partes.append("Aquí sigo contigo. Cuéntame: ¿cómo te sientes ahora mismo? ¿Te duele el pecho o te falta el aire?")
    return "\n\n".join(partes), fuentes


def protocolo_sintoma(estado: dict | None, conectado: bool, pregunta: str = "") -> tuple[str, list[dict]]:
    """El astronauta siente algo grave (dolor de pecho, falta de aire, desmayo), tenga o no datos en rojo."""
    import rag
    reglas = rag._reglas()
    rojos = _rojos(estado)
    partes = ["Has hecho muy bien en decírmelo. Lo que sientes es serio y merece atención ya, pero no estás solo: "
              "vamos a actuar ahora, juntos."]
    que = ("**Qué puede estar pasando**\nUn dolor o presión en el pecho, sobre todo si se va al brazo, al cuello o "
           "a la mandíbula, o si viene con sudor frío, falta de aire o mareo, puede venir del corazón o de los "
           "pulmones. Yo no puedo saber la causa exacta, pero sí sé que lo correcto es pedir ayuda sin esperar.")
    if rojos:
        que += "\n\nAdemás, tus datos muestran:\n" + "\n".join(_que_pasa_con_tus_datos(rojos, reglas))
    partes.append(que)
    datos = (": tengo " + " y ".join(f"{_nombre(i, reglas).lower()} en {_valor(i)}" for i in rojos[:2])) if rojos else ""
    partes.append(f"**Llama a alguien ahora**\nDi en voz alta o por el intercomunicador: *«¡Emergencia médica! "
                  f"{_frase_sintoma(pregunta)}{datos}»*. Pide que venga el oficial médico y que alguien "
                  "se quede a tu lado.")
    pasos = ["Deja lo que estés haciendo y sujétate en un lugar seguro: si te mareas, así no te golpeas.",
             RESPIRAR,
             "Si puedes, mide pulso y oxígeno (o pide que te los midan) y regístralos: le dirán mucho al oficial médico.",
             "El oficial médico decide con el botiquín de a bordo y su protocolo de dolor de pecho; tú no tienes que decidirlo solo.",
             "Si te desmayas, tus compañeros sabrán qué hacer: pueden escribirme *«mi compañero se desmayó»* y los guío."]
    partes.append("**Qué hacer ahora**\n" + _numerar(pasos))
    partes.append(_bloque_enlace(conectado))
    partes.append("Aquí sigo contigo. ¿El dolor es fuerte, se va hacia el brazo o la mandíbula, o te falta el aire?")
    respira = re.search(r"(respirar|aire|ahog)", _plano(pregunta))
    fuentes = [_fuente("oxigeno_aire.md" if respira else "presion_cardiovascular.md", "Señales de alerta · Qué hacer"),
               _fuente(GUIA_COMPANERO, "Señales de alerta")]
    return "\n\n".join(partes), fuentes


def _frase_sintoma(pregunta: str) -> str:
    p = _plano(pregunta)
    if "pecho" in p or "brazo" in p:
        return "Me duele el pecho"
    if re.search(r"(respirar|aire|ahog)", p):
        return "Me falta el aire"
    return "Me estoy mareando, siento que me voy a desmayar"


def protocolo_companero(conectado: bool) -> tuple[str, list[dict]]:
    """Un compañero se desploma, no responde o tiene dolor de pecho."""
    import rag
    pasos = rag._pasos_de_la_guia(GUIA_COMPANERO, 10)
    por_que = rag._seccion(GUIA_COMPANERO, "Por qué importa").strip()
    partes = ["Mantén la calma: puedes ayudarle y no estás solo. Lo que hagan en los próximos minutos es lo que "
              "más importa, y te voy a guiar paso a paso."]
    partes.append("**Pide ayuda ya**\nGrita *«¡Emergencia médica!»* o activa la alarma. Llama al oficial médico y pide "
                  "que alguien traiga **el botiquín de emergencia y el desfibrilador**.")
    partes.append("**Qué hacer**\n" + _numerar([p[0].upper() + p[1:] for p in pasos[1:]]))
    if por_que:
        partes.append("**Qué puede estar pasando**\n" + por_que)
    partes.append(_bloque_enlace(conectado, companero=True))
    partes.append("Lo estás haciendo bien. Cuando sepas si respira, cuéntamelo y te digo qué vigilar después.")
    return "\n\n".join(partes), [_fuente(GUIA_COMPANERO, "Qué hacer · Señales de alerta")]
