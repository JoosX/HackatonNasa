// Transformaciones de lectura del contrato existente GET /api/nasa/osd575.
// Los datos históricos nunca se convierten en estado clínico del usuario.
export const ANALITOS = {
  glucosa: { nombre: "Glucosa", descripcion: "Azúcar medido en el suero; forma parte del panel metabólico de esta misión." },
  calcio: { nombre: "Calcio", descripcion: "Calcio medido en el suero. Este análisis no mide por sí solo la densidad de los huesos." },
  sodio: { nombre: "Sodio", descripcion: "Uno de los electrolitos medidos en las muestras de suero del estudio." },
  potasio: { nombre: "Potasio", descripcion: "Otro de los electrolitos incluidos en el panel metabólico publicado." },
  creatinina: { nombre: "Creatinina", descripcion: "Sustancia medida en el panel metabólico. Un resultado aislado no establece un diagnóstico." },
};

export const esNumero = v => typeof v === "number" && Number.isFinite(v);

// R se cuenta desde el regreso, tres días después del lanzamiento de Inspiration4.
export function diaDesdeLanzamiento(momento) {
  const m = /^(L-|R\+)(\d+)$/.exec(momento);
  return m ? (m[1] === "L-" ? -Number(m[2]) : 3 + Number(m[2])) : null;
}

export function puntosSerie(datos, tripulante, analito) {
  const serie = datos?.tripulantes?.[tripulante]?.[analito];
  return (datos?.momentos ?? []).map(momento => ({
    momento,
    dia: diaDesdeLanzamiento(momento),
    valor: esNumero(serie?.valores?.[momento]) ? serie.valores[momento] : null,
    fase: momento.startsWith("L-") ? "Antes del vuelo" : "Después del regreso",
  }));
}

export function comparar(serie, antes, despues) {
  const a = serie?.valores?.[antes], b = serie?.valores?.[despues];
  if (!esNumero(a) || !esNumero(b)) return null;
  return { antes: a, despues: b, diferencia: b - a, porcentaje: a === 0 ? null : ((b - a) / Math.abs(a)) * 100 };
}

export function csvSerie(datos, tripulante, analito) {
  const celda = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const filas = [["estudio", "tripulante", "analito", "momento", "fase", "valor", "unidad"],
    ...puntosSerie(datos, tripulante, analito).map(p => ["OSD-575", tripulante, analito, p.momento, p.fase, p.valor,
      datos.tripulantes[tripulante][analito].unidad])];
  return filas.map(f => f.map(celda).join(",")).join("\r\n");
}
