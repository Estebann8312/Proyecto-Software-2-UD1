// Rangos de fechas para los informes (Reportes y Sedes).

export type Rango = { desde: string; hasta: string };

/** Fecha local en formato AAAA-MM-DD (sin pasar por UTC). */
export function iso(d: Date) {
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

function ultimosDias(n: number): Rango {
  const hoy = new Date();
  const desde = new Date(hoy);
  desde.setDate(hoy.getDate() - (n - 1));
  return { desde: iso(desde), hasta: iso(hoy) };
}

export const ATAJOS: { id: string; texto: string; rango: () => Rango }[] = [
  { id: "7", texto: "7 días", rango: () => ultimosDias(7) },
  { id: "30", texto: "30 días", rango: () => ultimosDias(30) },
  {
    id: "mes",
    texto: "Este mes",
    rango: () => {
      const hoy = new Date();
      return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: iso(hoy) };
    },
  },
  {
    id: "mes-anterior",
    texto: "Mes anterior",
    rango: () => {
      const hoy = new Date();
      return {
        desde: iso(new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)),
        hasta: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 0)),
      };
    },
  },
  {
    id: "anio",
    texto: "Este año",
    rango: () => {
      const hoy = new Date();
      return { desde: iso(new Date(hoy.getFullYear(), 0, 1)), hasta: iso(hoy) };
    },
  },
];

export function atajo(id: string) {
  return ATAJOS.find((a) => a.id === id)!.rango();
}

/** Arma una celda de CSV (separador ";", para Excel en español). */
export function celdaCsv(valor: string | number | null | undefined) {
  const texto = valor === null || valor === undefined ? "" : String(valor);
  return /[";\n]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
}

/** Descarga filas como CSV con BOM, para que Excel lea bien las tildes. */
export function descargarCsv(nombre: string, filas: (string | number | null | undefined)[][]) {
  const contenido = "﻿" + filas.map((f) => f.map(celdaCsv).join(";")).join("\r\n");
  const url = URL.createObjectURL(new Blob([contenido], { type: "text/csv;charset=utf-8" }));
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  URL.revokeObjectURL(url);
}
