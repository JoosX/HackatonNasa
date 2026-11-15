"""Pruebas del asistente RAG y de la API.
Las pruebas con el modelo se saltan solas si Ollama no está corriendo.
Escrito con asistencia de IA (Claude); revisado por el equipo."""

import pytest

import ollama_cliente
import rag

ESTADO_ROJO = {"indicadores": [{"indicador": "pulso", "valor": 150, "unidad": "lpm", "color": "rojo", "antiguedad_min": 1}]}
ESTADO_VERDE = {"indicadores": [{"indicador": "pulso", "valor": 70, "unidad": "lpm", "color": "verde", "antiguedad_min": 1}]}
hay_ollama = pytest.mark.skipif(not ollama_cliente.disponible(), reason="Ollama no está corriendo")


@pytest.fixture
def sin_ollama(monkeypatch):
    """Simula que Ollama está apagado: la app debe seguir respondiendo con las guías."""
    def falla(*_a, **_k):
        raise ollama_cliente.OllamaNoDisponible("apagado (prueba)")
    monkeypatch.setattr(ollama_cliente, "embeber", falla)
    monkeypatch.setattr(ollama_cliente, "chatear", falla)


@pytest.mark.parametrize("pregunta", ["¿Cuál es la capital de Francia?", "Me torcí el tobillo", "receta de pizza"])
def test_fuera_de_las_guias_no_inventa(sin_ollama, pregunta):
    r = rag.responder(pregunta, ESTADO_VERDE)
    assert r["modo"] == "sin_informacion"
    assert r["fuentes"] == []
    assert "No tengo información" in r["respuesta"]


@pytest.mark.parametrize("pregunta,guia", [
    ("Me duele la cabeza", "Dolor de cabeza en el espacio"),
    ("No puedo dormir bien", "Sueño y fatiga en misiones espaciales"),
    ("Mi oxígeno salió bajo", "Oxígeno en sangre y aire de la nave"),
    ("Tengo una erupción en la piel", "Temperatura corporal y piel"),
    ("Hay aviso de tormenta solar", "Radiación espacial"),
])
def test_encuentra_la_guia_correcta_sin_ia(sin_ollama, pregunta, guia):
    r = rag.responder(pregunta, ESTADO_VERDE)
    assert r["modo"] == "respaldo_sin_ia"
    assert guia in [f["guia"] for f in r["fuentes"]]


def test_alerta_roja_la_deciden_las_reglas(sin_ollama):
    """Con un indicador en rojo, el aviso fijo aparece siempre, haya o no IA."""
    r = rag.responder("Siento el corazón rápido", ESTADO_ROJO)
    assert r["alerta_roja"] is True
    assert r["respuesta"].startswith(rag.AVISO_ROJO)
    r2 = rag.responder("¿Cuál es la capital de Francia?", ESTADO_ROJO)
    assert r2["respuesta"].startswith(rag.AVISO_ROJO)


def test_resumen_de_estado():
    texto, rojo = rag.resumir_estado(ESTADO_ROJO)
    assert "Pulso" in texto and "en alerta" in texto and rojo
    assert rag.resumir_estado(None) == ("Sin datos recientes del astronauta.", False)


@hay_ollama
def test_ia_local_responde_con_fuente():
    r = rag.responder("Me duele la cabeza y dormí 4 horas, ¿qué hago?", ESTADO_VERDE)
    assert r["modo"] == "ia_local"
    assert r["fuentes"]
    assert len(r["respuesta"]) > 40


@hay_ollama
def test_ia_local_no_inventa_fuera_de_tema():
    r = rag.responder("¿Cuál es la capital de Francia?", ESTADO_VERDE)
    assert r["modo"] == "sin_informacion"


# ---------- API ----------

@pytest.fixture(scope="module")
def cliente():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


def test_api_fichas_reglas_y_nasa(cliente):
    assert len(cliente.get("/api/fichas").json()["fichas"]) == 8
    assert len(cliente.get("/api/reglas").json()["indicadores"]) >= 10
    assert "C001" in cliente.get("/api/nasa/osd575").json()["tripulantes"]


