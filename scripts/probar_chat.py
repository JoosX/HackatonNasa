"""Prueba el asistente con preguntas típicas (sin levantar la API).

    python scripts/probar_chat.py

Muestra el modo usado (ia_local, respaldo_sin_ia o sin_informacion),
las fuentes y el tiempo de cada respuesta. Ideal para probar con el wifi apagado.

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))

import rag  # noqa: E402

PREGUNTAS = [
    "Me duele la cabeza y dormí 4 horas, ¿qué hago?",
    "Mi presión salió alta, ¿es grave?",
    "No puedo dormir bien desde hace varios días",
    "¿Cómo debo medirme la presión en microgravedad?",
    "Siento el corazón muy rápido estando en reposo",
    "¿Cuándo tengo que avisar a la tripulación por el sueño?",
    "Tengo un dolor de cabeza muy fuerte y veo borroso",
    "¿Qué pasa con la sangre en el espacio?",
    "¿Cuál es la capital de Francia?",          # debe decir que no tiene información
    "Me torcí el tobillo",                       # no hay guía: debe decir que no tiene información
]


def main() -> None:
    estado = json.loads((RAIZ / "data" / "estado_ejemplo.json").read_text(encoding="utf-8"))
    for pregunta in PREGUNTAS:
        inicio = time.time()
        r = rag.responder(pregunta, estado)
        fuentes = ", ".join(f"{f['guia']} ({f['seccion']})" for f in r["fuentes"]) or "—"
        print("=" * 80)
        print("P:", pregunta)
        print(f"Modo: {r['modo']} · búsqueda: {r['busqueda']} · {time.time() - inicio:.1f} s")
        print("Fuentes:", fuentes)
        print("-" * 80)
        print(r["respuesta"][:700])


if __name__ == "__main__":
    main()
