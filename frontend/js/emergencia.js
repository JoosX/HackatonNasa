// Recorrido local: no consulta sensores, registros, servidor ni modelo de IA.
export const FUENTE_BLS = 'https://www.resus.org.uk/professional-library/2025-resuscitation-guidelines/adult-basic-life-support-guidelines';
export const FUENTE_ESPACIO = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC7607644/';
export const NODOS = {
  inicio: {titulo:'¿La persona responde al hablarle?', texto:'Comprueba que sea seguro acercarte. Háblale y observa si responde.', opciones:[['Sí, responde','sintomas'],['No responde','respiracion'],['No estoy seguro','respiracion']]},
  respiracion: {titulo:'¿Respira normalmente?', texto:'Comprueba la respiración según tu entrenamiento. Los jadeos aislados o una respiración agónica no son respiración normal. Pide ayuda a otro tripulante mientras lo compruebas.', opciones:[['Sí, respira normalmente','inconsciente'],['No respira o solo jadea','reanimacion'],['No puedo confirmarlo','reanimacion']]},
  sintomas: {titulo:'¿Hay dolor de pecho, falta de aire, confusión o un desmayo reciente?', texto:'Los síntomas tienen prioridad aunque los indicadores aparezcan verdes. No hace falta completar mediciones para pedir ayuda.', opciones:[['Sí, hay alguna de estas señales','alerta'],['No estoy seguro','alerta'],['No, ninguna de estas señales','sin_senales']]},
  reanimacion: {titulo:'Posible paro: actúa de inmediato', texto:'La falta de respuesta y de respiración normal requiere actuar sin esperar confirmación de la IA.', pasos:['Activa la respuesta de emergencia de la tripulación y pide el desfibrilador externo automático (DEA), si está disponible.','Inicia reanimación cardiopulmonar (RCP) según tu entrenamiento y el procedimiento de la misión. No demores la ayuda para medir pulso, presión o glucosa.','Enciende el DEA y sigue sus instrucciones en cuanto esté disponible.'], espacio:true},
  inconsciente: {titulo:'No responde, aunque respira: necesita ayuda urgente', texto:'Activa la respuesta de emergencia y sigue el procedimiento de la misión para mantener la vía aérea y vigilar la respiración. No la dejes sola.', pasos:['Pide ayuda a la persona con mayor formación médica de la tripulación.','Si la respiración deja de ser normal, vuelve a «Respiración» para seguir la ruta de reanimación.','No des comida, bebida ni medicamentos a una persona que no responde.'], opciones:[['La respiración cambió o tengo dudas','respiracion']]},
  alerta: {titulo:'Pide ayuda ahora; no esperes a la Tierra', texto:'Avisa de inmediato a la tripulación y activa el protocolo de emergencia de la misión. Un valor en rango no descarta una emergencia.', pasos:['Permanece con la persona y pide apoyo al tripulante con mayor formación médica.','Observa si responde y cómo respira. Si deja de responder, cambia a la ruta «No responde».','No retrases la ayuda para completar el historial o conversar con ORI.'], opciones:[['La persona dejó de responder','respiracion']]},
  sin_senales: {titulo:'Continúa observando; esto no descarta una enfermedad', texto:'Si el malestar persiste, empeora o te preocupa, avisa a la tripulación. Puedes consultar cómo medir el indicador correspondiente. Si aparece alguna señal urgente, reinicia este recorrido.', pasos:[]},
};

export function avanzarEmergencia(actual,destino) {
  return NODOS[actual]?.opciones?.some(([,id])=>id===destino)?destino:actual;
}

export function renderEmergencia(id='inicio',historial=[]) {
  const n=NODOS[id]??NODOS.inicio;
  return `<section class="emergencia-recorrido" aria-label="Recorrido de emergencia">
    <p class="rotulo">Decisión ${historial.length+1} · Sin esperar al chat</p>
    <h3 id="emergenciaPregunta" tabindex="-1">${n.titulo}</h3><p>${n.texto}</p>
    ${n.pasos?.length?`<ol>${n.pasos.map(p=>`<li>${p}</li>`).join('')}</ol>`:''}
    ${n.espacio?'<p class="orientacion-revision">En microgravedad hacen falta sujeción y técnicas entrenadas para la misión. Esta pantalla no enseña esas maniobras ni valida su ejecución; usa el procedimiento y equipo de a bordo.</p>':''}
    <div class="emergencia-opciones">${(n.opciones??[]).map(([texto,destino])=>`<button type="button" class="btn" data-emergencia="${destino}">${texto}</button>`).join('')}</div>
    <div class="emergencia-navegacion">${historial.length?'<button type="button" class="btn" data-emergencia-atras>Volver a la pregunta anterior</button>':''}${id!=='inicio'?'<button type="button" class="btn" data-emergencia-reiniciar>Reiniciar recorrido</button>':''}</div>
    <details><summary>Fuentes y alcance de este recorrido</summary><p>Referencia de reconocimiento y RCP: <a href="${FUENTE_BLS}" target="_blank" rel="noopener noreferrer">Resuscitation Council UK, soporte vital básico adulto 2025</a>. Referencia terrestre para adultos; no es un protocolo aprobado para esta misión.</p><p>Contexto de sujeción y entrenamiento: <a href="${FUENTE_ESPACIO}" target="_blank" rel="noopener noreferrer">DGLRM / ESAM-SMG, RCP en microgravedad (2020)</a>. Adaptación del equipo pendiente de revisión médica. No indica medicamentos ni dosis.</p><p>Las respuestas se borran al cerrar o reiniciar; no se guardan como diagnóstico.</p></details>
  </section>`;
}
