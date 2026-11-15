"""Indexa las guías: calcula un vector (embedding) por fragmento con Ollama
y lo guarda en data/indice_guias.json (español) y data/indice_guias_en.json (inglés).

Ejecutar cada vez que P6 agregue o cambie guías:
    python scripts/indexar_guias.py

Requiere Ollama corriendo con el modelo de embeddings descargado
(ollama pull nomic-embed-text). Funciona sin internet.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import idioma  # noqa: E402
import ollama_cliente  # noqa: E402
from guias import RAIZ, cargar_fragmentos  # noqa: E402

SALIDAS = {"es": RAIZ / "data" / "indice_guias.json", "en": RAIZ / "data" / "indice_guias_en.json"}


def main() -> None:
    for lengua, salida in SALIDAS.items():
        with idioma.usar(lengua):
            print(f"[{lengua}]", end=" ")
            indexar(salida)


def indexar(SALIDA: Path) -> None:
    fragmentos = cargar_fragmentos()
    if not fragmentos:
        print("No hay guías en", idioma.carpeta_guias())
        return
    print(f"{len(fragmentos)} fragmentos en {len({f['archivo'] for f in fragmentos})} guías.")

    if not ollama_cliente.disponible():
        print("Ollama no responde en", ollama_cliente.OLLAMA_URL)
        print("Inicia Ollama y descarga el modelo:  ollama pull", ollama_cliente.MODELO_EMBED)
        sys.exit(1)

    inicio = time.time()
    # nomic-embed-text recomienda este prefijo para documentos.
    textos = [f"search_document: {f['guia']} – {f['seccion']}\n{f['texto']}" for f in fragmentos]
    vectores = ollama_cliente.embeber(textos)
    for f, v in zip(fragmentos, vectores):
        f["vector"] = v

    SALIDA.write_text(
        json.dumps(
            {"modelo": ollama_cliente.MODELO_EMBED, "creado": time.strftime("%Y-%m-%d %H:%M"),
             "fragmentos": fragmentos},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Índice guardado en {SALIDA} ({time.time() - inicio:.1f} s).")


if __name__ == "__main__":
    main()
