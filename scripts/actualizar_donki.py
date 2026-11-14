"""Sincroniza el clima espacial desde NASA DONKI y lo guarda en data/nasa_donki.json.

    python scripts/actualizar_donki.py [dias]

Representa la sincronización con la Tierra: cuando hay señal, la nave descarga los últimos
eventos solares; sin señal, la app sigue usando el último archivo guardado (y muestra su antigüedad).

Fuente: NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information), CCMC / NASA GSFC.
Desde el 30/09/2026 el servicio está en https://ccmc.gsfc.nasa.gov/DONKI-API/get/ (sin clave).
Si falla, se intenta https://api.nasa.gov/DONKI/ con la clave de NASA_API_KEY (o DEMO_KEY).

Código escrito con asistencia de IA (Claude); revisado por el equipo.
"""

import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "nasa_donki.json"
BASES = [
    "https://ccmc.gsfc.nasa.gov/DONKI-API/get/{tipo}?startDate={ini}&endDate={fin}",
    "https://api.nasa.gov/DONKI/{tipo}?startDate={ini}&endDate={fin}&api_key=" + os.environ.get("NASA_API_KEY", "DEMO_KEY"),
]


def descargar(tipo: str, ini: str, fin: str) -> list:
    for base in BASES:
        url = base.format(tipo=tipo, ini=ini, fin=fin)
        try:
            pedido = urllib.request.Request(url, headers={"User-Agent": "asistente-salud-prototipo"})
            with urllib.request.urlopen(pedido, timeout=40) as r:
                return json.loads(r.read().decode("utf-8") or "[]")
        except Exception as e:   # noqa: BLE001 - se prueba la siguiente fuente
            print(f"  {tipo}: {url.split('?')[0]} falló ({e})")
    raise RuntimeError(f"No se pudo descargar {tipo} de DONKI")


def main() -> None:
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    hoy = dt.datetime.now(dt.timezone.utc).date()
    ini, fin = str(hoy - dt.timedelta(days=dias)), str(hoy)

    eventos = []
    for f in descargar("FLR", ini, fin):            # llamaradas solares
        eventos.append({"tipo": "llamarada", "id": f.get("flrID"), "inicio": f.get("beginTime"),
                        "pico": f.get("peakTime"), "clase": f.get("classType"), "enlace": f.get("link")})
    for s in descargar("SEP", ini, fin):            # partículas energéticas solares (radiación)
        eventos.append({"tipo": "particulas", "id": s.get("sepID"), "inicio": s.get("eventTime"),
                        "pico": s.get("eventTime"), "clase": "SEP", "enlace": s.get("link")})
    for g in descargar("GST", ini, fin):            # tormentas geomagnéticas
        kp = max((k.get("kpIndex", 0) for k in g.get("allKpIndex") or []), default=None)
        eventos.append({"tipo": "tormenta_geomagnetica", "id": g.get("gstID"), "inicio": g.get("startTime"),
                        "pico": g.get("startTime"), "clase": f"Kp {kp:g}" if kp is not None else "GST", "kp": kp,
                        "enlace": g.get("link")})
    eventos.sort(key=lambda e: e.get("pico") or "")

    SALIDA.write_text(json.dumps({
        "fuente": "NASA DONKI – CCMC / NASA Goddard Space Flight Center",
        "url": "https://ccmc.gsfc.nasa.gov/tools/DONKI/",
        "sincronizado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "desde": ini, "hasta": fin,
        "eventos": eventos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    cuenta = {t: sum(e["tipo"] == t for e in eventos) for t in ("llamarada", "particulas", "tormenta_geomagnetica")}
    print(f"{len(eventos)} eventos {cuenta} -> {SALIDA}")


if __name__ == "__main__":
    main()
