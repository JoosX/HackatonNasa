# ORI en la nube (Hugging Face Spaces, Docker, CPU gratis).
# Todo corre dentro del contenedor, igual que en la nave: Ollama (IA local), FastAPI, SQLite y la voz (Whisper + Piper).
# En la nave no hace falta Docker: ver IA_LOCAL.md.
# Escrito con asistencia de IA (Claude); revisado por el equipo.

# Ollama 0.40.7 (la misma versión probada en el equipo); solo se usa la CPU, así que se quitan las librerías de GPU.
FROM ollama/ollama:0.40.7 AS ollama
RUN rm -rf /usr/lib/ollama/cuda* /usr/lib/ollama/rocm* /usr/lib/ollama/vulkan* /usr/lib/ollama/mlx*

FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*
COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /usr/lib/ollama /usr/lib/ollama

# Hugging Face ejecuta el contenedor con el usuario 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS=/home/user/ollama \
    OLLAMA_KEEP_ALIVE=24h \
    MODELO_CHAT=gemma3:1b \
    MODELO_EMBED=nomic-embed-text \
    HF_HOME=/home/user/.cache/huggingface
WORKDIR /home/user/app

RUN pip install --no-cache-dir --user fastapi "uvicorn[standard]" faster-whisper numpy piper-tts==1.8.0

# Modelos de IA dentro de la imagen: la app arranca sin descargar nada.
RUN ollama serve > /tmp/ollama.log 2>&1 & \
    for i in $(seq 1 60); do ollama list > /dev/null 2>&1 && break; sleep 1; done; \
    ollama pull "$MODELO_CHAT" && ollama pull "$MODELO_EMBED"
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

COPY --chown=user scripts/descargar_voces.py scripts/descargar_voces.py
RUN python scripts/descargar_voces.py

COPY --chown=user . .

EXPOSE 7860
CMD ["bash", "scripts/iniciar_space.sh"]
