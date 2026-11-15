# Copiloto de salud · prototipo (NASA Space Apps 2026)

Asistente de salud **local** para astronautas, con **ORI**, un compañero de salud con IA: monitoreo con semáforo, cuerpo 3D anatómico y asistente con IA que responde **sin conexión** citando guías de NASA. Prototipo TRL 3–4; no diagnostica.

## Ejecutar

### Registro e historial local

El acceso **Registro e historial · A1** permite guardar ocho indicadores manuales, con fecha,
contexto y notas. La presión conserva sistólica y diastólica por separado. El historial se filtra
por indicador y se pagina de 20 en 20, ordenado por fecha de medición. Ánimo y estrés usan una
escala de demostración de 1 a 5; no son instrumentos clínicos validados.

La API ofrece `POST /api/mediciones` y `GET /api/historial/{astronauta_id}` con parámetros
`indicador`, `limite` (1–100) y `offset`. Las fechas requieren zona horaria y se guardan en UTC;
la interfaz presenta la hora local. El identificador de cada envío permite reintentar sin duplicarlo.

SQLite utiliza la biblioteca estándar de Python, sin instalaciones nuevas. El archivo se crea en
`data/local/mediciones.sqlite3`, excluido de Git. `APELOGIC_DB_PATH` permite otra ubicación.
Los registros permanecen al reiniciar el servidor y el navegador. Para conservarlos al cambiar
de máquina, hay que conservar ese archivo; no se sincronizan automáticamente con otros equipos.

El registro funciona sin internet con FastAPI activo. Los **ocho indicadores** se conectan al panel,
a los órganos correspondientes, a sus gráficas y a ORI. Visión y huesos no tienen registro integrado
y se muestran sin datos. OSD-575 permanece como explorador histórico separado.
La clasificación reutiliza los rangos **ilustrativos** de `data/reglas.json`; no es diagnóstico.
En presión, se evalúan ambos componentes y se muestran dos series. El color de un órgano toma la
alerta conocida más alta; si no hay alerta pero faltan datos actuales de ese sistema, se muestra gris.
Glucosa conserva el valor sin clasificar si el contexto no es ayunas: el rango disponible no está
adaptado a otras condiciones. Ánimo y estrés siguen siendo escalas de demostración, no validadas.
Ausencia, antigüedad superior al límite o valor fuera de plausibilidad dan estado gris. La gráfica
usa hasta 100 registros reales y corta el trazo ante muestras sospechosas, sin puntos generados.
Guardar actualiza el panel; también se refresca cada minuto y al volver a la ventana. Los controles
de simulación conservan una etiqueta explícita y «Reiniciar datos» vuelve a leer el registro local.
El chat relee los ocho indicadores de SQLite antes de responder, salvo en simulación explícita.
No se implementan aquí modificación ni borrado de registros.

