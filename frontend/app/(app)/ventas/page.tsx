"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Paginador, usePaginacion } from "../../../components/Paginador";
import { Aviso, Dialogo, Encabezado, EstadoCarga } from "../../../components/ui";
import { enviar, type Cliente, type Empleado, type MetodoPago, type Venta } from "../../../lib/api";
import { fechaConHora, marcaDeTiempo, normalizar, NOMBRE_PAGO, precio } from "../../../lib/formato";
import { useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

type Orden = "recientes" | "antiguas" | "mayor" | "menor";

function unidades(v: Venta) {
  return v.detalles.reduce((t, d) => t + d.cantidad, 0);
}

export default function VentasPage() {
  const usuario = useRequiereSesion(["administrador", "vendedor"]);
  const esAdmin = usuario?.rol === "administrador";

  const ventas = useDatos<Venta[]>(usuario ? "/ventas/" : null);
  const clientes = useDatos<Cliente[]>(usuario ? "/clientes/" : null);
  const empleados = useDatos<Empleado[]>(esAdmin ? "/usuarios/" : null);

  const [busqueda, setBusqueda] = useState("");
  const [estado, setEstado] = useState("");
  const [metodo, setMetodo] = useState("");
  const [vendedor, setVendedor] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [orden, setOrden] = useState<Orden>("recientes");
  const [abiertaId, setAbiertaId] = useState<number | null>(null);
  const [porAnular, setPorAnular] = useState<Venta | null>(null);
  const [anulando, setAnulando] = useState(false);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");

  const clientePorId = useMemo(
    () => new Map((clientes.datos ?? []).map((c) => [c.id_cliente, c])),
    [clientes.datos]
  );
  const nombreCliente = (id: number) => {
    const c = clientePorId.get(id);
    return c ? `${c.nombres} ${c.apellidos}` : `Cliente ${id}`;
  };

  const nombreVendedor = useMemo(() => {
    const mapa = new Map((empleados.datos ?? []).map((e) => [e.id_usuario, `${e.nombres.split(" ")[0]} ${e.apellidos.split(" ")[0]}`]));
    return (id: number) => (id === usuario?.id_usuario ? "Tú" : mapa.get(id) ?? "Otro vendedor");
  }, [empleados.datos, usuario]);

  const filtradas = useMemo(() => {
    const q = normalizar(busqueda.trim().replace(/^n\.?º?\s*/i, ""));
    const lista = (ventas.datos ?? []).filter((v) => {
      if (estado && v.estado !== estado) return false;
      if (metodo && v.metodo_pago !== metodo) return false;
      if (vendedor && String(v.id_vendedor) !== vendedor) return false;
      const dia = v.fecha.slice(0, 10);
      if (desde && dia < desde) return false;
      if (hasta && dia > hasta) return false;
      if (q) {
        const c = clientePorId.get(v.id_cliente);
        const texto = normalizar(
          `${c ? `${c.nombres} ${c.apellidos} ${c.documento ?? ""}` : ""} ${v.detalles.map((d) => d.pieza_nombre).join(" ")}`
        );
        if (!String(v.id_venta).startsWith(q) && !texto.includes(q)) return false;
      }
      return true;
    });
    const comparar: Record<Orden, (a: Venta, b: Venta) => number> = {
      recientes: (a, b) => marcaDeTiempo(b.fecha) - marcaDeTiempo(a.fecha),
      antiguas: (a, b) => marcaDeTiempo(a.fecha) - marcaDeTiempo(b.fecha),
      mayor: (a, b) => Number(b.total) - Number(a.total),
      menor: (a, b) => Number(a.total) - Number(b.total),
    };
    return lista.sort(comparar[orden]);
  }, [ventas.datos, busqueda, estado, metodo, vendedor, desde, hasta, orden, clientePorId]);

  const paginas = usePaginacion(filtradas, 10, [busqueda, estado, metodo, vendedor, desde, hasta, orden].join("|"));

  const activas = filtradas.filter((v) => v.estado === "activa");
  const totalFiltrado = activas.reduce((t, v) => t + Number(v.total), 0);
  const hayFiltros = !!(busqueda || estado || metodo || vendedor || desde || hasta);
  const abierta = ventas.datos?.find((v) => v.id_venta === abiertaId) ?? null;

  function limpiar() {
    setBusqueda(""); setEstado(""); setMetodo(""); setVendedor(""); setDesde(""); setHasta("");
  }

  async function anular() {
    if (!porAnular) return;
    setError("");
    setAnulando(true);
    try {
      await enviar(`/ventas/${porAnular.id_venta}/anular/`, "POST");
      setMensaje(`Venta N.º ${porAnular.id_venta} anulada. Las unidades volvieron al inventario.`);
      setPorAnular(null);
      setAbiertaId(null);
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
      <Encabezado titulo="Ventas" descripcion="Historial de ventas de la tienda. Haz clic en una venta para ver su detalle.">
        <Link href="/ventas/nueva" className="boton">Registrar venta</Link>
      </Encabezado>

      <Aviso texto={mensaje} tipo="exito" />

      {ventas.datos && (
        <section className="cifras-resumen compacto" aria-label="Resumen de las ventas filtradas" style={{ marginTop: mensaje ? 14 : 0 }}>
          <div className="cifra">
            <span className="valor cifras">{precio(totalFiltrado)}</span>
            <span className="nombre">Vendido</span>
            <span className="detalle">Solo ventas activas</span>
          </div>
          <div className="cifra">
            <span className="valor cifras">{activas.length}</span>
            <span className="nombre">Ventas activas</span>
            <span className="detalle">{filtradas.length - activas.length} anuladas</span>
          </div>
          <div className="cifra">
            <span className="valor cifras">{precio(activas.length ? totalFiltrado / activas.length : 0)}</span>
            <span className="nombre">Ticket promedio</span>
            <span className="detalle">Por venta activa</span>
          </div>
          <div className="cifra">
            <span className="valor cifras">{activas.reduce((t, v) => t + unidades(v), 0)}</span>
            <span className="nombre">Unidades vendidas</span>
            <span className="detalle">{hayFiltros ? "Con los filtros aplicados" : "En todo el historial"}</span>
          </div>
        </section>
      )}

      <div className="filtros">
        <label className="visualmente-oculto" htmlFor="buscar">Buscar venta</label>
        <input id="buscar" className="control buscar" type="search" placeholder="Número, cliente, documento o pieza"
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
        {esAdmin && (
          <>
            <label className="visualmente-oculto" htmlFor="f-vendedor">Vendedor</label>
            <select id="f-vendedor" className="control" value={vendedor} onChange={(e) => setVendedor(e.target.value)}>
              <option value="">Todos los vendedores</option>
              {empleados.datos?.map((e) => (
                <option key={e.id_usuario} value={e.id_usuario}>{e.nombres} {e.apellidos}</option>
              ))}
            </select>
          </>
        )}
      </div>
      <div className="filtros">
        <label className="filtro-fecha pequeno secundario">
          Desde
          <input className="control cifras" type="date" value={desde} max={hasta || undefined}
            onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label className="filtro-fecha pequeno secundario">
          Hasta
          <input className="control cifras" type="date" value={hasta} min={desde || undefined}
            onChange={(e) => setHasta(e.target.value)} />
        </label>
        <label className="visualmente-oculto" htmlFor="f-orden">Ordenar</label>
        <select id="f-orden" className="control" value={orden} onChange={(e) => setOrden(e.target.value as Orden)}>
          <option value="recientes">Más recientes primero</option>
          <option value="antiguas">Más antiguas primero</option>
          <option value="mayor">Mayor total primero</option>
          <option value="menor">Menor total primero</option>
        </select>
        {hayFiltros && (
          <button type="button" className="boton-texto" onClick={limpiar}>Quitar filtros</button>
        )}
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
                <th>Piezas</th>
                <th>Vendedor</th>
                <th>Pago</th>
                <th className="num">Total</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {paginas.visibles.map((v) => (
                <tr
                  key={v.id_venta}
                  className={`clicable${v.estado === "anulada" ? " anulada" : ""}`}
                  onClick={() => setAbiertaId(v.id_venta)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setAbiertaId(v.id_venta); } }}
                  tabIndex={0}
                  aria-label={`Ver detalle de la venta ${v.id_venta}`}
                >
                  <td>
                    <span className="principal-celda cifras">N.º {v.id_venta}</span>
                    <span className="sub">{fechaConHora(v.fecha)}</span>
                  </td>
                  <td>{nombreCliente(v.id_cliente)}</td>
                  <td>
                    <span className="resumen-piezas">
                      {v.detalles[0]?.pieza_nombre}
                      {v.detalles.length > 1 && <span className="secundario"> y {v.detalles.length - 1} más</span>}
                    </span>
                    <span className="sub cifras">{unidades(v) === 1 ? "1 unidad" : `${unidades(v)} unidades`}</span>
                  </td>
                  <td>{nombreVendedor(v.id_vendedor)}</td>
                  <td>{NOMBRE_PAGO[v.metodo_pago] ?? v.metodo_pago}</td>
                  <td className="num">{precio(v.total)}</td>
                  <td>
                    <span className={v.estado === "activa" ? "etiqueta ok" : "etiqueta"}>
                      {v.estado === "activa" ? "Activa" : "Anulada"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <Paginador p={paginas} nombre="ventas" />

      <Dialogo abierto={!!abierta && !porAnular} titulo={abierta ? `Venta N.º ${abierta.id_venta}` : ""}
        alCerrar={() => setAbiertaId(null)}>
        {abierta && (
          <DetalleVenta
            venta={abierta}
            cliente={clientePorId.get(abierta.id_cliente)}
            vendedor={nombreVendedor(abierta.id_vendedor)}
            puedeAnular={esAdmin && abierta.estado === "activa"}
            alAnular={() => { setError(""); setMensaje(""); setPorAnular(abierta); }}
          />
        )}
      </Dialogo>

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

function DetalleVenta({
  venta,
  cliente,
  vendedor,
  puedeAnular,
  alAnular,
}: {
  venta: Venta;
  cliente?: Cliente;
  vendedor: string;
  puedeAnular: boolean;
  alAnular: () => void;
}) {
  const anulada = venta.estado === "anulada";
  return (
    <div className="detalle-factura">
      <div className="estado-factura">
        <span className={anulada ? "etiqueta" : "etiqueta ok"}>{anulada ? "Anulada" : "Activa"}</span>
        <span className="secundario pequeno">{fechaConHora(venta.fecha)}</span>
      </div>

      <dl className="datos-factura">
        <div>
          <dt>Cliente</dt>
          <dd>{cliente ? `${cliente.nombres} ${cliente.apellidos}` : `Cliente ${venta.id_cliente}`}</dd>
          {cliente && (
            <span className="secundario pequeno cifras">
              {[cliente.documento && `Doc. ${cliente.documento}`, cliente.telefono].filter(Boolean).join(" · ") || "Sin datos de contacto"}
            </span>
          )}
        </div>
        <div>
          <dt>Atendió</dt>
          <dd>{vendedor}</dd>
        </div>
        <div>
          <dt>Método de pago</dt>
          <dd>{NOMBRE_PAGO[venta.metodo_pago] ?? venta.metodo_pago}</dd>
        </div>
      </dl>

      <table className="tabla-factura">
        <thead>
          <tr>
            <th>Pieza</th>
            <th className="num">Cant.</th>
            <th className="num">Precio unit.</th>
            <th className="num">Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {venta.detalles.map((d) => (
            <tr key={d.id_pieza}>
              <td>{d.pieza_nombre}</td>
              <td className="num cifras">{d.cantidad}</td>
              <td className="num cifras">{precio(d.precio_unitario)}</td>
              <td className="num cifras">{precio(d.subtotal)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3}>{anulada ? "Total (anulada, sin cobro)" : "Total"}</td>
            <td className="num cifras">{precio(venta.total)}</td>
          </tr>
        </tfoot>
      </table>

      {puedeAnular && (
        <div className="pie-dialogo separado">
          <span className="secundario pequeno">Al anularla, las unidades vuelven al inventario.</span>
          <button type="button" className="boton secundario peligro-texto" onClick={alAnular}>Anular venta</button>
        </div>
      )}
    </div>
  );
}
