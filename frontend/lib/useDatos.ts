"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

type Resultado<T> = { endpoint: string; datos?: T; error?: string };

/**
 * Carga un endpoint de la API.
 * - endpoint null: no carga nada (p. ej. si el rol no tiene permiso).
 * - recargar(): vuelve a pedir los datos sin borrar los que se están mostrando.
 */
export function useDatos<T>(endpoint: string | null) {
  const [resultado, setResultado] = useState<Resultado<T> | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!endpoint) return;
    let activo = true;
    api<T>(endpoint)
      .then((datos) => {
        if (activo) setResultado({ endpoint, datos });
      })
      .catch((e: Error) => {
        if (activo) setResultado({ endpoint, error: e.message });
      });
    return () => {
      activo = false;
    };
  }, [endpoint, version]);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);
  const vigente = resultado && resultado.endpoint === endpoint ? resultado : null;

  return {
    datos: vigente?.datos,
    error: vigente?.error,
    cargando: endpoint !== null && !vigente,
    recargar,
  };
}
