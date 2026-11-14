"""
Sincronizacion simulada con la Tierra.

- Conectado: los datos "se envian" al instante (solo se actualiza ultima_sync).
- Sin conexion: cada medicion/alerta nueva se guarda en la cola_sync.
- Al reconectar: se "envia" todo lo pendiente y la cola queda en cero.

El estado se guarda en la base de datos, asi sobrevive a un reinicio del servidor.
"""
import json

import db

RETRASO_POR_DEFECTO = 14  # minutos que tarda un mensaje en llegar a la Tierra


def estado() -> dict:
    return {
        "conectado": db.get_config("sync_conectado", "1") == "1",
        "retraso_min": int(db.get_config("sync_retraso_min", str(RETRASO_POR_DEFECTO))),
        "pendientes": db.contar_pendientes(),
        "ultima_sync": db.get_config("sync_ultima"),
    }


def simular(conectado: bool | None = None, retraso_min: int | None = None) -> dict:
    """Cambia el estado de la senal. Sin argumentos, alterna conectado/desconectado."""
    actual = estado()
    nuevo = (not actual["conectado"]) if conectado is None else conectado
    enviados = 0

    if retraso_min is not None:
        db.set_config("sync_retraso_min", str(max(0, retraso_min)))

    db.set_config("sync_conectado", "1" if nuevo else "0")
    if nuevo:
        enviados = db.enviar_pendientes()
        db.set_config("sync_ultima", db.ahora_iso())

    return {**estado(), "enviados": enviados}


def registrar(tipo: str, payload: dict) -> None:
    """Llamar cada vez que se guarda algo que deberia viajar a la Tierra."""
    if estado()["conectado"]:
        db.set_config("sync_ultima", db.ahora_iso())
    else:
        db.encolar(tipo, json.dumps(payload, ensure_ascii=False))
