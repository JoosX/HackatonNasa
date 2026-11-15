**English** | [Español](IA_LOCAL.es.md)

# ORI's local AI

ORI answers **with no internet**, using the onboard health guides (`data/guias/` in Spanish, `data/guias_en/` in English) and the astronaut's data, and it **always cites its source**.

## How it works

```
Question → search the guides (Ollama vectors + keywords; keywords only if there is no model)
         → + astronaut status (rules engine over the SQLite records)
         → local model (Ollama, gemma3:4b) writes only the empathetic explanation
         → the steps and "when to alert" are copied verbatim from the guide
```

Safety rules (`backend/rag.py`, `backend/emergencia.py`):
- **Alerts are not decided by the AI**: if any indicator is red, a fixed warning is always added.
- **Emergencies skip the AI**: "my chest hurts", "my crewmate collapsed" or a red indicator plus "what should I do?" get a fixed, instant protocol.
- If no guide is relevant, ORI says **"I don't have information…"** instead of making something up; if a question has no related data, the AI is told not to mention any numbers.
- If Ollama is not available, ORI returns the guide passages as they are (**fallback mode**).
- The prompt forbids diagnosing or recommending medication or doses.

## Install (once, with internet)

Arch Linux:
```bash
sudo pacman -S ollama-cuda
sudo systemctl enable --now ollama
```
Windows or macOS: installer at https://ollama.com/download

Models:
```bash
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

## Use (no internet)

From the repository root:

```bash
python scripts/indexar_guias.py          # builds data/indice_guias.json and data/indice_guias_en.json (repeat if the guides change)
python scripts/probar_chat.py            # 10 test questions, without starting the API
uv run --with fastapi --with uvicorn uvicorn backend.main:app --port 8000   # API: http://localhost:8000/docs
```

Optional variables: `MODELO_CHAT` (e.g. `gemma3:1b` if it is slow), `MODELO_EMBED`, `OLLAMA_URL`.

**Offline voice (optional):** `python scripts/descargar_voces.py` downloads ORI's voices once; then add `--with faster-whisper --with numpy --with piper-tts` to the server command. Whisper transcribes the microphone and Piper gives ORI its voice, both on the same computer.

## Endpoints

| Endpoint | What it does |
|---|---|
| `POST /api/chat` | Input: `{"astronauta_id": "A1", "pregunta": "...", "conectado": true}`. Output: `respuesta`, `fuentes[]`, `datos_usados`, `modo`, `alerta_roja`, `segundos` |
| `GET /api/ia/estado` | Is Ollama running? Models and index status |
| `POST /api/ia/recargar` | Reload after re-indexing the guides |
| `POST /api/voz` · `POST /api/voz/hablar` | Speech to text (Whisper) · text to speech (Piper) |

`modo` can be: `ia_local` (the model answered), `respaldo_sin_ia` (no model, guide text), `sin_informacion`, `resumen`, `conversacion`, `protocolo`, `emergencia` or `emergencia_companero`.

The language comes from the `idioma` cookie or `?lang=en|es`; ORI, the guides and the rules answer in that language.

## Current status

- ✅ Ollama running gemma3:4b and nomic-embed-text; 11 guides indexed in Spanish and English.
- ✅ Answers in about 0.3–2.5 s, citing the guide, respecting each value's color and saying "I don't have information" for questions outside the guides.
- ✅ **Hybrid** search: vectors rank the passages and keyword overlap decides whether something is relevant.
- ✅ Real status from the onboard SQLite database and rules engine; offline voice with Whisper and Piper.
- ✅ 155 automated Python tests and 13 JavaScript tests.
- Guides are **illustrative** and based on NASA Human Research Program information; they need review by flight medicine.

> Code written with AI assistance (Claude) and reviewed by the team.
