"""Configuración común de las pruebas. Escrito con asistencia de IA (Claude); revisado por el equipo."""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

# Las pruebas usan una base de datos temporal: nunca tocan data/mision.db.
os.environ.setdefault("DB_RUTA", str(Path(tempfile.mkdtemp()) / "prueba.db"))

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
sys.path.insert(0, str(RAIZ))

ORGANOS_CONTRATO = {"corazon", "cerebro", "pulmones", "huesos", "ojos", "sangre", "piel"}


@pytest.fixture(scope="session")
def raiz() -> Path:
    return RAIZ


@pytest.fixture(scope="session")
def reglas() -> dict:
    return json.loads((RAIZ / "data" / "reglas.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def fichas() -> dict:
    return json.loads((RAIZ / "data" / "fichas.json").read_text(encoding="utf-8"))


def clasificar(regla: dict, valor) -> str:
    """Evaluador de referencia de reglas.json (el motor real es de P4)."""
    if "categorias" in regla:
        return regla["categorias"].get(valor, "sin dato")
    if "componentes" in regla:
        partes = [float(x) for x in str(valor).split("/")]
        colores = [clasificar(c, v) for c, v in zip(regla["componentes"].values(), partes)]
        return max(colores, key=["verde", "amarillo", "rojo"].index)
    v = float(str(valor).replace(",", "."))
    if regla["verde"][0] <= v <= regla["verde"][1]:
        return "verde"
    if regla["amarillo"][0] <= v <= regla["amarillo"][1]:
        return "amarillo"
    return "rojo"


def estado_demo_frontend() -> list[dict]:
    """Lee ESTADO_DEMO de frontend/js/organos.js para comparar con las reglas."""
    js = (RAIZ / "frontend" / "js" / "organos.js").read_text(encoding="utf-8")
    patron = r'indicador:\s*"(\w+)",\s*valor:\s*("?[^,]+?"?),\s*unidad:[^,]+,\s*color:\s*"(\w+)"'
    return [{"indicador": i, "valor": v.strip('"'), "color": c} for i, v, c in re.findall(patron, js)]
