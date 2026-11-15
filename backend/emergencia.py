"""Protocolos de emergencia de ORI: qué está pasando, qué puedes sentir, a quién llamar y qué hacer.

Se usan cuando no hay tiempo para la IA: siempre responden igual, al instante y sin internet.
Cubren los tres casos del desafío ("a medio camino a Marte, tu compañero siente un dolor agudo
en el pecho y se desploma: ¿qué está pasando?, ¿qué deberían hacer?"):
  1. un compañero se desploma o tiene dolor de pecho,
  2. el astronauta siente algo grave (dolor de pecho, falta de aire, desmayo),
  3. uno o más indicadores del astronauta están en alerta (rojo).

El tono es el de ORI: cálido y tranquilo, sin respuestas secas; los pasos explican el porqué.
Responde en español o en inglés según el idioma de la petición; reconoce frases en los dos idiomas.
Contenido ilustrativo: debe validarlo personal médico.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import re

import idioma
from idioma import t as T

GUIA_COMPANERO = "emergencia_companero.md"

# --- Cómo reconocer cada caso (sobre el texto sin tildes y en minúsculas; español e inglés) ---
COMPANERO = (r"(se desmay|se desplom|perdio el conocimiento|inconscient|no respira|se esta muriendo|se muere|"
             r"convulsion|no responde(?! la tierra)|tuvo un desmayo|solo jadea|"
             r"(companer|tripulante|colega|comandante|piloto)\w* .*(pecho|se cayo|no se mueve|mal)|"
             # inglés ("I fainted" es un síntoma propio, no un compañero)
             r"(?<!\bi )(?<!almost )(fainted|passed out|collapsed)|unconscious|unresponsive|not breathing|"
             r"isn t breathing|is dying|seizure|not responding|only gasping|"
             r"(crewmate|crew member|colleague|commander|pilot|partner)\w* .*(chest|fell|not moving|unwell|sick))")
SINTOMA_GRAVE = (r"(dolor (fuerte )?(de|en el) pecho|me duele (mucho )?el pecho|opresion en el pecho|presion en el pecho|"
                 r"no puedo respirar|me falta el aire|me cuesta respirar|falta de aire|me ahogo|me estoy ahogando|me voy a desmayar|me estoy desmayando|"
                 r"me desmayo|casi me desmayo|no siento el brazo|me duele el brazo izquierdo|"
                 # inglés
                 r"chest pain|pain in (my|the) chest|my chest hurts|chest (hurts|pressure|tightness)|tight chest|"
                 r"pressure in (my|the) chest|can t breathe|cannot breathe|short of breath|shortness of breath|"
                 r"hard to breathe|trouble breathing|choking|going to faint|about to faint|feel faint|almost fainted|"
                 r"i fainted|left arm (hurts|pain)|can t feel my arm)")

# --- Qué significa cada indicador en alerta y qué se puede sentir (alto / bajo), en español e inglés ---
SENSACION = {
    "pulso": (("tu corazón está latiendo mucho más rápido de lo normal. Es posible que notes palpitaciones, "
               "el corazón golpeando en el pecho, mareo o que te falta el aire",
               "your heart is beating much faster than normal. You may notice palpitations, "
               "your heart pounding in your chest, dizziness or shortness of breath"),
              ("tu corazón está latiendo más lento de lo normal. Puedes sentir cansancio, mareo o que te vas a desmayar",
               "your heart is beating slower than normal. You may feel tired, dizzy or like you are going to faint")),
    "presion_arterial": (("la sangre está empujando con mucha fuerza. A veces da dolor de cabeza, presión en la nuca "
                          "o visión borrosa, y a veces no se siente nada: por eso es tan útil medirla",
                          "your blood is pushing very hard. Sometimes it causes a headache, pressure at the back of the neck "
                          "or blurry vision, and sometimes you feel nothing: that is why measuring it is so useful"),
                         ("la presión está baja. Puedes sentir mareo al moverte, debilidad o que la vista se oscurece",
                          "your blood pressure is low. You may feel dizzy when you move, weak or like your vision is going dark")),
    "oxigeno": (("", ""),
                ("a tu sangre le está llegando menos oxígeno del que necesita. Puedes sentir falta de aire, "
                 "cansancio, dolor de cabeza o que te cuesta pensar con claridad",
                 "your blood is getting less oxygen than it needs. You may feel short of breath, "
                 "tired, have a headache or find it hard to think clearly")),
    "temperatura": (("tienes fiebre: tu cuerpo puede estar luchando contra algo. Es normal sentir escalofríos, "
                     "cansancio o dolor en el cuerpo",
                     "you have a fever: your body may be fighting something. It is normal to feel chills, "
                     "tiredness or body aches"),
                    ("tu temperatura está baja. Puedes sentir frío intenso, temblores o torpeza",
                     "your temperature is low. You may feel very cold, shivery or clumsy")),
    "glucosa": (("tienes el azúcar en sangre alto. Puede dar mucha sed, cansancio o ganas de orinar seguido",
                 "your blood sugar is high. It can cause strong thirst, tiredness or needing to urinate often"),
                ("tienes el azúcar en sangre bajo. Puedes notar temblor, sudor, hambre repentina o confusión",
                 "your blood sugar is low. You may notice shaking, sweating, sudden hunger or confusion")),
    "sueno": (("", ""),
              ("llevas muy pocas horas de sueño. Es normal sentir cansancio, menos concentración y cometer más errores",
               "you have had very few hours of sleep. It is normal to feel tired, concentrate less and make more mistakes")),
    "animo": (("", ""),
              ("tu ánimo está muy bajo. Puedes sentir tristeza, desgana o ganas de aislarte, y no es debilidad: "
               "la distancia y el encierro le pesan a cualquiera",
               "your mood is very low. You may feel sad, unmotivated or want to withdraw, and it is not weakness: "
               "distance and confinement weigh on anyone")),
    "estres": (("tu nivel de estrés está muy alto. Puede notarse como tensión, corazón acelerado o dificultad para pensar",
                "your stress level is very high. It can feel like tension, a racing heart or trouble thinking"),
               ("", "")),
}

# Lo primero que conviene hacer por cada indicador, con su porqué.
PRIMER_PASO = {
    "pulso": ("Quédate quieto, sentado o sujeto: así tu corazón no tiene que trabajar más.",
              "Stay still, seated or secured: that way your heart does not have to work harder."),
    "presion_arterial": ("Quédate en reposo y evita hacer fuerza: eso ayuda a que la presión no suba más.",
                         "Rest and avoid straining: that helps keep your blood pressure from rising further."),
    "oxigeno": ("Pide a la tripulación que revise el aire de la nave (CO₂ y oxígeno): si el problema es el aire, afecta a todos.",
                "Ask the crew to check the ship's air (CO₂ and oxygen): if the problem is the air, it affects everyone."),
    "temperatura": ("Hidrátate y descansa: con fiebre el cuerpo pierde más agua de lo habitual.",
                    "Hydrate and rest: with a fever the body loses more water than usual."),
    "animo": ("Busca ahora a alguien de confianza de la tripulación y cuéntale cómo estás: no tienes que cargar esto solo.",
              "Find someone you trust on the crew now and tell them how you are: you don't have to carry this alone."),
    "estres": ("Para un momento lo que estás haciendo; si puedes, deja la tarea a un compañero unos minutos.",
               "Pause what you are doing; if you can, hand the task to a crewmate for a few minutes."),
    "radiacion": ("Ve al área protegida de la nave y quédate allí hasta que pase el evento.",
                  "Go to the ship's shielded area and stay there until the event is over."),
}

RESPIRAR = ("Respira despacio: toma aire contando hasta 4 y suéltalo contando hasta 6. Calma el cuerpo y te ayuda a pensar.",
            "Breathe slowly: breathe in counting to 4 and out counting to 6. It calms the body and helps you think.")


def _plano(t: str) -> str:
    import rag
    return rag._texto_plano(t)


def es_companero(pregunta: str) -> bool:
    import rag
    texto = re.sub(rag.SIN_ENLACE, " ", _plano(pregunta))   # "la Tierra no responde" no es un compañero
    return bool(re.search(COMPANERO, texto))


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


def _datos(rojos: list[dict], reglas: dict) -> str:
    """'pulso en 148 lpm y oxígeno en 88 %' / 'pulse at 148 bpm and oxygen at 88 %'."""
    return T(" y ", " and ").join(f"{_nombre(i, reglas).lower()} {T('en', 'at')} {_valor(i)}" for i in rojos[:2])


def _fuente(archivo: str, seccion: str, fuente: str = "") -> dict:
    import rag
    titulo = next((f["guia"] for f in rag._fragmentos() if f["archivo"] == archivo), archivo)
    fuente = fuente or next((f.get("fuente", "") for f in rag._fragmentos() if f["archivo"] == archivo), "")
    return {"guia": titulo, "seccion": seccion, "fuente": fuente, "url": "", "version": "", "relevancia": 1.0}


def _secciones(*claves: str) -> str:
    return " · ".join(idioma.seccion(c) for c in claves)


def _bloque_enlace(conectado: bool, companero: bool = False) -> str:
    if conectado:
        return T("📡 **Hay enlace con la Tierra:** cuando la situación esté estable, enviaré el resumen a los médicos "
                 "de la Tierra. No esperes su respuesta para empezar a actuar.",
                 "📡 **There is a link to Earth:** when the situation is stable, I'll send the summary to the doctors "
                 "on Earth. Don't wait for their reply to start acting.")
    if companero:
        quien = T("Tú y la tripulación son", "You and the crew are")
    else:
        quien = T("La tripulación y el oficial médico de a bordo son", "The crew and the onboard medical officer are")
    return T(f"📡 **Sin enlace con la Tierra:** está bien, no los necesitas para dar los primeros pasos. {quien} "
             "el equipo que puede ayudar ahora. Anota la hora y lo que vaya pasando: guardo el resumen y lo envío "
             "solo en cuanto vuelva la señal.",
             f"📡 **No link to Earth:** that's okay, you don't need them for the first steps. {quien} "
             "the team that can help right now. Note the time and what happens: I'll keep the summary and send it "
             "automatically as soon as the signal is back.")


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
        alto, bajo = (T(*par) for par in SENSACION.get(i["indicador"], (("", ""), ("", ""))))
        texto = alto if _es_alto(i, regla) else bajo
        texto = texto or alto or bajo
        n = i.get("normal")
        cifra = round(n) if n is not None and abs(n) >= 20 else n
        normal = T(f" (tu normal es {cifra})", f" (your normal is {cifra})") if n is not None else ""
        if i["indicador"] == "radiacion":
            texto = T("hay un evento de clima espacial. La radiación no se siente en el momento: por eso hay que protegerse antes",
                      "there is a space weather event. Radiation cannot be felt at the moment: that is why you protect yourself beforehand")
        if not texto:
            texto = T("este valor está fuera de su rango seguro", "this value is outside its safe range")
        lineas.append(f"- **{_nombre(i, reglas)}: {_valor(i)}**{normal}: {texto}.")
    return lineas


def protocolo_alerta(estado: dict | None, conectado: bool) -> tuple[str, list[dict]]:
    """Indicadores propios en rojo: qué pasa, qué puedes sentir, a quién llamar y qué hacer."""
    import rag
    reglas = rag._reglas()
    rojos = _rojos(estado)
    datos = _datos(rojos, reglas)
    partes = [T("Estoy aquí contigo. Sé que ver una alerta asusta, pero no estás solo y lo vamos a hacer juntos, paso a paso.",
                "I'm here with you. I know seeing a warning is scary, but you are not alone and we'll do this together, step by step.")]
    partes.append(T("**Qué está pasando**", "**What is happening**") + "\n" + "\n".join(_que_pasa_con_tus_datos(rojos, reglas)))
    partes.append(T(f"**Llama a alguien ahora**\nDi en voz alta o por el intercomunicador: *«Necesito ayuda médica: "
                    f"tengo {datos}»*. Pide que venga el oficial médico de la tripulación y que alguien se quede contigo.",
                    f"**Call someone now**\nSay it out loud or over the intercom: *\"I need medical help: "
                    f"I have {datos}\"*. Ask the crew medical officer to come and someone to stay with you."))

    pasos, fuentes, vistas = [], [], set()
    for i in rojos[:2]:
        par = PRIMER_PASO.get(i["indicador"])
        pasos.append(T(*par) if par else "")
    pasos.append(T(*RESPIRAR))
    medir = ""
    for i in rojos[:2]:
        regla = reglas.get(i["indicador"]) or {"guia": "radiacion.md", "fuente": "NASA DONKI"}
        guia = regla.get("guia")
        if not guia or guia in vistas:
            continue
        vistas.add(guia)
        if not medir:
            medir = rag._seccion(guia, idioma.seccion("medir")).strip()
        fuentes.append(_fuente(guia, _secciones("hacer", "medir", "avisar"), regla.get("fuente", "")))
    vuelve = T("**Cuando ya estés acompañado, vuelve a medir** con el botón «+ Registrar medición» "
               "(nunca esperes una medición para pedir ayuda)",
               "**Once someone is with you, measure again** with the \"+ Log measurement\" button "
               "(never wait for a measurement to ask for help)")
    fiable = T("Para que el dato sea fiable: ", "For a reliable value: ")
    pasos.append(f"{vuelve}. {fiable + medir[0].lower() + medir[1:] if medir else ''}".strip())
    partes.append(T("**Qué hacer mientras llega la ayuda**", "**What to do while help arrives**") + "\n" + _numerar(pasos))
    partes.append(_bloque_enlace(conectado))
    partes.append(T("🚨 Si aparece **dolor de pecho, falta de aire, confusión o desmayo**, avisa de inmediato y sigan "
                    "el protocolo de emergencia de a bordo.",
                    "🚨 If **chest pain, shortness of breath, confusion or fainting** appears, alert immediately and "
                    "follow the onboard emergency protocol."))
    partes.append(T("Aquí sigo contigo. Cuéntame: ¿cómo te sientes ahora mismo? ¿Te duele el pecho o te falta el aire?",
                    "I'm still here with you. Tell me: how do you feel right now? Does your chest hurt or are you short of breath?"))
    return "\n\n".join(partes), fuentes


def protocolo_sintoma(estado: dict | None, conectado: bool, pregunta: str = "") -> tuple[str, list[dict]]:
    """El astronauta siente algo grave (dolor de pecho, falta de aire, desmayo), tenga o no datos en rojo."""
    import rag
    reglas = rag._reglas()
    rojos = _rojos(estado)
    partes = [T("Has hecho muy bien en decírmelo. Lo que sientes es serio y merece atención ya, pero no estás solo: "
                "vamos a actuar ahora, juntos.",
                "You did the right thing telling me. What you feel is serious and needs attention now, but you are not "
                "alone: let's act now, together.")]
    que = T("**Qué puede estar pasando**\nUn dolor o presión en el pecho, sobre todo si se va al brazo, al cuello o "
            "a la mandíbula, o si viene con sudor frío, falta de aire o mareo, puede venir del corazón o de los "
            "pulmones. Yo no puedo saber la causa exacta, pero sí sé que lo correcto es pedir ayuda sin esperar.",
            "**What may be happening**\nChest pain or pressure, especially if it spreads to the arm, neck or "
            "jaw, or comes with a cold sweat, shortness of breath or dizziness, can come from the heart or the "
            "lungs. I can't know the exact cause, but I do know the right thing is to ask for help without waiting.")
    if rojos:
        que += T("\n\nAdemás, tus datos muestran:\n", "\n\nYour data also shows:\n") + "\n".join(_que_pasa_con_tus_datos(rojos, reglas))
    partes.append(que)
    datos = (T(": tengo ", ": I have ") + _datos(rojos, reglas)) if rojos else ""
    partes.append(T(f"**Llama a alguien ahora**\nDi en voz alta o por el intercomunicador: *«¡Emergencia médica! "
                    f"{_frase_sintoma(pregunta)}{datos}»*. Pide que venga el oficial médico y que alguien "
                    "se quede a tu lado.",
                    f"**Call someone now**\nSay it out loud or over the intercom: *\"Medical emergency! "
                    f"{_frase_sintoma(pregunta)}{datos}\"*. Ask the medical officer to come and someone "
                    "to stay by your side."))
    pasos = [T("Deja lo que estés haciendo y sujétate en un lugar seguro: si te mareas, así no te golpeas.",
               "Stop what you are doing and secure yourself in a safe place: if you get dizzy, you won't hit anything."),
             T(*RESPIRAR),
             T("Si puedes, mide pulso y oxígeno (o pide que te los midan) y regístralos: le dirán mucho al oficial médico.",
               "If you can, measure your pulse and oxygen (or ask someone to) and log them: they will tell the medical officer a lot."),
             T("El oficial médico decide con el botiquín de a bordo y su protocolo de dolor de pecho; tú no tienes que decidirlo solo.",
               "The medical officer decides with the onboard medical kit and its chest pain protocol; you don't have to decide alone."),
             T("Si te desmayas, tus compañeros sabrán qué hacer: pueden escribirme *«mi compañero se desmayó»* y los guío.",
               "If you faint, your crewmates will know what to do: they can write to me *\"my crewmate fainted\"* and I'll guide them.")]
    partes.append(T("**Qué hacer ahora**", "**What to do now**") + "\n" + _numerar(pasos))
    partes.append(_bloque_enlace(conectado))
    partes.append(T("Aquí sigo contigo. ¿El dolor es fuerte, se va hacia el brazo o la mandíbula, o te falta el aire?",
                    "I'm still here with you. Is the pain strong, does it spread to your arm or jaw, or are you short of breath?"))
    respira = re.search(r"(respirar|aire|ahog|breath|choking)", _plano(pregunta))
    fuentes = [_fuente("oxigeno_aire.md" if respira else "presion_cardiovascular.md", _secciones("senales", "hacer")),
               _fuente(GUIA_COMPANERO, idioma.seccion("senales"))]
    return "\n\n".join(partes), fuentes


def _frase_sintoma(pregunta: str) -> str:
    p = _plano(pregunta)
    if re.search(r"(pecho|brazo|chest|arm)", p):
        return T("Me duele el pecho", "My chest hurts")
    if re.search(r"(respirar|aire|ahog|breath|choking)", p):
        return T("Me falta el aire", "I can't breathe well")
    return T("Me estoy mareando, siento que me voy a desmayar", "I'm getting dizzy, I feel like I'm going to faint")


def protocolo_companero(conectado: bool) -> tuple[str, list[dict]]:
    """Un compañero se desploma, no responde o tiene dolor de pecho."""
    import rag
    pasos = rag._pasos_de_la_guia(GUIA_COMPANERO, 10)
    por_que = rag._seccion(GUIA_COMPANERO, idioma.seccion("por_que")).strip()
    partes = [T("Mantén la calma: puedes ayudarle y no estás solo. Lo que hagan en los próximos minutos es lo que "
                "más importa, y te voy a guiar paso a paso.",
                "Stay calm: you can help them and you are not alone. What you do in the next few minutes is what "
                "matters most, and I'll guide you step by step.")]
    partes.append(T("**Pide ayuda ya**\nGrita *«¡Emergencia médica!»* o activa la alarma. Llama al oficial médico y pide "
                    "que alguien traiga **el botiquín de emergencia y el desfibrilador**.",
                    "**Get help now**\nShout *\"Medical emergency!\"* or activate the alarm. Call the medical officer and ask "
                    "someone to bring **the emergency kit and the defibrillator**."))
    partes.append(T("**Qué hacer**", "**What to do**") + "\n" + _numerar([p[0].upper() + p[1:] for p in pasos[1:]]))
    if por_que:
        partes.append(T("**Qué puede estar pasando**", "**What may be happening**") + "\n" + por_que)
    partes.append(_bloque_enlace(conectado, companero=True))
    partes.append(T("Lo estás haciendo bien. Cuando sepas si respira, cuéntamelo y te digo qué vigilar después.",
                    "You're doing well. Once you know whether they are breathing, tell me and I'll tell you what to watch next."))
    return "\n\n".join(partes), [_fuente(GUIA_COMPANERO, _secciones("hacer", "senales"))]
