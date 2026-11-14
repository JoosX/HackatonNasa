export const colores={verde:'#55d8af',amarillo:'#f2c76b',rojo:'#fa7c89',sin_datos:'#8d9caf'};
export const etiquetas={verde:'Estable',amarillo:'Atención',rojo:'Alerta',sin_datos:'Sin datos'};
// Solo representa el resultado del backend; no aplica reglas médicas.
export function normalizarEstado(data){
 if(!data?.organos||typeof data.organos!=='object'||Array.isArray(data.organos))throw new Error('La API no devolvió el campo organos esperado.');
 return Object.fromEntries(Object.entries(data.organos).map(([id,v])=>[id,{color:Object.hasOwn(colores,v?.color)?v.color:'sin_datos',pulso:typeof v?.pulso==='number'&&Number.isFinite(v.pulso)&&v.pulso>0?v.pulso:null}]));
}

