"use client";

import Link from "next/link";

import { Encabezado, EstadoCarga } from "../../../components/ui";
import type { Venta } from "../../../lib/api";
import { fechaConHora, NOMBRE_PAGO, precio } from "../../../lib/formato";
import { useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

export default function MisComprasPage() {
  const usuario = useRequiereSesion(["cliente"]);
  const compras = useDatos<Venta[]>(usuario ? "/mis-compras/" : null);

  if (!usuario) return null;

  const activas = (compras.datos ?? []).filter((c) => c.estado === "activa");
  const gastado = activas.reduce((t, c) => t + Number(c.total), 0);

  return (
    <>
      <Encabezado
        titulo="Mis compras"
        descripcion={
          compras.datos?.length
            ? `${activas.length === 1 ? "1 compra" : `${activas.length} compras`} por ${precio(gastado)} en total.`
            : "Las compras que hagas en la tienda aparecen aquí."
        }
      />

      <EstadoCarga cargando={compras.cargando} error={compras.error} />

      {compras.datos?.length === 0 && (
        <div className="panel panel-interior" style={{ maxWidth: 760 }}>
          <p>Todavía no tienes compras registradas a tu nombre.</p>
          <p className="secundario pequeno" style={{ marginTop: 6 }}>
            Si compraste en la tienda, pide que registren la venta con el mismo nombre o documento de tu cuenta.{" "}
            <Link href="/dashboard" className="boton-texto">Ver el catálogo</Link>
          </p>
        </div>
      )}

      <div className="compras">
        {compras.datos?.map((c) => (
          <article key={c.id_venta} className={`panel compra${c.estado === "anulada" ? " anulada" : ""}`}>
            <header>
              <h2 className="cifras">Compra N.º {c.id_venta}</h2>
              <span className="secundario pequeno">
                {fechaConHora(c.fecha)} · {NOMBRE_PAGO[c.metodo_pago] ?? c.metodo_pago}
                {c.estado === "anulada" && (
                  <>
                    {" · "}
                    <span className="etiqueta">Anulada</span>
                  </>
                )}
              </span>
            </header>
            <ul className="lineas">
              {c.detalles.map((d) => (
                <li key={d.id_pieza}>
                  <span>{d.pieza_nombre}</span>
                  <span className="secundario cifras">{d.cantidad} × {precio(d.precio_unitario)}</span>
                  <span className="cifras">{precio(d.subtotal)}</span>
                </li>
              ))}
            </ul>
            <footer>
              <span className="secundario">{c.estado === "anulada" ? "Compra anulada, sin cobro" : "Total"}</span>
              <strong className="cifras">{precio(c.total)}</strong>
            </footer>
          </article>
        ))}
      </div>
    </>
  );
}