Requisitos: Python 3, [uv](https://docs.astral.sh/uv/) (o `pip install -r requirements.txt`) y, para la IA, Ollama con `gemma3:4b` y `nomic-embed-text` (ver `IA_LOCAL.md`).

Desde la raíz del repositorio:

```bash
uv run --with fastapi --with uvicorn uvicorn backend.main:app --port 8000
```

Abrir http://localhost:8000 en Chrome o Chromium (el visor 3D necesita WebGL).

Atajos para la demo: `?organo=corazon` abre un órgano (la cámara lo enfoca) · `#emergencia` simula una emergencia · `#sinsenal` empieza sin conexión · `#hover-corazon` muestra la tarjeta de hover (capturas) · `#preguntar=texto` le hace esa pregunta a ORI al cargar (útil para grabar la demo) · `?quieto` detiene el giro.

En el visor: etiquetas anatómicas con línea guía (clic para abrir), tarjeta al pasar el mouse con valores y tendencia, capas (piel, esqueleto, vasos, órganos), pausa del giro y "Vista completa". Tipografía técnica: JetBrains Mono (OFL), incluida en `frontend/fuentes/`.

El modelo de IA (Gemma 3 4B, ~3,4 GB) no está en el repositorio: cada integrante lo descarga con `ollama pull gemma3:4b` y `ollama pull nomic-embed-text`. El índice de búsqueda de las guías (`data/indice_guias.json`) sí está incluido.

## Clima espacial (NASA DONKI)

`data/nasa_donki.json` guarda los eventos solares reales de los últimos 30 días (llamaradas, partículas solares y tormentas geomagnéticas) de NASA DONKI. Es la "sincronización con la Tierra": se actualiza con `python scripts/actualizar_donki.py` cuando hay señal, y sin señal la app usa el último archivo y avisa su antigüedad. El nivel de radiación (verde, precaución o alerta) se calcula en `backend/clima_espacial.py` con reglas ilustrativas. Desde el 30/09/2026 el servicio está en `https://ccmc.gsfc.nasa.gov/DONKI-API/get/` (sin clave).

## Pruebas

### Medir, comprender y actuar

La ficha de cada indicador abre una orientación con la medición actual, equipo o entrada,
instrucciones, motivo de calidad del dato, siguiente paso y cuándo avisar. También se abre
desde **Cómo tomar esta medida** en el registro y desde **Ver orientación del indicador**
después de guardar. El botón **Registrar medición** vuelve al formulario con el indicador elegido.

**Orientación urgente** abre inmediatamente un aviso para contactar con la tripulación y seguir
el protocolo de a bordo sin esperar a ORI. En esa vista no se usa una lectura en rango para
tranquilizar ni se pide completar mediciones antes de pedir ayuda. No implementa reanimación,
medicamentos ni dosis; muestra las señales y avisos del borrador local.

La biblioteca usa `GET /api/orientacion`, sin invocar Ollama. Expone los Markdown locales con
archivo, fuente de contexto, versión y estado de revisión. Son **adaptaciones ilustrativas del
equipo**, pendientes de revisión clínica; enlazar NASA no las convierte en protocolos oficiales.
Sueño y pulso incluyen instrucciones de registro adaptadas al prototipo. No se cambiaron las
guías usadas por RAG ni su índice. Los textos funcionan sin internet con FastAPI activo. Si la
biblioteca no carga, el aviso urgente permanece y se ofrece reintentar; la fuente externa sí requiere internet.

### Explorador de datos reales de Inspiration4

El botón **Explorar datos reales** abre una vista independiente del estado de salud de la app.
Permite seleccionar C001–C004 y glucosa, calcio, sodio, potasio o creatinina; comparar muestras
antes/después; consultar todos los valores y exportar la serie elegida a CSV.
La gráfica usa días proporcionales (R+ se cuenta desde el regreso, al día 3), corta el trazo
ante faltantes y presenta el rango del laboratorio como referencia, sin clasificar al usuario.
No se imputan valores, se atribuyen anomalías a errores de muestra ni se infiere causalidad del vuelo.

Usa el contrato existente `GET /api/nasa/osd575` y el dataset incluido, sin cambiar endpoints,
dependencias Python, modelos de Ollama ni datos enviados al chat. Si falla la carga, muestra
un aviso al abrir el explorador. Funciona sin internet con el servidor local activo; el enlace
al estudio NASA requiere conexión. Los datos históricos nunca reemplazan el estado del panel.

Validación adicional (Node.js para pruebas, no necesario para ejecutar la app):

```bash
node --test tests/nasa-datos.test.mjs
```

La suite Python también verifica las 20 series frente al CSV original incluido.

```bash
uv run --with pytest --with fastapi --with httpx python -m pytest -q tests
```

129 pruebas Python: registro local, conexión de ocho indicadores y calidad de los datos, biblioteca de orientación sin IA, guías, reglas del semáforo, fichas, datos NASA y procedencia del CSV, modelo 3D, asistente y API. Las dos pruebas con el modelo se saltan si Ollama está apagado. Las pruebas JavaScript se ejecutan con `node --test tests/*.test.mjs`.

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

`GET /api/estado/{id}` combina los ocho indicadores guardados, dos sistemas sin registro integrado y el clima espacial. Cada indicador incluye calidad, origen, fecha, motivo e historial de hasta 100 muestras. Los controles de demostración son explícitos y no modifican los registros guardados.

## Diseño

**Dirección de arte: pantalla de aviónica de tripulación.** Negro plano, aristas rectas y líneas de 1 px (sin brillos, desenfoques ni degradados), como los displays de cabina. Color con significado, según el sistema de Precaución y Alerta (C&W) de vuelo: verde = normal, ámbar = precaución, rojo = alerta, magenta = seleccionado, cian = rótulos. Datos en JetBrains Mono. Barra de estado con resumen C&W y barras de enlace; softkeys en el borde del visor; tira de instrumentos; asistente como consola.

Se aplicaron las [Web Interface Guidelines de Vercel](https://github.com/vercel-labs/web-interface-guidelines) (accesibilidad, foco visible, `prefers-reduced-motion`, números tabulares, estados de carga, sin `transition: all`) y principios de [taste-skill](https://github.com/leonxlnx/taste-skill) (la interfaz real del producto como protagonista, un solo efecto visual, un sistema de tokens, micro-interacciones discretas). Se usaron como referencia; no se instalaron sus scripts.

## Créditos y licencias

- Anatomía: **BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International**.
- Datos: NASA OSDR **OSD-575** (Inspiration4), **NASA DONKI** (clima espacial, CCMC / NASA GSFC) y NASA Human Research Program.
- Visor: Three.js (MIT). Servidor: FastAPI (MIT). IA local: Ollama, Gemma 3 4B, nomic-embed-text.
- Código y textos escritos con asistencia de IA (Claude) y revisados por el equipo; declararlo en la entrega.
