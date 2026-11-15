"""Idioma de cada petición (español o inglés).

La app envía el idioma en la cookie "idioma" (o ?lang=en en la URL). main.py lo fija al inicio de cada
petición y el resto del código lo consulta con actual() o elige un texto con t("español", "English").
Los datos traducidos viven en data/en/ (mismo nombre de archivo) y las guías en data/guias_en/.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import contextvars
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IDIOMAS = ("es", "en")
_actual: contextvars.ContextVar[str] = contextvars.ContextVar("idioma", default="es")


def normalizar(valor: str | None) -> str:
    valor = (valor or "").strip().lower()[:2]
    return valor if valor in IDIOMAS else "es"


def fijar(valor: str | None) -> contextvars.Token:
    return _actual.set(normalizar(valor))


def restaurar(token: contextvars.Token) -> None:
    _actual.reset(token)


def actual() -> str:
    return _actual.get()


def en() -> bool:
    return actual() == "en"


def t(es: str, en_: str) -> str:
    """Texto en el idioma activo."""
    return en_ if en() else es


class usar:
    """Bloque con un idioma fijo (pruebas y scripts):  with idioma.usar("en"): ..."""

    def __init__(self, valor: str):
        self.valor = valor

    def __enter__(self):
        self.token = fijar(self.valor)
        return self

    def __exit__(self, *_):
        restaurar(self.token)


def carpeta_guias() -> Path:
    return RAIZ / "data" / ("guias_en" if en() else "guias")


def datos(nombre: str) -> Path:
    """Ruta de un archivo de data/ en el idioma activo (si no hay traducción, el original)."""
    traducido = RAIZ / "data" / "en" / nombre
    return traducido if en() and traducido.exists() else RAIZ / "data" / nombre


def reglas() -> dict:
    """reglas.json con nombres, unidades, acciones y validación en el idioma activo."""
    base = json.loads((RAIZ / "data" / "reglas.json").read_text(encoding="utf-8"))
    if not en():
        return base
    capa = json.loads((RAIZ / "data" / "en" / "reglas.json").read_text(encoding="utf-8"))
    base["_nota"] = capa.get("_nota", base.get("_nota"))
    for r in base["indicadores"]:
        trad = capa["indicadores"].get(r["indicador"], {})
        for clave, valor in trad.items():
            if isinstance(valor, dict) and isinstance(r.get(clave), dict):
                r[clave] = {**r[clave], **valor}
            else:
                r[clave] = valor
    return base


# Nombres de las secciones de las guías en cada idioma (las guías en inglés usan los de la derecha).
SECCIONES = {
    "por_que": ("Por qué importa", "Why it matters"),
    "espacio": ("Qué pasa en el espacio", "What happens in space"),
    "medir": ("Cómo medir a bordo", "How to measure on board"),
    "senales": ("Señales de alerta", "Warning signs"),
    "hacer": ("Qué hacer", "What to do"),
    "avisar": ("Cuándo avisar", "When to alert"),
}


def seccion(clave: str) -> str:
    """Nombre de una sección de guía en el idioma activo: seccion("hacer") -> "Qué hacer" / "What to do"."""
    return t(*SECCIONES[clave])
