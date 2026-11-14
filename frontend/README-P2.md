# Panel P2 — ApeLogic MED

Primera versión local y autónoma del panel. No hay backend conectado ni datos OSD-575 importados. No emite evaluación médica. Los valores y avisos iniciales son simulados y están identificados en pantalla.

## Ejecutar

Desde `frontend/`: `python -m http.server 8765 --bind 127.0.0.1`. Abrir `http://127.0.0.1:8765`.

Sin dependencias, fuentes remotas ni CDN. El historial se conserva en localStorage del mismo navegador/origen; no es una base de datos compartida ni almacenamiento clínico seguro. La exportación CSV incluye origen y fecha UTC.

## Funciones

- Panel de seis indicadores, selección de tendencia, últimos siete registros.
- Formulario con unidades, fecha y contexto; validación básica del formato. No aplica umbrales médicos.
- Historial filtrable, exportación CSV, identificación de datos manuales y simulados.
- Diseño adaptable a móvil y navegación con teclado.

## Integración pendiente con P4

Reemplazar el almacenamiento local por POST /api/mediciones y lecturas GET /api/estado/{id}, GET /api/historial/{id}, GET /api/alertas/{id}. Acordar antes id de astronauta, zona horaria, nombres de indicadores y esquema de errores. Registros actuales: `{indicador, valor, fecha, origen, nota}`. El frontend no asigna prioridades clínicas.

La presión arterial requiere dos valores/unidades acordados con P4; estrés, recordatorios y datos NASA quedan para la siguiente integración. P3 integra cuerpo y chat; no están implementados aquí.

Las gráficas usan SVG nativo para funcionar sin descargas. Si el equipo mantiene Chart.js como contrato del PDF, puede sustituirse la función renderChart sin alterar los registros.

## Uso de IA

Interfaz y código inicial generados con asistencia de Codex. Revisión del equipo pendiente. No se creó ni entrenó un modelo médico.

## Actualización de experiencia P2

- Cabecera de misión y latencia de ida de 14 minutos identificadas como simulación; no representan telemetría real.
- Observación principal de sueño calculada desde el historial disponible, sin clasificación clínica.
- Selección de un punto/fecha con procedencia, contexto y diferencia respecto al registro anterior. El primer registro muestra que no existe comparación.
- Referencia corporal educativa sincronizada con el indicador. El botón de enlace emite en window el evento `apelogic:indicator-selected` con `{indicador, organo}`. P3 debe conectar su visor a este evento; el panel no incluye su implementación.
- Se verificaron selección de sueño, comparación -0,5 h entre los dos últimos registros de demo, primer registro sin comparación y emisión del enlace P3. No se observaron errores en la consola durante esta revisión. La adaptación móvil está en CSS; no se hizo verificación visual móvil en esta iteración.
