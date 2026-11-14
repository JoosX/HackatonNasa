"""Lee las guías de salud (data/guias/*.md) y las corta en fragmentos.

Cada guía tiene un encabezado con titulo, fuente, url y version, y
secciones que empiezan con "## ". Cada sección es un fragmento: así la
respuesta puede citar exactamente de qué parte de qué guía salió.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_GUIAS = RAIZ / "data" / "guias"


def leer_guia(ruta: Path) -> tuple[dict, str]:
    texto = ruta.read_text(encoding="utf-8")
    meta: dict = {"archivo": ruta.name}
    if texto.startswith("---"):
        _, encabezado, texto = texto.split("---", 2)
        for linea in encabezado.strip().splitlines():
            if ":" in linea:
                clave, valor = linea.split(":", 1)
                meta[clave.strip()] = valor.strip()
    meta.setdefault("titulo", ruta.stem)
    return meta, texto.strip()


def fragmentar(meta: dict, cuerpo: str) -> list[dict]:
    """Un fragmento por sección '## ...'."""
    fragmentos = []
    seccion, lineas = "Introducción", []

    def cerrar():
        contenido = "\n".join(lineas).strip()
        if contenido:
            fragmentos.append(
                {
                    "guia": meta["titulo"],
                    "seccion": seccion,
                    "texto": contenido,
                    "fuente": meta.get("fuente", ""),
                    "url": meta.get("url", ""),
                    "version": meta.get("version", ""),
                    "archivo": meta["archivo"],
                }
            )

    for linea in cuerpo.splitlines():
        if linea.startswith("## "):
            cerrar()
            seccion, lineas = linea[3:].strip(), []
        else:
            lineas.append(linea)
    cerrar()
    return fragmentos


def cargar_fragmentos() -> list[dict]:
    todos = []
    for ruta in sorted(CARPETA_GUIAS.glob("*.md")):
        meta, cuerpo = leer_guia(ruta)
        todos.extend(fragmentar(meta, cuerpo))
    return todos
