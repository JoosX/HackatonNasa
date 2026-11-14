# IA local del asistente (P5)

Asistente de salud que responde **sin internet** usando las guías de `data/guias/` y los datos del astronauta, y **cita la fuente**.

## Cómo funciona

```
Pregunta → buscar en las guías (vectores con Ollama, o palabras si no hay modelo)
         → + estado del astronauta (lo calcula P4 con las reglas)
         → modelo local (Ollama, gemma3:4b) redacta la respuesta con "Fuente:"
```

Reglas de seguridad (están en `backend/rag.py`):
- Las **alertas no las decide la IA**: si el estado trae un indicador en rojo, se antepone siempre un aviso fijo.
- Si ninguna guía es relevante, responde **"No tengo información…"** en vez de inventar.
- Si Ollama no está disponible, entrega los fragmentos de las guías tal cual (**modo respaldo**).
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
python scripts/indexar_guias.py          # crea data/indice_guias.json (repetir si cambian las guías)
python scripts/probar_chat.py            # 10 preguntas de prueba, sin levantar la API
uvicorn backend.main:app --reload --port 8000   # API: http://localhost:8000/docs
```

Instalar dependencias de la API: `pip install -r requirements.txt` (o `uv run --with fastapi --with uvicorn ...`).

Variables opcionales: `MODELO_CHAT` (p. ej. `gemma3:1b` si va lento), `MODELO_EMBED`, `OLLAMA_URL`.

## Endpoints

| Endpoint | Para quién | Qué hace |
|---|---|---|
| `POST /api/chat` | P3 (chat) | Entrada: `{"astronauta_id": "A1", "pregunta": "..."}`. Salida: `respuesta`, `fuentes[]`, `datos_usados`, `modo`, `alerta_roja`, `segundos` |
| `GET /api/ia/estado` | P3 (indicador) | ¿Ollama corriendo?, modelos, índice listo |
| `POST /api/ia/recargar` | P6 | Recargar después de volver a indexar |

`modo` puede ser: `ia_local` (respondió el modelo), `respaldo_sin_ia` (sin modelo, devuelve guías) o `sin_informacion`.

## Para el resto del equipo

- **P4:** reemplazar `obtener_estado()` en `backend/main.py` por el estado real. Formato esperado: `data/estado_ejemplo.json`. Tus endpoints van en el mismo `main.py`.
- **P6:** las guías van en `data/guias/*.md` con el encabezado `titulo`, `fuente`, `url`, `version` y secciones `## `. Cada sección es un fragmento que se puede citar. Después de agregar guías: `python scripts/indexar_guias.py`.
- **P3:** mostrar `respuesta` y, debajo, las `fuentes` (guía y sección). Si `alerta_roja` es `true`, resaltar el mensaje en rojo.

## Estado actual

- ✅ Ollama instalado (gemma3:4b + nomic-embed-text) en la laptop con RTX 4090; guías indexadas.
- ✅ 10 preguntas de prueba con el modelo local: respuestas en ~0,5–2,5 s, citan la guía, respetan el color de cada dato y dicen "no tengo información" ante preguntas fuera de las guías.
- ✅ Búsqueda **híbrida**: el vector ordena y la coincidencia de palabras decide si hay algo relevante (nomic-embed-text da puntajes muy parecidos en español; mejora futura: probar `bge-m3`).
- ⏳ Falta: probar con el wifi apagado frente al equipo y conectar el estado real de P4.
- 3 guías de ejemplo (sueño, presión/pulso, dolor de cabeza), **ilustrativas**: P6 las amplía y corrige.

> Código escrito con asistencia de IA (Claude) y revisado por el equipo. Declararlo en la entrega.
