"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

import BuscadorCliente from "../../../../components/BuscadorCliente";
import { Paginador, usePaginacion } from "../../../../components/Paginador";
import { Aviso, Campo, Dialogo, Encabezado, EstadoCarga } from "../../../../components/ui";
import { enviar, type Categoria, type Cliente, type MetodoPago, type Pieza, type Venta } from "../../../../lib/api";
import { estadoStock, normalizar, NOMBRE_CONDICION, NOMBRE_PAGO, precio } from "../../../../lib/formato";
import { useRequiereSesion } from "../../../../lib/session";
import { useDatos } from "../../../../lib/useDatos";

type Linea = { pieza: Pieza; cantidad: number };

export default function NuevaVentaPage() {
  const usuario = useRequiereSesion(["administrador", "vendedor"]);

  const piezas = useDatos<Pieza[]>(usuario ? "/piezas/" : null);
  const categorias = useDatos<Categoria[]>("/categorias/");
  const clientes = useDatos<Cliente[]>(usuario ? "/clientes/" : null);

  const [busqueda, setBusqueda] = useState("");
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [categoria, setCategoria] = useState("");
  const [soloDisponibles, setSoloDisponibles] = useState(true);
  const [clienteId, setClienteId] = useState("");
  const [metodo, setMetodo] = useState<MetodoPago>("efectivo");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [registrada, setRegistrada] = useState<Venta | null>(null);
  const [nuevoCliente, setNuevoCliente] = useState<string | null>(null);

  const nombreCategoria = useMemo(() => {
    const mapa = new Map((categorias.datos ?? []).map((c) => [c.id_categoria, c.nombre]));
    return (id: number) => mapa.get(id) ?? "";
  }, [categorias.datos]);

  const resultados = useMemo(() => {
    const palabras = normalizar(busqueda.trim()).split(/\s+/).filter(Boolean);
    return (piezas.datos ?? [])
      .filter((p) => !categoria || String(p.id_categoria) === categoria)
      .filter((p) => !soloDisponibles || p.stock_actual > 0)
      .filter((p) => {
        const texto = normalizar(`${p.nombre} ${p.marca ?? ""} ${nombreCategoria(p.id_categoria)}`);
        return palabras.every((w) => texto.includes(w));
      })
      .sort((a, b) => Number(b.stock_actual > 0) - Number(a.stock_actual > 0));
  }, [piezas.datos, busqueda, categoria, soloDisponibles, nombreCategoria]);

  const paginas = usePaginacion(resultados, 8, `${busqueda}|${categoria}|${soloDisponibles}`);
  const cliente = clientes.datos?.find((c) => String(c.id_cliente) === clienteId) ?? null;

  const total = lineas.reduce((t, l) => t + Number(l.pieza.precio_venta) * l.cantidad, 0);
  const unidades = lineas.reduce((t, l) => t + l.cantidad, 0);

  function agregar(pieza: Pieza) {
    setLineas((actual) => {
      const existente = actual.find((l) => l.pieza.id_pieza === pieza.id_pieza);
      if (existente) {
        return actual.map((l) =>
          l.pieza.id_pieza === pieza.id_pieza ? { ...l, cantidad: Math.min(l.cantidad + 1, pieza.stock_actual) } : l
        );
      }
      return [...actual, { pieza, cantidad: 1 }];
    });
  }

  function cambiarCantidad(id: number, valor: string) {
    setLineas((actual) =>
      actual.map((l) =>
        l.pieza.id_pieza === id
          ? { ...l, cantidad: Math.max(1, Math.min(Math.floor(Number(valor) || 1), l.pieza.stock_actual)) }
          : l
      )
    );
  }

  async function registrar(e: FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      const venta = await enviar<Venta>("/ventas/", "POST", {
        id_cliente: Number(clienteId),
        metodo_pago: metodo,
        detalles: lineas.map((l) => ({ id_pieza: l.pieza.id_pieza, cantidad: l.cantidad })),
      });
      setRegistrada(venta);
      setLineas([]);
      setClienteId("");
      setBusqueda("");
      piezas.recargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar la venta.");
      piezas.recargar(); // el stock pudo cambiar mientras tanto
    } finally {
      setEnviando(false);
    }
  }

  if (!usuario) return null;

  if (registrada) {
    const cliente = clientes.datos?.find((c) => c.id_cliente === registrada.id_cliente);
    return (
      <section className="panel venta-lista aparece">
        <h2>Venta N.º {registrada.id_venta} registrada</h2>
        <p>
          {cliente ? `${cliente.nombres} ${cliente.apellidos}` : "Cliente"} · {NOMBRE_PAGO[registrada.metodo_pago]} ·{" "}
          <strong className="cifras">{precio(registrada.total)}</strong>
        </p>
        <p className="secundario pequeno" style={{ marginTop: 6 }}>
          {registrada.detalles.map((d) => `${d.cantidad} × ${d.pieza_nombre}`).join(" · ")}
        </p>
        <div className="acciones">
          <button type="button" className="boton" onClick={() => setRegistrada(null)}>Registrar otra venta</button>
          <Link href="/ventas" className="boton secundario">Ver ventas</Link>
        </div>
      </section>
    );
  }

  return (
    <>
      <Encabezado titulo="Registrar venta" descripcion="Agrega las piezas, elige el cliente y el método de pago.">
        <Link href="/ventas" className="boton secundario">Volver a ventas</Link>
      </Encabezado>

      <div className="nueva-venta">
        <section>
          <div className="filtros">
            <label className="visualmente-oculto" htmlFor="buscar">Buscar pieza</label>
            <input id="buscar" className="control buscar" type="search" autoFocus
              placeholder="Buscar pieza: Ryzen, RTX 4060, SSD…" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
            <label className="visualmente-oculto" htmlFor="f-categoria">Categoría</label>
            <select id="f-categoria" className="control" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
              <option value="">Todas las categorías</option>
              {categorias.datos?.map((c) => <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>)}
            </select>
            <label className="interruptor pequeno">
              <input type="checkbox" checked={soloDisponibles} onChange={(e) => setSoloDisponibles(e.target.checked)} />
              Solo con stock
            </label>
          </div>
          <div className="panel">
            <EstadoCarga cargando={piezas.cargando} error={piezas.error}
              vacio={!!piezas.datos && resultados.length === 0} textoVacio="Ninguna pieza coincide con la búsqueda." />
            <ul className="lista-simple catalogo-venta">
              {paginas.visibles.map((p) => {
                const enVenta = lineas.find((l) => l.pieza.id_pieza === p.id_pieza)?.cantidad ?? 0;
                const quedan = p.stock_actual - enVenta;
                const e = estadoStock(p.stock_actual);
                return (
                  <li key={p.id_pieza}>
                    <span>
                      <span className="titulo">{p.nombre}</span>
                      <span className="secundario pequeno" style={{ display: "block" }}>
                        {nombreCategoria(p.id_categoria)} · {NOMBRE_CONDICION[p.condicion]} ·{" "}
                        <span className={e.clase === "ok" ? undefined : `etiqueta ${e.clase}`}>
                          {p.stock_actual === 0 ? "Agotada" : `${p.stock_actual} en tienda`}
                        </span>
                      </span>
                    </span>
                    <span className="cifras">{precio(p.precio_venta)}</span>
                    <button type="button" className="boton secundario" disabled={quedan <= 0}
                      onClick={() => agregar(p)} aria-label={`Agregar ${p.nombre}`}>
                      {enVenta > 0 ? `Agregar (${enVenta})` : "Agregar"}
                    </button>
                  </li>
                );
              })}
            </ul>
            <Paginador p={paginas} nombre="piezas" tamanos={[8, 16, 32]} />
          </div>
        </section>

        <form className="panel resumen-venta" onSubmit={registrar}>
          <div className="bloque">
            <h2>Piezas</h2>
            {lineas.length === 0 ? (
              <p className="secundario pequeno">Todavía no hay piezas en esta venta.</p>
            ) : (
              <ul className="lineas-venta">
                {lineas.map((l) => (
                  <li key={l.pieza.id_pieza}>
                    <span className="pequeno">
                      {l.pieza.nombre}
                      <span className="secundario" style={{ display: "block" }}>
                        {precio(l.pieza.precio_venta)} c/u ·{" "}
                        <button type="button" className="boton-texto peligro pequeno"
                          onClick={() => setLineas(lineas.filter((x) => x.pieza.id_pieza !== l.pieza.id_pieza))}>
                          Quitar
                        </button>
                      </span>
                    </span>
                    <input className="control cifras" type="number" min={1} max={l.pieza.stock_actual}
                      value={l.cantidad} aria-label={`Unidades de ${l.pieza.nombre}`}
                      onChange={(e) => cambiarCantidad(l.pieza.id_pieza, e.target.value)} />
                    <span className="cifras pequeno">{precio(Number(l.pieza.precio_venta) * l.cantidad)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="bloque">
            <Campo id="cliente" etiqueta="Cliente">
              <BuscadorCliente
                clientes={clientes.datos ?? []}
                seleccionado={cliente}
                alElegir={(c) => setClienteId(c ? String(c.id_cliente) : "")}
                alCrear={(texto) => setNuevoCliente(texto)}
              />
            </Campo>
            {!cliente && (
              <p className="pequeno" style={{ marginTop: 8 }}>
                ¿Es nuevo?{" "}
                <button type="button" className="boton-texto" onClick={() => setNuevoCliente("")}>Registrar cliente</button>
              </p>
            )}
          </div>

          <div className="bloque">
            <fieldset style={{ border: 0 }}>
              <legend className="pequeno" style={{ fontWeight: 500, marginBottom: 6 }}>Método de pago</legend>
              <div className="opciones-pago">
                {(Object.keys(NOMBRE_PAGO) as MetodoPago[]).map((m) => (
                  <label key={m}>
                    <input type="radio" name="metodo" value={m} checked={metodo === m} onChange={() => setMetodo(m)} />
                    {NOMBRE_PAGO[m]}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>

          <div className="bloque">
            <div className="total-venta">
              <span className="secundario">{unidades === 1 ? "1 unidad" : `${unidades} unidades`}</span>
              <strong>{precio(total)}</strong>
            </div>
            <Aviso texto={error} />
            <button type="submit" className="boton bloque" style={{ marginTop: error ? 12 : 0 }}
              disabled={enviando || lineas.length === 0 || !clienteId}>
              {enviando ? "Registrando…" : "Registrar venta"}
            </button>
          </div>
        </form>
      </div>

      <Dialogo abierto={nuevoCliente !== null} titulo="Registrar cliente" alCerrar={() => setNuevoCliente(null)}>
        <FormClienteRapido
          texto={nuevoCliente ?? ""}
          alGuardar={(c) => {
            setNuevoCliente(null);
            clientes.recargar();
            setClienteId(String(c.id_cliente));
          }}
        />
      </Dialogo>
    </>
  );
}

/** Lo escrito en el buscador se aprovecha: dígitos → documento; palabras → nombres y apellidos. */
function datosIniciales(texto: string) {
  const limpio = texto.trim();
  if (/^\d[\d\s.-]*$/.test(limpio)) return { nombres: "", apellidos: "", documento: limpio.replace(/\D/g, "") };
  const [nombres = "", ...resto] = limpio.split(/\s+/);
  return { nombres, apellidos: resto.join(" "), documento: "" };
}

function FormClienteRapido({ texto, alGuardar }: { texto: string; alGuardar: (c: Cliente) => void }) {
  const [form, setForm] = useState({ ...datosIniciales(texto), telefono: "", email: "" });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      const cliente = await enviar<Cliente>("/clientes/", "POST", {
        ...form,
        documento: form.documento || null,
        telefono: form.telefono || null,
        email: form.email || null,
      });
      alGuardar(cliente);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar el cliente.");
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
        <button type="submit" className="boton" disabled={enviando}>{enviando ? "Guardando…" : "Registrar y usar en la venta"}</button>
      </div>
    </form>
  );
}
