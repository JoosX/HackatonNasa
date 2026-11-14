# Copiloto de salud · prototipo (NASA Space Apps 2026)

Asistente de salud **local** para astronautas: monitoreo con semáforo, cuerpo 3D anatómico y asistente con IA que responde **sin conexión** citando guías de NASA. Prototipo TRL 3–4; no diagnostica.

## Ejecutar

Requisitos: Python 3, [uv](https://docs.astral.sh/uv/) (o `pip install -r requirements.txt`) y, para la IA, Ollama con `gemma3:4b` y `nomic-embed-text` (ver `IA_LOCAL.md`).

Desde la raíz del repositorio:

```bash
uv run --with fastapi --with uvicorn uvicorn backend.main:app --port 8000
```

Abrir http://localhost:8000 en Chrome o Chromium (el visor 3D necesita WebGL).

Atajos para la demo: `?organo=corazon` abre un órgano (la cámara lo enfoca) · `#emergencia` simula una emergencia · `#sinsenal` empieza sin conexión · `#hover-corazon` muestra la tarjeta de hover (capturas) · `?quieto` detiene el giro.

En el visor: etiquetas anatómicas con línea guía (clic para abrir), tarjeta al pasar el mouse con valores y tendencia, capas (piel, esqueleto, vasos, órganos), pausa del giro y "Vista completa". Tipografía técnica: JetBrains Mono (OFL), incluida en `frontend/fuentes/`.

El modelo de IA (Gemma 3 4B, ~3,4 GB) no está en el repositorio: cada integrante lo descarga con `ollama pull gemma3:4b` y `ollama pull nomic-embed-text`. El índice de búsqueda de las guías (`data/indice_guias.json`) sí está incluido.

## Pruebas

```bash
uv run --with pytest --with fastapi --with httpx python -m pytest -q tests
```

43 pruebas: guías, reglas del semáforo, fichas (5 preguntas del reto), datos NASA OSD-575, contrato del modelo 3D, asistente sin IA (no inventa, alerta roja fija) y con IA (se saltan si Ollama está apagado), y la API.

## Estructura y dueños

| Carpeta / archivo | Qué es | Dueño |
|---|---|---|
| `frontend/index.html`, `css/app.css`, `js/app.js` | App principal: visor, signos, ficha, chat, conexión | P2 / P3 |
| `frontend/js/visor3d.js`, `modelos/cuerpo.glb` | Visor 3D y modelo anatómico | P3 / P5 |
| `frontend/js/chat.js` | Chat con el asistente | P3 |
| `backend/main.py` | API (FastAPI) y servidor del frontend | P4 |
| `backend/rag.py`, `ollama_cliente.py`, `guias.py` | Asistente RAG local | P5 |
| `data/guias/*.md`, `reglas.json`, `fichas.json`, `nasa_osd575.json` | Contenido y datos NASA | P6 |
| `scripts/` | Indexar guías, convertir OSD-575, construir el modelo en Blender | P5 / P6 |
| `tests/` | Pruebas automáticas | P6 |

**Pendiente de P4:** `GET /api/estado/{id}` (estado real calculado con `reglas.json`). Mientras no exista, el frontend usa datos de demostración y los envía al chat.

## Diseño

**Dirección de arte: pantalla de aviónica de tripulación.** Negro plano, aristas rectas y líneas de 1 px (sin brillos, desenfoques ni degradados), como los displays de cabina. Color con significado, según el sistema de Precaución y Alerta (C&W) de vuelo: verde = normal, ámbar = precaución, rojo = alerta, magenta = seleccionado, cian = rótulos. Datos en JetBrains Mono. Barra de estado con resumen C&W y barras de enlace; softkeys en el borde del visor; tira de instrumentos; asistente como consola.

Se aplicaron las [Web Interface Guidelines de Vercel](https://github.com/vercel-labs/web-interface-guidelines) (accesibilidad, foco visible, `prefers-reduced-motion`, números tabulares, estados de carga, sin `transition: all`) y principios de [taste-skill](https://github.com/leonxlnx/taste-skill) (la interfaz real del producto como protagonista, un solo efecto visual, un sistema de tokens, micro-interacciones discretas). Se usaron como referencia; no se instalaron sus scripts.

## Créditos y licencias

- Anatomía: **BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International**.
- Datos: NASA OSDR **OSD-575** (Inspiration4) y NASA Human Research Program.
- Visor: Three.js (MIT). Servidor: FastAPI (MIT). IA local: Ollama, Gemma 3 4B, nomic-embed-text.
- Código y textos escritos con asistencia de IA (Claude) y revisados por el equipo; declararlo en la entrega.
