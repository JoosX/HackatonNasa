// Validación de los contratos propuestos. No transforma datos médicos.
function registro(value){return value!==null&&typeof value==='object'&&!Array.isArray(value);}
export function validarFuentes(fuentes){
 if(!Array.isArray(fuentes))throw new Error('Se esperaba una lista de fuentes.');
 return fuentes.map(f=>{if(!registro(f)||typeof f.titulo!=='string')throw new Error('Cada fuente necesita un titulo.');
 return {titulo:f.titulo,url:typeof f.url==='string'?f.url:null};});
}
export function validarFichas(data){
 if(!registro(data)||!Array.isArray(data.fichas))throw new Error('Se esperaba el campo fichas como lista.');
 const ids=new Set();
 return data.fichas.map(f=>{
  if(!registro(f)||typeof f.id!=='string'||ids.has(f.id)||!Array.isArray(f.preguntas))throw new Error('Ficha inválida o identificador duplicado.');
  ids.add(f.id);
  const preguntas=f.preguntas.map(p=>{if(!registro(p)||typeof p.pregunta!=='string'||typeof p.respuesta!=='string')throw new Error('Pregunta de ficha incompleta.');return {...p};});
  return {...f,preguntas,fuentes:validarFuentes(f.fuentes??[])};
 });
}
export function validarRespuesta(data){
 if(!registro(data)||typeof data.respuesta!=='string'||!data.respuesta.trim())throw new Error('El asistente devolvió una respuesta vacía o inválida.');
 return {respuesta:data.respuesta,fuentes:validarFuentes(data.fuentes)};
}

