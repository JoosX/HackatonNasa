[English](validacion-orientacion.md) | **Español**

# Orientación: alcance y validación pendiente

Versión 2026-11-14. Adaptación educativa de ApeLogic, para adultos. **Sin aprobación clínica ni certificación NASA.** No se ejecutó una prueba de integración en la laptop de David en esta mejora.

## Qué cambió

El recorrido de emergencia funciona con JavaScript incluido en la página, sin esperar a API, registros, Ollama o internet una vez cargada. Pregunta respuesta y respiración, contempla incertidumbre y prioriza ayuda ante síntomas aunque el panel esté verde. Permite volver, reiniciar y cerrar sin guardar respuestas. No enseña las técnicas específicas de RCP en microgravedad.

Las ocho guías incluyen preparación, equipo, pasos, errores y ausencia de equipo. Las cinco mediciones instrumentales tienen referencias específicas de medición, distintas de las fuentes NASA de contexto. Sueño es diario del equipo; ánimo y estrés son escalas propias no validadas.

Las reglas conservan sus colores de demostración por compatibilidad. Cada una declara aprobación clínica falsa, responsable, limitación y vigencia de software; la guía permite consultar los cortes concretos. Se retiraron esperas de 15/30 minutos en acciones sin fundamento y cortes de noches del consejo de sueño. Esto es una auditoría documental del prototipo, **no una validación de los cortes**. Para uso real, medicina de vuelo debe aprobar o reemplazar cada regla, dispositivo, contexto y procedimiento.

ORI deriva expresiones explícitas urgentes a una respuesta fija antes de buscar o generar con IA. Esta detección conservadora puede activar ejemplos y negaciones, no reconoce todas las formas de describir un síntoma y no debe usarse para descartar urgencia. El botón de orientación está siempre disponible. Si el índice de embeddings no coincide con las guías actuales, ORI usa el texto actualizado con búsqueda por palabras; David puede regenerar el índice con su proceso habitual.

## Fuentes y propósito

