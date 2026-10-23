"use client";

import { useEffect, useRef } from "react";

export function Encabezado({
  titulo,
  descripcion,
  children,
}: {
  titulo: string;
  descripcion?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="encabezado">
      <div>
        <h1>{titulo}</h1>
        {descripcion && <p>{descripcion}</p>}
      </div>
      {children && <div className="acciones">{children}</div>}
    </header>
  );
}

/** Muestra "Cargando", el error o "vacío"; si no aplica ninguno, no muestra nada. */
export function EstadoCarga({
  cargando,
  error,
  vacio,
  textoVacio = "No hay registros todavía.",
}: {
  cargando: boolean;
  error?: string;
  vacio?: boolean;
  textoVacio?: string;
}) {
  if (cargando) return <p className="cargando">Cargando…</p>;
  if (error) return <p className="error-carga" role="alert">{error}</p>;
  if (vacio) return <p className="vacio">{textoVacio}</p>;
  return null;
}

export function Aviso({ texto, tipo = "error" }: { texto: string; tipo?: "error" | "exito" }) {
  if (!texto) return null;
  return (
    <p className={tipo === "exito" ? "aviso exito" : "aviso"} role={tipo === "exito" ? "status" : "alert"}>
      {texto}
    </p>
  );
}

/** Diálogo nativo (<dialog>): accesible, cierra con Esc y atrapa el foco. */
export function Dialogo({
  abierto,
  titulo,
  alCerrar,
  children,
}: {
  abierto: boolean;
  titulo: string;
  alCerrar: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialogo = ref.current;
    if (!dialogo) return;
    if (abierto && !dialogo.open) dialogo.showModal();
    if (!abierto && dialogo.open) dialogo.close();
  }, [abierto]);

  return (
    <dialog ref={ref} className="dialogo" onClose={alCerrar} aria-labelledby="titulo-dialogo">
      {abierto && (
        <>
          <header>
            <h2 id="titulo-dialogo">{titulo}</h2>
            <button type="button" className="cerrar" onClick={alCerrar}>
              Cerrar
            </button>
          </header>
          <div className="cuerpo">{children}</div>
        </>
      )}
    </dialog>
  );
}

export function Campo({
  id,
  etiqueta,
  ayuda,
  children,
}: {
  id: string;
  etiqueta: string;
  ayuda?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="campo">
      <label htmlFor={id}>{etiqueta}</label>
      {children}
      {ayuda && <span className="ayuda">{ayuda}</span>}
    </div>
  );
}
