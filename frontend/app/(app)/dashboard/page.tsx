"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Encabezado, EstadoCarga } from "../../../components/ui";
import type { Cliente, Me, Pieza, PiezaPublica, Venta } from "../../../lib/api";
import { estadoStock, fechaConHora, marcaDeTiempo, normalizar, NOMBRE_CONDICION, precio, STOCK_BAJO } from "../../../lib/formato";
import { useSession } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

export default function InicioPage() {
  const { usuario } = useSession();
  if (!usuario) return null;
  return usuario.rol === "cliente" ? <Catalogo usuario={usuario} /> : <Resumen usuario={usuario} />;
}

// ---------------------------------------------------------------------------
// Empleados: cómo va el día y qué hay que reponer
// ---------------------------------------------------------------------------

const DIA = 24 * 60 * 60 * 1000;

function Resumen({ usuario }: { usuario: Me }) {
  const ventas = useDatos<Venta[]>("/ventas/");
  const piezas = useDatos<Pieza[]>("/piezas/");
  const clientes = useDatos<Cliente[]>("/clientes/");

  const cifras = useMemo(() => {
    if (!ventas.datos || !piezas.datos) return null;
    const activas = ventas.datos.filter((v) => v.estado === "activa");
    const inicioHoy = new Date();
    inicioHoy.setHours(0, 0, 0, 0);
    const hoy = activas.filter((v) => marcaDeTiempo(v.fecha) >= inicioHoy.getTime());
    const semana = activas.filter((v) => marcaDeTiempo(v.fecha) >= inicioHoy.getTime() - 6 * DIA);
    const suma = (lista: Venta[]) => lista.reduce((t, v) => t + Number(v.total), 0);
    return {
      hoy: { cantidad: hoy.length, total: suma(hoy) },
      semana: { cantidad: semana.length, total: suma(semana) },
      bajo: piezas.datos.filter((p) => p.stock_actual > 0 && p.stock_actual <= STOCK_BAJO).length,
      agotadas: piezas.datos.filter((p) => p.stock_actual <= 0).length,
    };
  }, [ventas.datos, piezas.datos]);

  const porReponer = useMemo(
    () =>
      (piezas.datos ?? [])
        .filter((p) => p.stock_actual <= STOCK_BAJO)
        .sort((a, b) => a.stock_actual - b.stock_actual)
        .slice(0, 8),
    [piezas.datos]
  );

  const nombreCliente = useMemo(() => {
    const mapa = new Map((clientes.datos ?? []).map((c) => [c.id_cliente, `${c.nombres} ${c.apellidos}`]));
    return (id: number) => mapa.get(id) ?? `Cliente ${id}`;
  }, [clientes.datos]);

  const ultimas = (ventas.datos ?? []).slice(0, 6);
  const nombre = usuario.nombres.split(" ")[0] || usuario.username;

  return (
    <>
      <Encabezado titulo={`Hola, ${nombre}`} descripcion="Así va la tienda hoy.">
        <Link href="/ventas/nueva" className="boton">Registrar venta</Link>
      </Encabezado>

      {cifras ? (
        <section className="cifras-resumen aparece" aria-label="Resumen">
          <div className="cifra">
            <span className="valor cifras">{precio(cifras.hoy.total)}</span>
            <span className="nombre">Vendido hoy</span>
            <span className="detalle">{cifras.hoy.cantidad === 1 ? "1 venta" : `${cifras.hoy.cantidad} ventas`}</span>
          </div>
          <div className="cifra">
            <span className="valor cifras">{precio(cifras.semana.total)}</span>
            <span className="nombre">Últimos 7 días</span>
            <span className="detalle">{cifras.semana.cantidad === 1 ? "1 venta" : `${cifras.semana.cantidad} ventas`}</span>
          </div>
          <div className={cifras.bajo > 0 ? "cifra alerta" : "cifra"}>
            <span className="valor cifras">{cifras.bajo}</span>
            <span className="nombre">Con stock bajo</span>
            <span className="detalle">{STOCK_BAJO} unidades o menos</span>
          </div>
          <div className="cifra">
            <span className="valor cifras">{cifras.agotadas}</span>
            <span className="nombre">Agotadas</span>
            <span className="detalle">Sin unidades en tienda</span>
          </div>
        </section>
      ) : (
        <EstadoCarga cargando={ventas.cargando || piezas.cargando} error={ventas.error || piezas.error} />
      )}

      <div className="columnas">
        <section className="seccion">
          <h2>Para reponer</h2>
          <div className="panel">
            <EstadoCarga
              cargando={piezas.cargando}
              error={piezas.error}
              vacio={!!piezas.datos && porReponer.length === 0}
              textoVacio="Todas las piezas tienen más de 3 unidades."
            />
            {porReponer.length > 0 && (
              <ul className="lista-simple">
                {porReponer.map((p) => {
                  const estado = estadoStock(p.stock_actual);
                  return (
                    <li key={p.id_pieza}>
                      <span>
                        <span className="titulo">{p.nombre}</span>
                        <span className="sub secundario pequeno" style={{ display: "block" }}>
                          {NOMBRE_CONDICION[p.condicion]}
                        </span>
                      </span>
                      <span className={`etiqueta ${estado.clase} cifras`}>
                        {p.stock_actual === 0 ? "Agotada" : `${p.stock_actual} ud.`}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>

        <section className="seccion">
          <h2>Últimas ventas</h2>
          <div className="tabla-contenedor">
            <EstadoCarga cargando={ventas.cargando} error={ventas.error} vacio={ventas.datos?.length === 0} textoVacio="Todavía no hay ventas." />
            {ultimas.length > 0 && (
              <table style={{ minWidth: 520 }}>
                <thead>
                  <tr>
                    <th>Venta</th>
                    <th>Cliente</th>
                    <th className="num">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {ultimas.map((v) => (
                    <tr key={v.id_venta} className={v.estado === "anulada" ? "anulada" : undefined}>
                      <td>
                        <span className="principal-celda cifras">N.º {v.id_venta}</span>
                        <span className="sub">{fechaConHora(v.fecha)}</span>
                      </td>
                      <td>
                        {nombreCliente(v.id_cliente)}
                        {v.estado === "anulada" && <span className="sub">Anulada</span>}
                      </td>
                      <td className="num">{precio(v.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <p className="pequeno" style={{ marginTop: 10 }}>
            <Link href="/ventas" className="boton-texto">Ver todas las ventas</Link>
          </p>
        </section>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Clientes: catálogo con precios, agrupado por categoría
// ---------------------------------------------------------------------------

function Catalogo({ usuario }: { usuario: Me }) {
  const piezas = useDatos<PiezaPublica[]>("/piezas/");
  const [busqueda, setBusqueda] = useState("");
  const [soloDisponibles, setSoloDisponibles] = useState(true);

  const grupos = useMemo(() => {
    const q = normalizar(busqueda.trim());
    const filtradas = (piezas.datos ?? []).filter(
      (p) =>
        (!soloDisponibles || p.en_stock) &&
        (!q || normalizar(`${p.nombre} ${p.categoria_nombre} ${p.descripcion ?? ""}`).includes(q))
    );
    const mapa = new Map<string, PiezaPublica[]>();
    for (const p of filtradas) {
      mapa.set(p.categoria_nombre, [...(mapa.get(p.categoria_nombre) ?? []), p]);
    }
    return [...mapa.entries()].sort(([a], [b]) => a.localeCompare(b, "es"));
  }, [piezas.datos, busqueda, soloDisponibles]);

  const nombre = usuario.nombres.split(" ")[0] || usuario.username;

  return (
    <>
      <Encabezado
        titulo="Catálogo"
        descripcion={`Hola, ${nombre}. Precios actualizados de las piezas en tienda; para comprar, acércate o escríbenos.`}
      />

      <div className="filtros">
        <label className="visualmente-oculto" htmlFor="buscar">Buscar en el catálogo</label>
        <input
          id="buscar"
          className="control buscar"
          type="search"
          placeholder="Buscar: RTX, DDR5, 750W…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
        />
        <label className="control" style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input type="checkbox" checked={soloDisponibles} onChange={(e) => setSoloDisponibles(e.target.checked)} style={{ accentColor: "var(--acento)" }} />
          Solo disponibles
        </label>
      </div>

      <EstadoCarga
        cargando={piezas.cargando}
        error={piezas.error}
        vacio={!!piezas.datos && grupos.length === 0}
        textoVacio="No hay piezas que coincidan con la búsqueda."
      />

      <div className="catalogo">
        {grupos.map(([categoria, lista]) => (
          <section key={categoria} className="catalogo-grupo">
            <h2>{categoria}</h2>
            <ul className="lista-simple panel">
              {lista.map((p) => (
                <li key={p.id_pieza}>
                  <span>
                    <span className="titulo">{p.nombre}</span>
                    {p.descripcion && <span className="secundario pequeno" style={{ display: "block" }}>{p.descripcion}</span>}
                  </span>
                  <span className="etiqueta">
                    {p.en_stock ? NOMBRE_CONDICION[p.condicion] : "Agotada"}
                  </span>
                  <span className="precio">{precio(p.precio_venta)}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </>
  );
}
