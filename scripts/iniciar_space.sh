#!/usr/bin/env bash
# Arranca ORI en el contenedor de Hugging Face Spaces: primero Ollama, luego la app en el puerto 7860.
# Escrito con asistencia de IA (Claude); revisado por el equipo.
set -u

ollama serve > /tmp/ollama.log 2>&1 &

for _ in $(seq 1 60); do
  curl -sf http://127.0.0.1:11434/api/tags > /dev/null && break
  sleep 1
done

# Si en la configuración del Space se eligió otro modelo (p. ej. MODELO_CHAT=gemma3:4b), se descarga una vez.
ollama list | grep -q "^${MODELO_CHAT}" || ollama pull "${MODELO_CHAT}" || echo "No se pudo descargar ${MODELO_CHAT}; ORI usará el modo respaldo."

# Carga el modelo en memoria para que la primera pregunta no tarde tanto.
curl -s http://127.0.0.1:11434/api/generate \
  -d "{\"model\": \"${MODELO_CHAT}\", \"prompt\": \"hola\", \"stream\": false}" > /dev/null &

exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 7860
