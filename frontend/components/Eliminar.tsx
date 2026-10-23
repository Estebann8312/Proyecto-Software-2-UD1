"use client";

import { useState } from "react";
import { enviar } from "../lib/api";
import { Aviso, Dialogo } from "./ui";

/** Confirmación de borrado. Si el backend lo impide (409), muestra su motivo. */
export default function Eliminar({
  endpoint,
  nombre,
  explicacion,
  alCerrar,
  alEliminar,
}: {
  endpoint: string | null;
  nombre: string;
  explicacion?: string;
  alCerrar: () => void;
  alEliminar: () => void;
}) {
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function eliminar() {
    if (!endpoint) return;
    setError("");
    setEnviando(true);
    try {
      await enviar(endpoint, "DELETE");
      alEliminar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo eliminar.");
    } finally {
      setEnviando(false);
    }
  }

  function cerrar() {
    setError("");
    alCerrar();
  }

  return (
    <Dialogo abierto={!!endpoint} titulo={`¿Eliminar a ${nombre}?`} alCerrar={cerrar}>
      <div className="formulario">
        <p>{explicacion ?? "Esta acción no se puede deshacer."}</p>
        <Aviso texto={error} />
        <div className="pie-dialogo">
          <button type="button" className="boton secundario" onClick={cerrar}>Cancelar</button>
          <button type="button" className="boton peligro" onClick={eliminar} disabled={enviando}>
            {enviando ? "Eliminando…" : "Eliminar"}
          </button>
        </div>
      </div>
    </Dialogo>
  );
}
