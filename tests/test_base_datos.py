"""Pruebas de la base de datos y el motor de reglas. Escrito con asistencia de IA (Claude); revisado por el equipo."""

import pytest

import db
import motor


@pytest.fixture(autouse=True)
def base_limpia():
    db.sembrar("T1", forzar=True, valor_num=motor.valor_num)


def indicador(estado, nombre):
    return next(i for i in estado["indicadores"] if i["indicador"] == nombre)


def test_historial_sembrado_cuenta_la_historia_de_la_demo():
    e = motor.evaluar("T1")
    pulso = indicador(e, "pulso")
    assert pulso["valor"] == 96 and pulso["color"] == "verde" and pulso["tendencia"] == "sube"
    assert 65 <= pulso["normal"] <= 75 and pulso["desviacion_pct"] > 20      # "tu normal" ~70
    assert indicador(e, "sueno")["color"] == "amarillo"
    assert any("noches seguidas" in n for n in e["notas"])


def test_registrar_medicion_actualiza_el_estado_y_guarda_alerta():
    r = motor.registrar("T1", "pulso", "150")
    assert r["color"] == "rojo" and not r["sospechoso"]
    assert indicador(motor.evaluar("T1"), "pulso")["valor"] == 150
    assert db.alertas("T1")[0]["indicador"] == "pulso"


def test_valor_imposible_es_sospechoso():
    r = motor.registrar("T1", "oxigeno", "30")
    assert r["sospechoso"] and "Repite la medición" in r["mensaje"]


@pytest.mark.parametrize("indicador_,valor", [("presion_arterial", "120"), ("pulso", "abc"), ("inventado", "1"), ("pulso", " ")])
def test_valores_invalidos_se_rechazan(indicador_, valor):
    with pytest.raises(ValueError):
        motor.registrar("T1", indicador_, valor)


def test_historial_para_graficas():
    h = motor.historial("T1")
    assert len(h["pulso"]) >= 7 and all("num" in p for p in h["pulso"])
    assert "vision" not in h   # lo categórico no se grafica


def test_api_registrar_y_reiniciar():
    from fastapi.testclient import TestClient
    from backend.main import app
    c = TestClient(app)
    r = c.post("/api/mediciones", json={"astronauta_id": "T1", "indicador": "pulso", "valor": "150"}).json()
    assert r["resultado"]["color"] == "rojo" and any(i["valor"] == 150 for i in r["estado"]["indicadores"])
    assert c.post("/api/mediciones", json={"astronauta_id": "T1", "indicador": "pulso", "valor": "x"}).status_code == 422
    e = c.post("/api/demo/reiniciar", params={"astronauta_id": "T1"}).json()
    assert indicador(e, "pulso")["valor"] == 96
    assert "pulso" in c.get("/api/historial/T1").json()


def test_pregunta_de_seguimiento_usa_el_tema_anterior(monkeypatch):
    import ollama_cliente
    import rag
    monkeypatch.setattr(ollama_cliente, "embeber", lambda *a, **k: (_ for _ in ()).throw(ollama_cliente.OllamaNoDisponible("x")))
    monkeypatch.setattr(ollama_cliente, "chatear", lambda *a, **k: (_ for _ in ()).throw(ollama_cliente.OllamaNoDisponible("x")))
    turnos = [{"rol": "astronauta", "texto": "Me siento con el corazón acelerado"}, {"rol": "ori", "texto": "..."}]
    r = rag.responder("¿y por qué pasa eso?", motor.evaluar("T1"), turnos)
    assert r.get("seguimiento_de") and "Por qué pasa en el espacio" in r["respuesta"]
