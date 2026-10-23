import type { Condicion, MetodoPago } from "./api";

const numero = new Intl.NumberFormat("es-CO", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** "155.00" → "$ 155,00" */
export function precio(valor: string | number) {
  return `$ ${numero.format(Number(valor))}`;
}

const fechaCorta = new Intl.DateTimeFormat("es-CO", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const fechaHora = new Intl.DateTimeFormat("es-CO", {
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
});

/** Fechas tipo "2026-10-05" se leen como día local, no como UTC. */
function aFecha(valor: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(valor) ? new Date(`${valor}T00:00:00`) : new Date(valor);
}

export function fecha(valor: string) {
  return fechaCorta.format(aFecha(valor));
}

export function fechaConHora(valor: string) {
  return fechaHora.format(aFecha(valor));
}

export function marcaDeTiempo(valor: string) {
  return aFecha(valor).getTime();
}

export const NOMBRE_PAGO: Record<MetodoPago, string> = {
  efectivo: "Efectivo",
  tarjeta_debito: "Tarjeta débito",
  tarjeta_credito: "Tarjeta crédito",
  transferencia: "Transferencia",
};

export const NOMBRE_CONDICION: Record<Condicion, string> = {
  nueva: "Nueva",
  reacondicionada: "Reacondicionada",
};

/** Por debajo de este número de unidades, una pieza se marca con stock bajo. */
export const STOCK_BAJO = 3;

export function estadoStock(stock: number) {
  if (stock <= 0) return { texto: "Agotada", clase: "peligro" } as const;
  if (stock <= STOCK_BAJO) return { texto: "Stock bajo", clase: "alerta" } as const;
  return { texto: "Disponible", clase: "ok" } as const;
}

/** Quita tildes y mayúsculas para buscar "grafica" y encontrar "Gráfica". */
export function normalizar(texto: string) {
  return texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}
