"use client";

import { useMemo } from "react";
import type { Categoria, PiezaPublica } from "../lib/api";
import { useDatos } from "../lib/useDatos";

/**
 * Panel del login: cuántas piezas hay disponibles hoy en cada categoría.
 * Usa la API pública, así que funciona sin iniciar sesión.
 */
export default function Disponibilidad() {
  const piezas = useDatos<PiezaPublica[]>("/piezas/");
  const categorias = useDatos<Categoria[]>("/categorias/");

  const filas = useMemo(() => {
    if (!piezas.datos || !categorias.datos) return [];
    return categorias.datos
      .map((c) => {
        const deLaCategoria = piezas.datos!.filter((p) => p.categoria_nombre === c.nombre);
        return {
          nombre: c.nombre,
          total: deLaCategoria.length,
          disponibles: deLaCategoria.filter((p) => p.en_stock).length,
          reacondicionadas: deLaCategoria.filter((p) => p.en_stock && p.condicion === "reacondicionada").length,
        };
      })
      .filter((f) => f.total > 0);
  }, [piezas.datos, categorias.datos]);

  const disponibles = filas.reduce((suma, f) => suma + f.disponibles, 0);

  return (
    <section className="disponible" aria-labelledby="titulo-disponible">
      <h2 id="titulo-disponible">Disponible hoy</h2>
      <p className="nota">
        {filas.length
          ? `${disponibles} referencias con unidades en tienda. Al lado, cuántas son reacondicionadas.`
          : "Consultando el inventario…"}
      </p>

      {piezas.error || categorias.error ? (
        <p className="vacio">No se pudo consultar el inventario en este momento.</p>
      ) : (
        <ul>
          {filas.map((f) => (
            <li key={f.nombre}>
              <span>{f.nombre}</span>
              <span className="cuenta cifras">
                {f.disponibles}
                <small>
                  {f.reacondicionadas > 0 ? `${f.reacondicionadas} reacond.` : "nuevas"}
                </small>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
