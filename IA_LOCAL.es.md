[English](IA_LOCAL.md) | **Español**

# IA local de ORI

ORI responde **sin internet** usando las guías de salud de a bordo (`data/guias/` en español, `data/guias_en/` en inglés) y los datos del astronauta, y **siempre cita la fuente**.

## Cómo funciona

```
Pregunta → buscar en las guías (vectores de Ollama + palabras; solo palabras si no hay modelo)
         → + estado del astronauta (motor de reglas sobre los registros de SQLite)
         → modelo local (Ollama, gemma3:4b) redacta solo la explicación empática
         → los pasos y el "cuándo avisar" se copian tal cual de la guía
```

Reglas de seguridad (`backend/rag.py`, `backend/emergencia.py`):
- Las **alertas no las decide la IA**: si algún indicador está en rojo, siempre se agrega un aviso fijo.
- **Las emergencias no usan IA**: "me duele el pecho", "mi compañero se desmayó" o un indicador en rojo con "¿qué hago?" reciben un protocolo fijo e instantáneo.
- Si ninguna guía es relevante, ORI responde **"No tengo información…"** en vez de inventar; si una pregunta no tiene datos relacionados, se le indica a la IA que no mencione cifras.
- Si Ollama no está disponible, ORI entrega los fragmentos de las guías tal cual (**modo respaldo**).
- El prompt prohíbe diagnosticar e indicar medicamentos o dosis.

## Instalar (una sola vez, con internet)

Arch Linux:
```bash
sudo pacman -S ollama-cuda
sudo systemctl enable --now ollama
```
Windows o Mac: instalador en https://ollama.com/download

Modelos:
```bash
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

## Usar (sin internet)

Desde la raíz del repositorio:

```bash
python scripts/indexar_guias.py          # crea data/indice_guias.json y data/indice_guias_en.json (repetir si cambian las guías)
python scripts/probar_chat.py            # 10 preguntas de prueba, sin levantar la API
uv run --with fastapi --with uvicorn uvicorn backend.main:app --port 8000   # API: http://localhost:8000/docs
```

Variables opcionales: `MODELO_CHAT` (p. ej. `gemma3:1b` si va lento), `MODELO_EMBED`, `OLLAMA_URL`.

**Voz sin internet (opcional):** `python scripts/descargar_voces.py` descarga una vez las voces de ORI; luego agrega `--with faster-whisper --with numpy --with piper-tts` al comando del servidor. Whisper transcribe el micrófono y Piper le da voz a ORI, los dos en la misma computadora.

## Endpoints

| Endpoint | Qué hace |
|---|---|
| `POST /api/chat` | Entrada: `{"astronauta_id": "A1", "pregunta": "...", "conectado": true}`. Salida: `respuesta`, `fuentes[]`, `datos_usados`, `modo`, `alerta_roja`, `segundos` |
| `GET /api/ia/estado` | ¿Ollama corriendo? Modelos e índice |
| `POST /api/ia/recargar` | Recargar después de volver a indexar las guías |
| `POST /api/voz` · `POST /api/voz/hablar` | Voz a texto (Whisper) · texto a voz (Piper) |

`modo` puede ser: `ia_local` (respondió el modelo), `respaldo_sin_ia` (sin modelo, texto de la guía), `sin_informacion`, `resumen`, `conversacion`, `protocolo`, `emergencia` o `emergencia_companero`.

El idioma llega en la cookie `idioma` o con `?lang=en|es`; ORI, las guías y las reglas responden en ese idioma.

## Estado actual

- ✅ Ollama con gemma3:4b y nomic-embed-text; 11 guías indexadas en español e inglés.
- ✅ Respuestas en unos 0,3–2,5 s, citan la guía, respetan el color de cada dato y dicen "no tengo información" ante preguntas fuera de las guías.
- ✅ Búsqueda **híbrida**: los vectores ordenan y la coincidencia de palabras decide si hay algo relevante.
- ✅ Estado real desde la base de datos SQLite de a bordo y el motor de reglas; voz sin internet con Whisper y Piper.
- ✅ 155 pruebas automáticas en Python y 13 en JavaScript.
- Las guías son **ilustrativas** y se basan en información del Human Research Program de NASA; requieren revisión de medicina de vuelo.

> Código escrito con asistencia de IA (Claude) y revisado por el equipo.
