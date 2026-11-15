"""Sensor simulado: envía signos vitales a la API cada cierto tiempo, como lo haría un sensor real.

    python scripts/sensor_simulado.py                 # pulso, oxígeno y temperatura cada 10 s
    python scripts/sensor_simulado.py --cada 5        # cada 5 segundos
    python scripts/sensor_simulado.py --subida        # el pulso sube poco a poco hasta alerta (para la demo)
    python scripts/sensor_simulado.py --veces 3       # solo 3 envíos

La app se actualiza sola cada 15 s y ORI avisa si un indicador pasa a alerta.
Necesita el servidor encendido (uvicorn backend.main:app --port 8000).

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import argparse
import json
import random
import time
import urllib.request

API = "http://localhost:8000"


def enviar(indicador: str, valor) -> dict:
    datos = json.dumps({"astronauta_id": "A1", "indicador": indicador, "valor": str(valor), "origen": "sensor"}).encode()
    pedido = urllib.request.Request(f"{API}/api/mediciones", data=datos, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=10) as r:
        return json.loads(r.read())["resultado"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cada", type=float, default=10, help="segundos entre envíos")
    p.add_argument("--veces", type=int, default=0, help="número de envíos (0 = sin fin)")
    p.add_argument("--subida", action="store_true", help="el pulso sube hasta alerta")
    a = p.parse_args()

    pulso, oxigeno, temp = 82.0, 97.0, 36.7
    n = 0
    print("Sensor simulado enviando a", API, "(Ctrl+C para detener)")
    while not a.veces or n < a.veces:
        pulso += 6 if a.subida else random.uniform(-3, 3)
        pulso = max(55, min(165, pulso))
        oxigeno = max(90, min(99, oxigeno + random.uniform(-0.6, 0.6)))
        temp = max(36.2, min(37.3, temp + random.uniform(-0.05, 0.05)))
        for ind, val in (("pulso", round(pulso)), ("oxigeno", round(oxigeno)), ("temperatura", round(temp, 1))):
            r = enviar(ind, val)
            print(f"  {ind:12s} {val:>6} {r['unidad']:<4} -> {r['color']}")
        n += 1
        time.sleep(a.cada)


if __name__ == "__main__":
    main()
