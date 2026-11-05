"use client";

import { FormEvent, Fragment, useMemo, useState } from "react";

import Eliminar from "../../../components/Eliminar";
import { Aviso, Campo, Dialogo, Encabezado, EstadoCarga } from "../../../components/ui";
import { enviar, type Cliente, type Venta } from "../../../lib/api";
import { fecha, fechaConHora, normalizar, NOMBRE_PAGO, precio } from "../../../lib/formato";
import { useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

export default function ClientesPage() {
  const usuario = useRequiereSesion(["administrador", "vendedor"]);
  const clientes = useDatos<Cliente[]>(usuario ? "/clientes/" : null);
  const ventas = useDatos<Venta[]>(usuario ? "/ventas/" : null);

  const [busqueda, setBusqueda] = useState("");
  const [editando, setEditando] = useState<Cliente | "nuevo" | null>(null);
  const [eliminando, setEliminando] = useState<Cliente | null>(null);
  const [mensaje, setMensaje] = useState("");
  const [abiertoId, setAbiertoId] = useState<number | null>(null);

  // Compras de cada cliente, a partir del historial de ventas.
  const comprasPorCliente = useMemo(() => {
    const mapa = new Map<number, Venta[]>();
    for (const v of ventas.datos ?? []) {
      mapa.set(v.id_cliente, [...(mapa.get(v.id_cliente) ?? []), v]);
    }
    return mapa;
  }, [ventas.datos]);

  const filtrados = useMemo(() => {
    const q = normalizar(busqueda.trim());
    return (clientes.datos ?? [])
      .filter((c) => !q || normalizar(`${c.nombres} ${c.apellidos} ${c.documento ?? ""} ${c.email ?? ""} ${c.telefono ?? ""}`).includes(q))
      .sort((a, b) => `${a.nombres} ${a.apellidos}`.localeCompare(`${b.nombres} ${b.apellidos}`, "es"));
  }, [clientes.datos, busqueda]);

  if (!usuario) return null;

  return (
    <>
      <Encabezado
        titulo="Clientes"
        descripcion={clientes.datos ? `${clientes.datos.length} clientes. Haz clic en uno para ver sus compras.` : undefined}
      >
        <button type="button" className="boton" onClick={() => { setMensaje(""); setEditando("nuevo"); }}>Nuevo cliente</button>
      </Encabezado>

      <Aviso texto={mensaje} tipo="exito" />

      <div className="filtros" style={{ marginTop: mensaje ? 14 : 0 }}>
        <label className="visualmente-oculto" htmlFor="buscar">Buscar cliente</label>
        <input id="buscar" className="control buscar" type="search" placeholder="Buscar por nombre, documento, correo o teléfono"
          value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
      </div>

      <div className="tabla-contenedor">
        <EstadoCarga cargando={clientes.cargando} error={clientes.error}
          vacio={!!clientes.datos && filtrados.length === 0} textoVacio="Ningún cliente coincide con la búsqueda." />
        {filtrados.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Contacto</th>
                <th>Registro</th>
                <th className="num">Compras</th>
                <th><span className="visualmente-oculto">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((c) => {
                const compras = comprasPorCliente.get(c.id_cliente) ?? [];
                const activas = compras.filter((v) => v.estado === "activa");
                const total = activas.reduce((t, v) => t + Number(v.total), 0);
                const abierto = abiertoId === c.id_cliente;
                const alternar = () => setAbiertoId(abierto ? null : c.id_cliente);
                return (
                  <Fragment key={c.id_cliente}>
                    <tr
                      className={abierto ? "clicable seleccionada" : "clicable"}
                      onClick={alternar}
                      onKeyDown={(e) => {
                        if (e.target !== e.currentTarget) return;
                        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); alternar(); }
                      }}
                      tabIndex={0}
                      aria-expanded={abierto}
                    >
                      <td>
                        <span className="principal-celda">{c.nombres} {c.apellidos}</span>
                        <span className="sub cifras">{c.documento ? `Doc. ${c.documento}` : "Sin documento"}</span>
                      </td>
                      <td>
                        {c.telefono ?? "—"}
                        <span className="sub">{c.email ?? "Sin correo"}</span>
                      </td>
                      <td>
                        {c.user ? "Cuenta en línea" : "En tienda"}
                        <span className="sub">{fecha(c.fecha_registro)}</span>
                      </td>
                      <td className="num">
                        {ventas.datos ? (activas.length === 0 ? "—" : precio(total)) : "…"}
                        {activas.length > 0 && (
                          <span className="sub">{activas.length === 1 ? "1 compra" : `${activas.length} compras`}</span>
                        )}
                      </td>
                      <td className="num" onClick={(e) => e.stopPropagation()}>
                        <button type="button" className="boton-texto" onClick={() => { setMensaje(""); setEditando(c); }}>Editar</button>
                        <button type="button" className="boton-texto peligro" style={{ marginLeft: 12 }}
                          onClick={() => { setMensaje(""); setEliminando(c); }}>Eliminar</button>
                      </td>
                    </tr>
                    {abierto && (
                      <tr className="detalle-venta">
                        <td colSpan={5}>
                          {compras.length === 0 ? (
                            <p className="secundario pequeno" style={{ padding: "6px 0" }}>Sin compras registradas.</p>
                          ) : (
                            <ul className="historial-cliente">
                              {compras.map((v) => (
                                <li key={v.id_venta} className={v.estado === "anulada" ? "anulada" : undefined}>
                                  <span className="cifras">N.º {v.id_venta}</span>
                                  <span className="pequeno">{fechaConHora(v.fecha)}</span>
                                  <span className="pequeno">
                                    {v.detalles.map((d) => `${d.cantidad} × ${d.pieza_nombre}`).join(", ")}
                                    <span className="secundario"> · {NOMBRE_PAGO[v.metodo_pago] ?? v.metodo_pago}{v.estado === "anulada" ? " · anulada" : ""}</span>
                                  </span>
                                  <span className="num cifras">{precio(v.total)}</span>
                                </li>
                              ))}
                            </ul>
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

      <Dialogo abierto={!!editando} titulo={editando === "nuevo" ? "Nuevo cliente" : "Editar cliente"} alCerrar={() => setEditando(null)}>
        {editando && (
          <FormCliente
            cliente={editando === "nuevo" ? undefined : editando}
            alGuardar={(c) => {
              setEditando(null);
              setMensaje(`${c.nombres} ${c.apellidos} quedó guardado.`);
              clientes.recargar();
            }}
          />
        )}
      </Dialogo>

      <Eliminar
        endpoint={eliminando ? `/clientes/${eliminando.id_cliente}/` : null}
        nombre={eliminando ? `${eliminando.nombres} ${eliminando.apellidos}` : ""}
        explicacion={
          eliminando?.user
            ? "También se eliminará su cuenta en línea. Si tiene compras registradas, no se podrá eliminar."
            : "Si tiene compras registradas, no se podrá eliminar."
        }
        alCerrar={() => setEliminando(null)}
        alEliminar={() => {
          setMensaje(`${eliminando?.nombres} ${eliminando?.apellidos} fue eliminado.`);
          setEliminando(null);
          clientes.recargar();
        }}
      />
    </>
  );
}

function FormCliente({ cliente, alGuardar }: { cliente?: Cliente; alGuardar: (c: Cliente) => void }) {
  const [form, setForm] = useState({
    nombres: cliente?.nombres ?? "",
    apellidos: cliente?.apellidos ?? "",
    documento: cliente?.documento ?? "",
    telefono: cliente?.telefono ?? "",
    email: cliente?.email ?? "",
  });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    const cuerpo = { ...form, documento: form.documento || null, telefono: form.telefono || null, email: form.email || null };
    try {
      alGuardar(
        cliente
          ? await enviar<Cliente>(`/clientes/${cliente.id_cliente}/`, "PATCH", cuerpo)
          : await enviar<Cliente>("/clientes/", "POST", cuerpo)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar.");
      setEnviando(false);
    }
  }

  return (
    <form className="formulario" onSubmit={guardar}>
      <div className="fila-campos">
        <Campo id="c-nombres" etiqueta="Nombres">
          <input id="c-nombres" className="control" required value={form.nombres} onChange={(e) => setForm({ ...form, nombres: e.target.value })} />
        </Campo>
        <Campo id="c-apellidos" etiqueta="Apellidos">
          <input id="c-apellidos" className="control" required value={form.apellidos} onChange={(e) => setForm({ ...form, apellidos: e.target.value })} />
        </Campo>
      </div>
      <div className="fila-campos">
        <Campo id="c-documento" etiqueta="Documento (opcional)">
          <input id="c-documento" className="control" inputMode="numeric" value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} />
        </Campo>
        <Campo id="c-telefono" etiqueta="Teléfono (opcional)">
          <input id="c-telefono" className="control" type="tel" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} />
        </Campo>
      </div>
      <Campo id="c-email" etiqueta="Correo (opcional)">
        <input id="c-email" className="control" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </Campo>
      <Aviso texto={error} />
      <div className="pie-dialogo">
        <button type="submit" className="boton" disabled={enviando}>{enviando ? "Guardando…" : "Guardar"}</button>
      </div>
    </form>
  );
}
