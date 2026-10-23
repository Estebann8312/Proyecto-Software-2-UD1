"use client";

import Link from "next/link";
import { Fragment, useMemo, useState } from "react";

import { Aviso, Dialogo, Encabezado, EstadoCarga } from "../../../components/ui";
import { enviar, type Cliente, type Empleado, type MetodoPago, type Venta } from "../../../lib/api";
import { fechaConHora, normalizar, NOMBRE_PAGO, precio } from "../../../lib/formato";
import { useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

export default function VentasPage() {
  const usuario = useRequiereSesion(["administrador", "vendedor"]);
  const esAdmin = usuario?.rol === "administrador";

  const ventas = useDatos<Venta[]>(usuario ? "/ventas/" : null);
  const clientes = useDatos<Cliente[]>(usuario ? "/clientes/" : null);
  const empleados = useDatos<Empleado[]>(esAdmin ? "/usuarios/" : null);

  const [busqueda, setBusqueda] = useState("");
  const [estado, setEstado] = useState("");
  const [metodo, setMetodo] = useState("");
  const [abiertaId, setAbiertaId] = useState<number | null>(null);
  const [porAnular, setPorAnular] = useState<Venta | null>(null);
  const [anulando, setAnulando] = useState(false);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");

  const nombreCliente = useMemo(() => {
    const mapa = new Map((clientes.datos ?? []).map((c) => [c.id_cliente, `${c.nombres} ${c.apellidos}`]));
    return (id: number) => mapa.get(id) ?? `Cliente ${id}`;
  }, [clientes.datos]);

  const nombreVendedor = useMemo(() => {
    const mapa = new Map((empleados.datos ?? []).map((e) => [e.id_usuario, `${e.nombres.split(" ")[0]} ${e.apellidos.split(" ")[0]}`]));
    return (id: number) => (id === usuario?.id_usuario ? "Tú" : mapa.get(id) ?? "Otro vendedor");
  }, [empleados.datos, usuario]);

  const filtradas = useMemo(() => {
    const q = normalizar(busqueda.trim().replace(/^n\.?º?\s*/i, ""));
    return (ventas.datos ?? []).filter((v) => {
      if (estado && v.estado !== estado) return false;
      if (metodo && v.metodo_pago !== metodo) return false;
      if (q && !String(v.id_venta).startsWith(q) && !normalizar(nombreCliente(v.id_cliente)).includes(q)) return false;
      return true;
    });
  }, [ventas.datos, busqueda, estado, metodo, nombreCliente]);

  const totalFiltrado = filtradas
    .filter((v) => v.estado === "activa")
    .reduce((t, v) => t + Number(v.total), 0);

  async function anular() {
    if (!porAnular) return;
    setError("");
    setAnulando(true);
    try {
      await enviar(`/ventas/${porAnular.id_venta}/anular/`, "POST");
      setMensaje(`Venta N.º ${porAnular.id_venta} anulada. Las unidades volvieron al inventario.`);
      setPorAnular(null);
      ventas.recargar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo anular la venta.");
    } finally {
      setAnulando(false);
    }
  }

  if (!usuario) return null;

  return (
    <>
      <Encabezado
        titulo="Ventas"
        descripcion={
          ventas.datos
            ? `${filtradas.length} ventas · ${precio(totalFiltrado)} en ventas activas`
            : "Historial de ventas de la tienda."
        }
      >
        <Link href="/ventas/nueva" className="boton">Registrar venta</Link>
      </Encabezado>

      <Aviso texto={mensaje} tipo="exito" />

      <div className="filtros" style={{ marginTop: mensaje ? 14 : 0 }}>
        <label className="visualmente-oculto" htmlFor="buscar">Buscar venta</label>
        <input id="buscar" className="control buscar" type="search" placeholder="Buscar por número o cliente"
          value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
        <label className="visualmente-oculto" htmlFor="f-estado">Estado</label>
        <select id="f-estado" className="control" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Activas y anuladas</option>
          <option value="activa">Solo activas</option>
          <option value="anulada">Solo anuladas</option>
        </select>
        <label className="visualmente-oculto" htmlFor="f-metodo">Método de pago</label>
        <select id="f-metodo" className="control" value={metodo} onChange={(e) => setMetodo(e.target.value)}>
          <option value="">Cualquier método</option>
          {(Object.keys(NOMBRE_PAGO) as MetodoPago[]).map((m) => (
            <option key={m} value={m}>{NOMBRE_PAGO[m]}</option>
          ))}
        </select>
      </div>

      <div className="tabla-contenedor">
        <EstadoCarga cargando={ventas.cargando} error={ventas.error}
          vacio={!!ventas.datos && filtradas.length === 0}
          textoVacio={ventas.datos?.length ? "Ninguna venta coincide con los filtros." : "Todavía no hay ventas."} />
        {filtradas.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Venta</th>
                <th>Cliente</th>
                <th>Vendedor</th>
                <th>Pago</th>
                <th className="num">Total</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.map((v) => {
                const abierta = abiertaId === v.id_venta;
                const alternar = () => setAbiertaId(abierta ? null : v.id_venta);
                return (
                  <Fragment key={v.id_venta}>
                    <tr
                      className={`clicable${abierta ? " seleccionada" : ""}${v.estado === "anulada" ? " anulada" : ""}`}
                      onClick={alternar}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); alternar(); } }}
                      tabIndex={0}
                      aria-expanded={abierta}
                    >
                      <td>
                        <span className="principal-celda cifras">N.º {v.id_venta}</span>
                        <span className="sub">{fechaConHora(v.fecha)}</span>
                      </td>
                      <td>{nombreCliente(v.id_cliente)}</td>
                      <td>{nombreVendedor(v.id_vendedor)}</td>
                      <td>{NOMBRE_PAGO[v.metodo_pago] ?? v.metodo_pago}</td>
                      <td className="num">{precio(v.total)}</td>
                      <td>
                        <span className={v.estado === "activa" ? "etiqueta ok" : "etiqueta"}>
                          {v.estado === "activa" ? "Activa" : "Anulada"}
                        </span>
                      </td>
                    </tr>
                    {abierta && (
                      <tr className="detalle-venta">
                        <td colSpan={6}>
                          <ul>
                            {v.detalles.map((d) => (
                              <li key={d.id_pieza}>
                                <span>{d.pieza_nombre}</span>
                                <span className="cifras secundario">{d.cantidad} × {precio(d.precio_unitario)}</span>
                                <span className="num cifras">{precio(d.subtotal)}</span>
                              </li>
                            ))}
                          </ul>
                          {esAdmin && v.estado === "activa" && (
                            <div className="pie">
                              <button type="button" className="boton-texto peligro"
                                onClick={() => { setError(""); setMensaje(""); setPorAnular(v); }}>
                                Anular venta
                              </button>
                              <span className="secundario pequeno">Las unidades vuelven al inventario.</span>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <Dialogo abierto={!!porAnular} titulo={`¿Anular la venta N.º ${porAnular?.id_venta ?? ""}?`} alCerrar={() => setPorAnular(null)}>
        {porAnular && (
          <div className="formulario">
            <p>
              Se devolverán al inventario{" "}
              {porAnular.detalles.map((d) => `${d.cantidad} × ${d.pieza_nombre}`).join(", ")}.
              La venta queda en el historial marcada como anulada; no se puede deshacer.
            </p>
            <Aviso texto={error} />
            <div className="pie-dialogo">
              <button type="button" className="boton secundario" onClick={() => setPorAnular(null)}>Cancelar</button>
              <button type="button" className="boton peligro" onClick={anular} disabled={anulando}>
                {anulando ? "Anulando…" : `Anular por ${precio(porAnular.total)}`}
              </button>
            </div>
          </div>
        )}
      </Dialogo>
    </>
  );
}
