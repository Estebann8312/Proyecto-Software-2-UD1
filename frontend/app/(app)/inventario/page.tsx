"use client";

import { FormEvent, useMemo, useState } from "react";

import { Aviso, Campo, Dialogo, Encabezado, EstadoCarga } from "../../../components/ui";
import { enviar, type Categoria, type Condicion, type Pieza, type Proveedor, type Venta } from "../../../lib/api";
import { estadoStock, fecha, marcaDeTiempo, normalizar, NOMBRE_CONDICION, precio } from "../../../lib/formato";
import { useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

type Movimiento = {
  clave: string;
  tipo: "entrada" | "salida";
  cantidad: number;
  fecha: string;
  texto: string;
  anulada?: boolean;
};

export default function InventarioPage() {
  const usuario = useRequiereSesion(["administrador", "vendedor"]);
  const esAdmin = usuario?.rol === "administrador";

  const piezas = useDatos<Pieza[]>(usuario ? "/piezas/" : null);
  const categorias = useDatos<Categoria[]>("/categorias/");
  const proveedores = useDatos<Proveedor[]>(usuario ? "/proveedores/" : null);
  const ventas = useDatos<Venta[]>(usuario ? "/ventas/" : null);

  const [busqueda, setBusqueda] = useState("");
  const [categoria, setCategoria] = useState("");
  const [condicion, setCondicion] = useState("");
  const [estado, setEstado] = useState("");
  const [seleccionId, setSeleccionId] = useState<number | null>(null);
  const [dialogo, setDialogo] = useState<null | "nueva" | "editar" | "lote">(null);
  const [mensaje, setMensaje] = useState("");

  const nombreCategoria = useMemo(() => {
    const mapa = new Map((categorias.datos ?? []).map((c) => [c.id_categoria, c.nombre]));
    return (id: number) => mapa.get(id) ?? "Sin categoría";
  }, [categorias.datos]);

  const nombreProveedor = useMemo(() => {
    const mapa = new Map((proveedores.datos ?? []).map((p) => [p.id_proveedor, p.nombre]));
    return (id: number) => mapa.get(id) ?? `Proveedor ${id}`;
  }, [proveedores.datos]);

  const filtradas = useMemo(() => {
    const q = normalizar(busqueda.trim());
    return (piezas.datos ?? []).filter((p) => {
      if (q && !normalizar(`${p.nombre} ${p.descripcion ?? ""}`).includes(q)) return false;
      if (categoria && String(p.id_categoria) !== categoria) return false;
      if (condicion && p.condicion !== condicion) return false;
      if (estado && estadoStock(p.stock_actual).clase !== estado) return false;
      return true;
    });
  }, [piezas.datos, busqueda, categoria, condicion, estado]);

  const seleccion = piezas.datos?.find((p) => p.id_pieza === seleccionId) ?? null;

  const movimientos = useMemo<Movimiento[]>(() => {
    if (!seleccion) return [];
    const entradas: Movimiento[] = seleccion.lotes.map((l) => ({
      clave: `l${l.id_lote}`,
      tipo: "entrada",
      cantidad: l.cantidad,
      fecha: l.fecha_compra,
      texto: `${nombreProveedor(l.id_proveedor)} · ${precio(l.costo_unitario)} c/u`,
    }));
    const salidas: Movimiento[] = (ventas.datos ?? []).flatMap((v) =>
      v.detalles
        .filter((d) => d.id_pieza === seleccion.id_pieza)
        .map((d) => ({
          clave: `v${v.id_venta}`,
          tipo: "salida" as const,
          cantidad: d.cantidad,
          fecha: v.fecha,
          texto: v.estado === "anulada" ? `Venta N.º ${v.id_venta}, anulada` : `Venta N.º ${v.id_venta}`,
          anulada: v.estado === "anulada",
        }))
    );
    return [...entradas, ...salidas].sort((a, b) => marcaDeTiempo(b.fecha) - marcaDeTiempo(a.fecha));
  }, [seleccion, ventas.datos, nombreProveedor]);

  function guardado(texto: string, id?: number) {
    setDialogo(null);
    setMensaje(texto);
    if (id) setSeleccionId(id);
    piezas.recargar();
  }

  if (!usuario) return null;

  return (
    <>
      <Encabezado
        titulo="Inventario"
        descripcion={
          piezas.datos
            ? `${piezas.datos.length} piezas. El stock solo cambia con entradas de proveedor y con ventas.`
            : "El stock solo cambia con entradas de proveedor y con ventas."
        }
      >
        {esAdmin && (
          <button type="button" className="boton" onClick={() => { setMensaje(""); setDialogo("nueva"); }}>
            Nueva pieza
          </button>
        )}
      </Encabezado>

      <Aviso texto={mensaje} tipo="exito" />

      <div className="filtros" style={{ marginTop: mensaje ? 14 : 0 }}>
        <label className="visualmente-oculto" htmlFor="buscar">Buscar pieza</label>
        <input id="buscar" className="control buscar" type="search" placeholder="Buscar por nombre o descripción"
          value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />

        <label className="visualmente-oculto" htmlFor="f-categoria">Categoría</label>
        <select id="f-categoria" className="control" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          <option value="">Todas las categorías</option>
          {categorias.datos?.map((c) => (
            <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>
          ))}
        </select>

        <label className="visualmente-oculto" htmlFor="f-condicion">Condición</label>
        <select id="f-condicion" className="control" value={condicion} onChange={(e) => setCondicion(e.target.value)}>
          <option value="">Nuevas y reacondicionadas</option>
          <option value="nueva">Solo nuevas</option>
          <option value="reacondicionada">Solo reacondicionadas</option>
        </select>

        <label className="visualmente-oculto" htmlFor="f-estado">Stock</label>
        <select id="f-estado" className="control" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Cualquier stock</option>
          <option value="ok">Disponibles</option>
          <option value="alerta">Stock bajo</option>
          <option value="peligro">Agotadas</option>
        </select>
      </div>

      <div className="inventario">
        <div className="tabla-contenedor">
          <EstadoCarga cargando={piezas.cargando} error={piezas.error}
            vacio={!!piezas.datos && filtradas.length === 0} textoVacio="Ninguna pieza coincide con los filtros." />
          {filtradas.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Pieza</th>
                  <th>Condición</th>
                  <th className="num">Precio</th>
                  <th className="num">Stock</th>
                </tr>
              </thead>
              <tbody>
                {filtradas.map((p) => {
                  const e = estadoStock(p.stock_actual);
                  const activa = p.id_pieza === seleccionId;
                  return (
                    <tr
                      key={p.id_pieza}
                      className={activa ? "clicable seleccionada" : "clicable"}
                      onClick={() => setSeleccionId(p.id_pieza)}
                      onKeyDown={(ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); setSeleccionId(p.id_pieza); } }}
                      tabIndex={0}
                      aria-selected={activa}
                    >
                      <td>
                        <span className="principal-celda">{p.nombre}</span>
                        <span className="sub">{nombreCategoria(p.id_categoria)}</span>
                      </td>
                      <td>{NOMBRE_CONDICION[p.condicion]}</td>
                      <td className="num">{precio(p.precio_venta)}</td>
                      <td className="num">
                        <span className={`etiqueta ${e.clase}`}>{p.stock_actual}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <aside className="panel detalle-pieza" aria-live="polite">
          {!seleccion ? (
            <p className="vacio">Elige una pieza para ver su stock y su historial de entradas y salidas.</p>
          ) : (
            <>
              <header>
                <span className={`etiqueta ${estadoStock(seleccion.stock_actual).clase}`}>
                  {estadoStock(seleccion.stock_actual).texto}
                </span>
                <h2>{seleccion.nombre}</h2>
                <p className="secundario pequeno">
                  {nombreCategoria(seleccion.id_categoria)} · {NOMBRE_CONDICION[seleccion.condicion]}
                </p>
                {seleccion.descripcion && <p className="pequeno" style={{ marginTop: 8 }}>{seleccion.descripcion}</p>}
              </header>

              <dl className="datos-pieza">
                <div>
                  <dt>En tienda</dt>
                  <dd className="cifras">{seleccion.stock_actual} ud.</dd>
                </div>
                <div>
                  <dt>Precio de venta</dt>
                  <dd className="cifras">{precio(seleccion.precio_venta)}</dd>
                </div>
              </dl>

              {esAdmin && (
                <div className="acciones">
                  <button type="button" className="boton" onClick={() => { setMensaje(""); setDialogo("lote"); }}>
                    Registrar entrada
                  </button>
                  <button type="button" className="boton secundario" onClick={() => { setMensaje(""); setDialogo("editar"); }}>
                    Editar
                  </button>
                </div>
              )}

              <section className="movimientos">
                <h3>Entradas y salidas</h3>
                {movimientos.length === 0 ? (
                  <p className="secundario pequeno">Sin movimientos registrados.</p>
                ) : (
                  <ol>
                    {movimientos.map((m) => (
                      <li key={m.clave} className={`${m.tipo}${m.anulada ? " anulada" : ""}`}>
                        <span className="cantidad">{m.tipo === "entrada" ? `+${m.cantidad}` : `−${m.cantidad}`}</span>
                        <span className="pequeno">{m.tipo === "entrada" ? `Entrada · ${m.texto}` : m.texto}</span>
                        <span className="fecha">{fecha(m.fecha)}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </>
          )}
        </aside>
      </div>

      {esAdmin && (
        <>
          <Dialogo abierto={dialogo === "nueva"} titulo="Nueva pieza" alCerrar={() => setDialogo(null)}>
            <FormPieza categorias={categorias.datos ?? []} alGuardar={(p) => guardado(`“${p.nombre}” quedó registrada. Ahora registra su primera entrada para tener stock.`, p.id_pieza)} />
          </Dialogo>

          <Dialogo abierto={dialogo === "editar"} titulo="Editar pieza" alCerrar={() => setDialogo(null)}>
            {seleccion && (
              <FormPieza pieza={seleccion} categorias={categorias.datos ?? []} alGuardar={(p) => guardado(`Cambios guardados en “${p.nombre}”.`)} />
            )}
          </Dialogo>

          <Dialogo abierto={dialogo === "lote"} titulo="Registrar entrada de proveedor" alCerrar={() => setDialogo(null)}>
            {seleccion && (
              <FormLote pieza={seleccion} proveedores={proveedores.datos ?? []}
                alGuardar={(cantidad) => guardado(`Entrada registrada: +${cantidad} ud. de “${seleccion.nombre}”.`)} />
            )}
          </Dialogo>
        </>
      )}
    </>
  );
}

function FormPieza({
  pieza,
  categorias,
  alGuardar,
}: {
  pieza?: Pieza;
  categorias: Categoria[];
  alGuardar: (p: Pieza) => void;
}) {
  const [form, setForm] = useState({
    nombre: pieza?.nombre ?? "",
    id_categoria: pieza ? String(pieza.id_categoria) : "",
    condicion: (pieza?.condicion ?? "nueva") as Condicion,
    precio_venta: pieza?.precio_venta ?? "",
    descripcion: pieza?.descripcion ?? "",
  });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    const cuerpo = { ...form, id_categoria: Number(form.id_categoria), descripcion: form.descripcion || null };
    try {
      const resultado = pieza
        ? await enviar<Pieza>(`/piezas/${pieza.id_pieza}/`, "PATCH", cuerpo)
        : await enviar<Pieza>("/piezas/", "POST", cuerpo);
      alGuardar(resultado);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar.");
      setEnviando(false);
    }
  }

  return (
    <form className="formulario" onSubmit={guardar}>
      <Campo id="p-nombre" etiqueta="Nombre">
        <input id="p-nombre" className="control" value={form.nombre} required maxLength={150}
          onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
      </Campo>
      <div className="fila-campos">
        <Campo id="p-categoria" etiqueta="Categoría">
          <select id="p-categoria" className="control" value={form.id_categoria} required
            onChange={(e) => setForm({ ...form, id_categoria: e.target.value })}>
            <option value="" disabled>Elige una</option>
            {categorias.map((c) => <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>)}
          </select>
        </Campo>
        <Campo id="p-condicion" etiqueta="Condición">
          <select id="p-condicion" className="control" value={form.condicion}
            onChange={(e) => setForm({ ...form, condicion: e.target.value as Condicion })}>
            <option value="nueva">Nueva</option>
            <option value="reacondicionada">Reacondicionada</option>
          </select>
        </Campo>
      </div>
      <Campo id="p-precio" etiqueta="Precio de venta" ayuda={pieza ? undefined : "El stock empieza en 0: se suma al registrar entradas."}>
        <input id="p-precio" className="control cifras" type="number" min="0" step="0.01" required
          value={form.precio_venta} onChange={(e) => setForm({ ...form, precio_venta: e.target.value })} />
      </Campo>
      <Campo id="p-descripcion" etiqueta="Descripción (opcional)">
        <textarea id="p-descripcion" className="control" value={form.descripcion}
          onChange={(e) => setForm({ ...form, descripcion: e.target.value })} />
      </Campo>
      <Aviso texto={error} />
      <div className="pie-dialogo">
        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? "Guardando…" : pieza ? "Guardar cambios" : "Crear pieza"}
        </button>
      </div>
    </form>
  );
}

function FormLote({
  pieza,
  proveedores,
  alGuardar,
}: {
  pieza: Pieza;
  proveedores: Proveedor[];
  alGuardar: (cantidad: number) => void;
}) {
  const [form, setForm] = useState({ id_proveedor: "", cantidad: "1", costo_unitario: "" });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const cantidad = Math.max(0, Math.floor(Number(form.cantidad) || 0));

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      await enviar("/lotes/", "POST", {
        id_pieza: pieza.id_pieza,
        id_proveedor: Number(form.id_proveedor),
        cantidad,
        costo_unitario: form.costo_unitario,
      });
      alGuardar(cantidad);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar la entrada.");
      setEnviando(false);
    }
  }

  return (
    <form className="formulario" onSubmit={guardar}>
      <p className="secundario">{pieza.nombre}</p>
      <Campo id="l-proveedor" etiqueta="Proveedor">
        <select id="l-proveedor" className="control" value={form.id_proveedor} required
          onChange={(e) => setForm({ ...form, id_proveedor: e.target.value })}>
          <option value="" disabled>Elige uno</option>
          {proveedores.map((p) => <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>)}
        </select>
      </Campo>
      <div className="fila-campos">
        <Campo id="l-cantidad" etiqueta="Unidades recibidas">
          <input id="l-cantidad" className="control cifras" type="number" min="1" step="1" required
            value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: e.target.value })} />
        </Campo>
        <Campo id="l-costo" etiqueta="Costo unitario">
          <input id="l-costo" className="control cifras" type="number" min="0" step="0.01" required
            value={form.costo_unitario} onChange={(e) => setForm({ ...form, costo_unitario: e.target.value })} />
        </Campo>
      </div>
      <p className="pequeno">
        Stock: <span className="cifras">{pieza.stock_actual}</span> → <strong className="cifras">{pieza.stock_actual + cantidad}</strong> unidades
        {Number(form.costo_unitario) > 0 && cantidad > 0 && (
          <> · costo total <span className="cifras">{precio(Number(form.costo_unitario) * cantidad)}</span></>
        )}
      </p>
      <Aviso texto={error} />
      <div className="pie-dialogo">
        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? "Registrando…" : "Registrar entrada"}
        </button>
      </div>
    </form>
  );
}