| Fuente | Se usa para | No demuestra |
|---|---|---|
| [RCUK BLS 2025](https://www.resus.org.uk/professional-library/2025-resuscitation-guidelines/adult-basic-life-support-guidelines) | Reconocimiento de falta de respuesta, respiración anormal, ayuda, RCP y DEA | Aprobación del recorrido espacial |
| [DGLRM / ESAM-SMG 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7607644/) | Necesidad de técnicas y sujeción específicas de microgravedad | Que el usuario sepa realizarlas o que la app las valide |
| [MedlinePlus Pulse](https://medlineplus.gov/ency/article/003399.htm) | Reposo y conteo manual en muñeca | Cortes del semáforo para astronautas |
| [CDC Blood Pressure](https://www.cdc.gov/high-blood-pressure/measure/index.html) | Preparación y técnica terrestre de presión | Posición aprobada para una misión en microgravedad |
| [FDA Pulse Oximeter](https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics) | Lectura y limitaciones del oxímetro | CO₂, aire de nave o diagnóstico por un porcentaje |
| [FDA Glucose Devices](https://www.fda.gov/medical-devices/in-vitro-diagnostics/blood-glucose-monitoring-devices) | Uso, higiene y limitaciones del glucómetro | Equivalencia de alarmas capilares con el laboratorio de OSD-575 |
| [MedlinePlus Temperature](https://medlineplus.gov/ency/article/003400.htm) | Preparación y método de termómetro | Un mismo corte diagnóstico para todos los métodos |
| [NASA HRP](https://www.nasa.gov/hrp/risks/) / [OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575) | Riesgos espaciales y muestras históricas | Validación clínica de las reglas del equipo |

## Prueba breve con personas ajenas al equipo (pendiente)

Comprobación técnica realizada en navegador local: ruta de colapso con jadeos, ruta consciente con síntomas, acceso desde registro a guía de presión, tabla de límites, derivación de ORI y reapertura con respuestas reiniciadas. Se comprobó activación con Enter, cierre con Escape y foco en la nueva pregunta. En 390 × 844 los botones de decisión tienen 52 px de alto y el diálogo no presenta desborde horizontal; se acortó el aviso para que las tres respuestas iniciales sean visibles. Se restauró el tamaño original del navegador. Estas comprobaciones no son una auditoría completa de accesibilidad ni una prueba con usuarios.

No presentar una comprobación técnica como prueba con usuarios. Pidan a tres personas sin formación médica que completen estos escenarios con datos de demostración, sin explicarles dónde hacer clic. No simular maniobras sobre personas.

1. «Tu compañero se desploma y solo jadea. ¿Dónde buscas ayuda y qué harías primero?» Debe abrir orientación, llegar a la ruta de reanimación y priorizar ayuda sin esperar mediciones o chat.
2. «Tienes dolor de pecho, pero el pulso aparece verde.» Debe pedir ayuda; el verde no debe tranquilizarlo.
3. «Quieres registrar presión. No sabes qué preparar.» Debe encontrar equipo, preparación, pasos, unidad y ambos valores.
4. «No tienes oxímetro.» Debe comunicar síntomas y dejar el dato ausente; nunca inventar un porcentaje.
5. «¿Estos colores los aprobó NASA?» Debe encontrar la explicación y responder que no.

Registrar por persona: escenario, tiempo hasta primera acción, tarea completada sin ayuda, error observado y comentario literal. Meta interna de usabilidad (no clínica): localizar ayuda en 10 segundos y cero interpretaciones de «verde = emergencia descartada». Si alguien se equivoca, ajustar y repetir con otra persona. No afirmar que la meta se cumplió hasta tener resultados.

| Persona anónima | Escenario | Segundos | Sin ayuda | Error / comentario |
|---|---|---|---|---|
| Pendiente | — | — | — | No se realizó todavía |

## Revisión profesional (pendiente)

Revisor de medicina de vuelo / urgencias por asignar. Solicitar revisión del texto completo, rutas de incertidumbre, RCP/DEA según entorno y equipamiento, criterios de aviso, intervalos de plausibilidad, antigüedad de datos y cada corte de color. Registrar nombre, credencial, fecha, versión, observaciones y aprobación explícita antes de cambiar el estado a aprobado. No sustituir esta revisión con fuentes bibliográficas ni con aprobación del equipo.

## Integración en la versión DavidMAC (2026-11-15)

Partes de la rama `romario/orientacion-fundamentada` integradas sobre la versión con base de datos de a bordo y protocolos de ORI:

- **Recorrido de emergencia** (árbol de decisión ¿responde? / ¿respira?): botón «Orientación urgente» en la barra superior y botón «Abrir recorrido paso a paso» en cada respuesta de emergencia de ORI. Funciona sin servidor, sin IA y sin enlace.
- **Guía «Medir, comprender y actuar»** por indicador (`data/medicion_guiada.json`, `/api/orientacion`), accesible desde «¿Cómo tomo esta medida?» en el registro.
- **Contexto de la medición** (reposo, ejercicio, ayunas, después de comer): se guarda en la base de datos; la glucosa medida fuera de ayunas no se clasifica.
- **Calidad del dato** (vigente, sospechoso, vencido, contexto pendiente) calculada por el motor de reglas.
- **Validación declarada** en `data/reglas.json` y retirada de esperas de 15/30 minutos sin fundamento, también en los protocolos de ORI.
- **Robustez**: si el índice de la IA no coincide con las guías actuales se usan las guías actuales; el chat usa el estado de la base de datos, no el enviado por el navegador.

No se integraron `mediciones.py` ni `evolucion.py`: duplican el registro (`db.py`) y el motor de reglas (`motor.py`) de esta versión. Diferencia de criterio pendiente: ORI responde a las urgencias con un protocolo paso a paso en el chat (empático, con a quién llamar), además de derivar al recorrido. Debe revisarlo medicina de vuelo igual que el resto.
