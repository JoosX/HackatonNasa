"""Descarga las voces de ORI (Piper) a data/voces/. Se hace una sola vez, con internet; después ORI habla sin conexión.

    python scripts/descargar_voces.py

Voces (repositorio oficial del proyecto Piper en Hugging Face, ~60 MB cada una):
    es_MX-ald-medium     (español)
    en_US-lessac-medium  (inglés)

Para que el servidor las use: uv run --with piper-tts ... (ver README, sección Voz).

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import sys
import urllib.request
from pathlib import Path

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
VOCES = {"es_MX-ald-medium": "es/es_MX/ald/medium", "en_US-lessac-medium": "en/en_US/lessac/medium"}
CARPETA = Path(__file__).resolve().parent.parent / "data" / "voces"


def main() -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    for nombre, ruta in VOCES.items():
        for ext in (".onnx", ".onnx.json"):
            destino = CARPETA / f"{nombre}{ext}"
            if destino.exists() and destino.stat().st_size > 0:
                print("  ya está:", destino.name)
                continue
            print("  descargando:", destino.name, "…", end=" ", flush=True)
            try:
                urllib.request.urlretrieve(f"{BASE}/{ruta}/{nombre}{ext}", destino)
            except OSError as e:
                print("falló:", e)
                sys.exit(1)
            print(f"{destino.stat().st_size / 1e6:.0f} MB")
    print("Listo. Voces en", CARPETA)


if __name__ == "__main__":
    main()