def test_api_chat_acepta_estado_propio_solo_en_modo_demo(cliente, sin_ollama):
    r = cliente.post("/api/chat", json={"pregunta": "Siento el corazón rápido", "estado": {**ESTADO_ROJO, "modo_demo": True}}).json()
    for clave in ("respuesta", "fuentes", "datos_usados", "modo", "alerta_roja", "segundos"):
        assert clave in r
    assert r["alerta_roja"] is True


def test_api_sirve_el_frontend(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "Copiloto de salud" in r.text
    assert cliente.get("/modelos/cuerpo.glb").status_code == 200


# ---------- Comprensión de preguntas naturales (errores reportados en la revisión) ----------

@pytest.mark.parametrize("pregunta,intencion", [
    ("hola", "saludo"), ("Buenas tardes", "saludo"), ("gracias", "gracias"),
    ("¿qué puedes hacer?", "ayuda"), ("¿cómo estoy?", "estado"), ("dame un resumen", "estado"),
    ("¿qué significa el color amarillo?", "colores"),
    ("hola, me duele la cabeza", None),   # saludo + síntoma: va a las guías
])
def test_intenciones(pregunta, intencion):
    assert rag.detectar_intencion(pregunta) == intencion


def test_saludo_no_parece_un_error(sin_ollama):
    r = rag.responder("hola", ESTADO_VERDE)
    assert r["modo"] == "conversacion" and "No tengo información" not in r["respuesta"]


def test_como_estoy_resume_lo_que_esta_fuera_de_rango(sin_ollama):
    estado = {"indicadores": [
        {"indicador": "pulso", "valor": 150, "unidad": "lpm", "color": "rojo"},
        {"indicador": "sueno", "valor": 4.5, "unidad": "h", "color": "amarillo"},
        {"indicador": "oxigeno", "valor": 97, "unidad": "%", "color": "verde"}]}
    r = rag.responder("¿cómo estoy?", estado)
    assert r["modo"] == "resumen"
    assert "Pulso" in r["respuesta"] and "alerta" in r["respuesta"] and "precaución" in r["respuesta"]
    assert r["respuesta"].index("Pulso") < r["respuesta"].index("Sueño")   # lo rojo primero
    assert r["fuentes"]


@pytest.mark.parametrize("pregunta,guia", [
    ("me siento mareado", "Presión arterial y pulso en microgravedad"),
    ("estoy estresado", "Ánimo, estrés y salud mental"),
    ("¿por qué baja mi oxígeno en la nave?", "Oxígeno en sangre y aire de la nave"),   # "me cuesta respirar" ahora es urgencia
    ("me duele el pecho", "Presión arterial y pulso en microgravedad"),
    ("hola, me duele la cabeza", "Dolor de cabeza en el espacio"),
    ("tengo frío", "Temperatura corporal y piel"),
])
def test_entiende_como_habla_el_astronauta(sin_ollama, pregunta, guia):
    r = rag.responder(pregunta, ESTADO_VERDE)
    assert r["fuentes"] and r["fuentes"][0]["guia"] == guia


def test_sintoma_sin_guia_dice_que_hacer_mientras(sin_ollama):
    r = rag.responder("me sangra la nariz", ESTADO_VERDE)
    assert r["modo"] == "sin_informacion"
    assert "Mientras tanto" in r["respuesta"] and "avisa de inmediato" in r["respuesta"]


def test_api_estado_existe(cliente):
    d = cliente.get("/api/estado/A1").json()
    assert len(d["indicadores"]) == 11 and d["origen"] == "base de datos"
    assert any(i["indicador"] == "radiacion" for i in d["indicadores"])


def test_los_pasos_salen_textuales_de_la_guia(sin_ollama):
    """Los pasos y el 'cuándo avisar' se copian de la guía de NASA: la IA no puede inventarlos."""
    r = rag.responder("Llevo varios días con el ánimo bajo", ESTADO_VERDE)
    pasos = rag._pasos_de_la_guia("animo_estres.md")
    assert pasos and all(p in r["respuesta"] for p in pasos[:3])
    assert "Cuándo avisar a la tripulación" in r["respuesta"] and "Alerta" in r["respuesta"]


def test_pregunta_mixta_usa_dos_guias(sin_ollama):
    r = rag.responder("Me duele la cabeza y dormí 4 horas, ¿qué hago?", ESTADO_VERDE)
    assert {"Dolor de cabeza en el espacio", "Sueño y fatiga en misiones espaciales"} <= {f["guia"] for f in r["fuentes"]}


# --- Alerta roja sin enlace con la Tierra: ORI siempre da un protocolo paso a paso ---
def _estado_rojo():
    return {"indicadores": [
        {"indicador": "pulso", "nombre": "Pulso", "valor": 148, "unidad": "lpm", "color": "rojo"},
        {"indicador": "oxigeno", "nombre": "Oxígeno", "valor": 97, "unidad": "%", "color": "verde"}]}


import pytest as _pytest


@_pytest.mark.parametrize("pregunta", ["¿qué hago?", "ayuda", "me siento mal", "emergencia",
                                       "no hay conexión con la Tierra, ¿qué hago?"])
def test_protocolo_alerta_sin_enlace(pregunta):
    import rag
    r = rag.responder(pregunta, _estado_rojo(), [], conectado=False)
    assert r["modo"] == "protocolo"
    assert "tripulación" in r["respuesta"] and "Sin enlace con la Tierra" in r["respuesta"]
    assert "148" in r["respuesta"]
    assert r["fuentes"]


def test_protocolo_detecta_sin_senal_en_la_pregunta():
    import rag
    r = rag.responder("se perdió la señal, ¿qué hago?", _estado_rojo(), [], conectado=True)
    assert r["modo"] == "protocolo" and r["conectado"] is False


def test_sin_alerta_ayuda_sigue_siendo_menu():
    import rag
    verde = {"indicadores": [{"indicador": "pulso", "valor": 70, "unidad": "lpm", "color": "verde"}]}
    assert rag.responder("ayuda", verde, [])["modo"] != "protocolo"


# --- El caso del video del desafío: un compañero se desploma; dolor de pecho propio ---
@_pytest.mark.parametrize("pregunta", ["Mi compañero se desmayó y no responde", "el comandante se cayó y no se mueve",
                                       "mi compañera tiene dolor en el pecho", "¿se está muriendo?"])
def test_protocolo_companero(pregunta):
    import rag
    r = rag.responder(pregunta, None, [], conectado=False)
    assert r["modo"] == "emergencia_companero"
    t = r["respuesta"]
    assert "¡Emergencia médica!" in t and "desfibrilador" in t and "RCP" in t
    assert "respira" in t and "Sin enlace con la Tierra" in t
    assert r["fuentes"][0]["guia"].startswith("Emergencia")


@_pytest.mark.parametrize("pregunta", ["me duele el pecho", "no puedo respirar", "siento que me voy a desmayar"])
def test_sintoma_grave_aun_con_datos_normales(pregunta):
    import rag
    verde = {"indicadores": [{"indicador": "pulso", "valor": 72, "unidad": "lpm", "color": "verde"}]}
    r = rag.responder(pregunta, verde, [])
    assert r["modo"] == "emergencia"
    assert "Llama a alguien ahora" in r["respuesta"] and "oficial médico" in r["respuesta"]


def test_protocolo_explica_que_se_siente_y_a_quien_llamar():
    import rag
    t = rag.responder("¿qué hago?", _estado_rojo(), [], conectado=False)["respuesta"]
    assert "Qué está pasando" in t and "palpitaciones" in t          # qué se siente
    assert "Llama a alguien ahora" in t and "«Necesito ayuda médica" in t   # a quién y qué decir
    assert "no estás solo" in t                                        # empatía, no respuesta seca
    assert t.rstrip().endswith("?")                                    # sigue la conversación


def test_no_responde_la_tierra_no_es_un_companero():
    import emergencia
    assert not emergencia.es_companero("no responde la Tierra")


def test_api_chat_no_confia_en_el_estado_del_navegador(cliente, sin_ollama):
    """Sin modo_demo, un estado enviado por el navegador (quizá antiguo) se ignora: manda la base de datos."""
    import db, motor
    db.sembrar("A1", forzar=True, valor_num=motor.valor_num)   # base sin alertas rojas
    falso = {"indicadores": [{"indicador": "pulso", "valor": 190, "unidad": "lpm", "color": "rojo"}]}
    r = cliente.post("/api/chat", json={"pregunta": "¿Cómo estoy?", "estado": falso}).json()
    assert "190" not in r["respuesta"]
