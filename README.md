# Copiloto de salud · prototipo (NASA Space Apps 2026)

Asistente de salud **local** para astronautas, con **ORI**, un compañero de salud con IA: monitoreo con semáforo, cuerpo 3D anatómico y asistente con IA que responde **sin conexión** citando guías de NASA. Prototipo TRL 3–4; no diagnostica.

## Ejecutar

Requisitos: Python 3, [uv](https://docs.astral.sh/uv/) (o `pip install -r requirements.txt`) y, para la IA, Ollama con `gemma3:4b` y `nomic-embed-text` (ver `IA_LOCAL.md`).

Desde la raíz del repositorio:

```bash
uv run --with fastapi --with uvicorn uvicorn backend.main:app --port 8000
```

Abrir http://localhost:8000 en Chrome o Chromium (el visor 3D necesita WebGL).

Atajos para la demo: `?organo=corazon` abre un órgano (la cámara lo enfoca) · `#emergencia` simula una emergencia · `#sinsenal` empieza sin conexión · `#hover-corazon` muestra la tarjeta de hover (capturas) · `#preguntar=texto` le hace esa pregunta a ORI al cargar (útil para grabar la demo) · `?quieto` detiene el giro.

En el visor: etiquetas anatómicas con línea guía (clic para abrir), tarjeta al pasar el mouse con valores y tendencia, capas (piel, esqueleto, vasos, órganos), pausa del giro y "Vista completa". Tipografía técnica: JetBrains Mono (OFL), incluida en `frontend/fuentes/`.

El modelo de IA (Gemma 3 4B, ~3,4 GB) no está en el repositorio: cada integrante lo descarga con `ollama pull gemma3:4b` y `ollama pull nomic-embed-text`. El índice de búsqueda de las guías (`data/indice_guias.json`) sí está incluido.

## Base de datos de a bordo (SQLite)

Las mediciones se guardan en `data/mision.db` (un solo archivo, sin servidor, funciona sin internet). Al primer arranque se siembra un historial de demostración de 7 días; luego se suman las mediciones nuevas. `backend/motor.py` calcula con `data/reglas.json` el color, la tendencia, **tu normal** (promedio de tus primeras mediciones) y detecta datos sospechosos o vencidos.

- Registrar: botón **+ Registrar medición** (o `POST /api/mediciones`). ORI comenta cada medición.
- Sensor simulado: `python scripts/sensor_simulado.py` (o `--subida` para que el pulso llegue a alerta en la demo). La app se actualiza sola cada 15 s.
- Reiniciar la demo: "Controles de demostración → Reiniciar datos" (o `POST /api/demo/reiniciar`).
- ORI recuerda los últimos turnos de la conversación: entiende "¿y por qué pasa eso?".

## Clima espacial (NASA DONKI)

`data/nasa_donki.json` guarda los eventos solares reales de los últimos 30 días (llamaradas, partículas solares y tormentas geomagnéticas) de NASA DONKI. Es la "sincronización con la Tierra": se actualiza con `python scripts/actualizar_donki.py` cuando hay señal, y sin señal la app usa el último archivo y avisa su antigüedad. El nivel de radiación (verde, precaución o alerta) se calcula en `backend/clima_espacial.py` con reglas ilustrativas. Desde el 30/09/2026 el servicio está en `https://ccmc.gsfc.nasa.gov/DONKI-API/get/` (sin clave).

## Idiomas / Languages

La app funciona en **español e inglés** (botón **ES | EN** arriba a la derecha). Para abrirla directamente en inglés: `http://localhost:8000/?lang=en`. Se recuerda la elección; sin elección, usa el idioma del navegador.

- Interfaz: `frontend/js/i18n.js` (`L("español", "English")`).
- Servidor: `backend/idioma.py` lee la cookie `idioma` (o `?lang=`) en cada petición; ORI, reglas, fichas y protocolos responden en ese idioma.
- Contenido en inglés: `data/guias_en/` (11 guías, misma estructura), `data/en/` (fichas, reglas, guías de medición) y el índice `data/indice_guias_en.json` (`python scripts/indexar_guias.py` genera los dos).

The app works in **Spanish and English** (**ES | EN** button, top right). Open it in English with `?lang=en`.

## Emergencias y orientación

- **ORI en una emergencia** (`backend/emergencia.py`): ante "me duele el pecho", "mi compañero se desmayó" o un indicador en alerta con "¿qué hago?", responde al instante y sin IA: qué puede estar pasando, qué se siente, a quién llamar y qué decirle, pasos con su porqué y qué hacer sin enlace con la Tierra. El chat se amplía solo.
- **Orientación urgente** (botón rojo arriba, de Romario): recorrido paso a paso ¿responde? / ¿respira? hasta RCP y desfibrilador. Funciona aunque fallen el servidor, la IA o el enlace.
- **Medir, comprender y actuar** (de Romario): por indicador, equipo, preparación, pasos, errores frecuentes y qué hacer sin equipo, con fuentes (MedlinePlus, CDC, FDA). Se abre con «¿Cómo tomo esta medida?» al registrar.
- Alcance y validación pendiente: [`docs/validacion-orientacion.md`](docs/validacion-orientacion.md). Nada de esto tiene aprobación clínica.

## Pruebas

```bash
uv run --with pytest --with fastapi --with httpx python -m pytest -q tests
node --test tests/*.mjs
```

126 pruebas en Python (guías, semáforo, fichas, datos NASA, modelo 3D, base de datos, contexto y calidad del dato, protocolos de emergencia, orientación, asistente con y sin IA, API) y 11 en JavaScript (recorrido de emergencia y orientación).

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
| `backend/emergencia.py` | Protocolos de emergencia de ORI | P5 |
| `backend/orientacion.py`, `data/medicion_guiada.json`, `frontend/js/orientacion*.js`, `emergencia.js`, `docs/validacion-orientacion.md` | Orientación urgente y guías de medición | Romario |
| `tests/` | Pruebas automáticas | P6 |

El estado del astronauta (`GET /api/estado/{id}`) se calcula con la base de datos y `reglas.json`; el chat siempre usa ese estado.

## Diseño

**Dirección de arte: pantalla de aviónica de tripulación.** Negro plano, aristas rectas y líneas de 1 px (sin brillos, desenfoques ni degradados), como los displays de cabina. Color con significado, según el sistema de Precaución y Alerta (C&W) de vuelo: verde = normal, ámbar = precaución, rojo = alerta, magenta = seleccionado, cian = rótulos. Datos en JetBrains Mono. Barra de estado con resumen C&W y barras de enlace; softkeys en el borde del visor; tira de instrumentos; asistente como consola.

Se aplicaron las [Web Interface Guidelines de Vercel](https://github.com/vercel-labs/web-interface-guidelines) (accesibilidad, foco visible, `prefers-reduced-motion`, números tabulares, estados de carga, sin `transition: all`) y principios de [taste-skill](https://github.com/leonxlnx/taste-skill) (la interfaz real del producto como protagonista, un solo efecto visual, un sistema de tokens, micro-interacciones discretas). Se usaron como referencia; no se instalaron sus scripts.

## Créditos y licencias

- Anatomía: **BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International**.
- Datos: NASA OSDR **OSD-575** (Inspiration4), **NASA DONKI** (clima espacial, CCMC / NASA GSFC) y NASA Human Research Program.
- Visor: Three.js (MIT). Servidor: FastAPI (MIT). IA local: Ollama, Gemma 3 4B, nomic-embed-text.
- Código y textos escritos con asistencia de IA (Claude) y revisados por el equipo; declararlo en la entrega.
