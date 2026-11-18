"use client";

import { useState } from "react";

const TAMANOS = [10, 25, 50];

export type Paginacion<T> = {
  visibles: T[];
  pagina: number;
  totalPaginas: number;
  cantidad: number;
  porPagina: number;
  irA: (pagina: number) => void;
  cambiarTamano: (porPagina: number) => void;
};

/**
 * Pagina una lista que ya está en memoria.
 * `clave` resume los filtros: cuando cambia, se vuelve a la primera página.
 */
export function usePaginacion<T>(items: T[], porPaginaInicial = 10, clave = ""): Paginacion<T> {
  const [estado, setEstado] = useState({ clave, pagina: 1, porPagina: porPaginaInicial });
  const porPagina = estado.porPagina;
  const totalPaginas = Math.max(1, Math.ceil(items.length / porPagina));
  const pagina = estado.clave === clave ? Math.min(estado.pagina, totalPaginas) : 1;

  return {
    visibles: items.slice((pagina - 1) * porPagina, pagina * porPagina),
    pagina,
    totalPaginas,
    cantidad: items.length,
    porPagina,
    irA: (p) => setEstado({ clave, porPagina, pagina: Math.max(1, Math.min(p, totalPaginas)) }),
    cambiarTamano: (n) => setEstado({ clave, porPagina: n, pagina: 1 }),
  };
}

/** Números de página a mostrar: 1 … 4 5 6 … 12 */
function numeros(pagina: number, total: number): (number | "…")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const cerca = [pagina - 1, pagina, pagina + 1].filter((n) => n > 1 && n < total);
  const lista: (number | "…")[] = [1];
  if (cerca[0] > 2) lista.push("…");
  lista.push(...cerca);
  if (cerca[cerca.length - 1] < total - 1) lista.push("…");
  lista.push(total);
  return lista;
}

export function Paginador<T>({
  p,
  nombre = "registros",
  tamanos = TAMANOS,
}: {
  p: Paginacion<T>;
  nombre?: string;
  tamanos?: number[];
}) {
  if (p.cantidad <= Math.min(...tamanos, p.porPagina)) return null;
  const desde = (p.pagina - 1) * p.porPagina + 1;
  const hasta = Math.min(p.pagina * p.porPagina, p.cantidad);

  return (
    <nav className="paginador" aria-label={`Páginas de ${nombre}`}>
      <span className="secundario pequeno cifras">
        {desde}–{hasta} de {p.cantidad} {nombre}
      </span>

      <div className="paginas">
        <button type="button" onClick={() => p.irA(p.pagina - 1)} disabled={p.pagina === 1} aria-label="Página anterior">
          ‹
        </button>
        {numeros(p.pagina, p.totalPaginas).map((n, i) =>
          n === "…" ? (
            <span key={`e${i}`} className="elipsis" aria-hidden="true">…</span>
          ) : (
            <button key={n} type="button" onClick={() => p.irA(n)}
              aria-current={n === p.pagina ? "page" : undefined} aria-label={`Página ${n}`}>
              {n}
            </button>
          )
        )}
        <button type="button" onClick={() => p.irA(p.pagina + 1)} disabled={p.pagina === p.totalPaginas}
          aria-label="Página siguiente">
          ›
        </button>
      </div>

      <label className="secundario pequeno tamano">
        Ver
        <select className="control" value={p.porPagina} onChange={(e) => p.cambiarTamano(Number(e.target.value))}>
          {tamanos.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        por página
      </label>
    </nav>
  );
}
