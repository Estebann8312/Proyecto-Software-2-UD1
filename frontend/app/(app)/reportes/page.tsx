"use client";

import { FormEvent, useMemo, useState } from "react";

import { Encabezado, EstadoCarga } from "../../../components/ui";
import type { Reporte } from "../../../lib/api";
import { fecha, fechaConHora, NOMBRE_CONDICION, NOMBRE_PAGO, precio } from "../../../lib/formato";
import { useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

// ---------------------------------------------------------------------------
// Rango de fechas
// ---------------------------------------------------------------------------

/** Fecha local en formato AAAA-MM-DD (sin pasar por UTC). */
function iso(d: Date) {
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

type Rango = { desde: string; hasta: string };

const ATAJOS: { id: string; texto: string; rango: () => Rango }[] = [
  {
    id: "7",
    texto: "7 días",
    rango: () => {
      const hoy = new Date();
      const desde = new Date(hoy);
      desde.setDate(hoy.getDate() - 6);
      return { desde: iso(desde), hasta: iso(hoy) };
    },
  },
  {
    id: "30",
    texto: "30 días",
    rango: () => {
      const hoy = new Date();
      const desde = new Date(hoy);
      desde.setDate(hoy.getDate() - 29);
      return { desde: iso(desde), hasta: iso(hoy) };
    },
  },
  {
    id: "mes",
    texto: "Este mes",
    rango: () => {
      const hoy = new Date();
      return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: iso(hoy) };
    },
  },
  {
    id: "mes-anterior",
    texto: "Mes anterior",
    rango: () => {
      const hoy = new Date();
      return {
        desde: iso(new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)),
        hasta: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 0)),
      };
    },
  },
  {
    id: "anio",
    texto: "Este año",
    rango: () => {
      const hoy = new Date();
      return { desde: iso(new Date(hoy.getFullYear(), 0, 1)), hasta: iso(hoy) };
    },
  },
];

// ---------------------------------------------------------------------------
// Formatos propios del informe
// ---------------------------------------------------------------------------

function porcentaje(valor: number | null) {
  return valor === null ? "—" : `${valor.toLocaleString("es-CO", { maximumFractionDigits: 1 })} %`;
}

function numero(valor: number) {
  return valor.toLocaleString("es-CO");
}

/** "+12,5 % vs. periodo anterior", con clase según si sube o baja. */
function Variacion({ valor }: { valor: number | null }) {
  if (valor === null) return <span className="detalle">Sin datos del periodo anterior</span>;
  const clase = valor > 0 ? "sube" : valor < 0 ? "baja" : "";
  const signo = valor > 0 ? "+" : "";
  return (
    <span className={`detalle variacion ${clase}`}>
      {signo}
      {porcentaje(valor)} vs. periodo anterior
    </span>
  );
}

// ---------------------------------------------------------------------------
// Exportación a CSV (se abre en Excel con tildes y separador ";")
// ---------------------------------------------------------------------------

function celda(valor: string | number | null | undefined) {
  const texto = valor === null || valor === undefined ? "" : String(valor);
  return /[";\n]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
}

/** Pesos enteros: Excel en español confunde el punto decimal con miles. */
function pesos(valor: string | null) {
  return valor === null ? "" : Math.round(Number(valor)).toString();
}

function descargarCsv(r: Reporte) {
  const filas: (string | number | null)[][] = [];
  const seccion = (titulo: string, encabezados: string[], datos: (string | number | null)[][]) => {
    filas.push([titulo], encabezados, ...datos, []);
  };

  filas.push(["Informe PC Stock"], ["Desde", r.rango.desde], ["Hasta", r.rango.hasta], ["Moneda", r.moneda], []);
  const s = r.resumen;
  seccion("Resumen", ["Indicador", "Valor"], [
    ["Ingresos", pesos(s.ingresos)],
    ["Ventas", s.ventas],
    ["Ticket promedio", pesos(s.ticket_promedio)],
    ["Unidades vendidas", s.unidades_vendidas],
    ["Clientes distintos", s.clientes_distintos],
    ["Costo estimado", pesos(s.costo_estimado)],
    ["Utilidad estimada", pesos(s.utilidad_estimada)],
    ["Margen estimado (%)", s.margen],
    ["Ingresos sin costo conocido", pesos(s.ingresos_sin_costo)],
    ["Ventas anuladas", s.anuladas],
    ["Monto anulado", pesos(s.monto_anulado)],
    ["Ingresos periodo anterior", pesos(s.ingresos_anterior)],
    ["Variación de ingresos (%)", s.variacion_ingresos],
  ]);
  seccion("Ventas por día", ["Fecha", "Ventas", "Ingresos"], r.por_dia.map((d) => [d.fecha, d.ventas, pesos(d.ingresos)]));
  seccion("Por categoría", ["Categoría", "Unidades", "Ingresos", "Utilidad estimada", "Margen (%)", "Participación (%)"],
    r.por_categoria.map((c) => [c.categoria, c.unidades, pesos(c.ingresos), pesos(c.utilidad_estimada), c.margen, c.porcentaje]));
  seccion("Por método de pago", ["Método", "Ventas", "Ingresos", "Participación (%)"],
    r.por_metodo_pago.map((m) => [NOMBRE_PAGO[m.metodo], m.ventas, pesos(m.ingresos), m.porcentaje]));
  seccion("Por vendedor", ["Vendedor", "Ventas", "Ingresos", "Ticket promedio", "Participación (%)"],
    r.por_vendedor.map((v) => [v.nombre, v.ventas, pesos(v.ingresos), pesos(v.ticket_promedio), v.porcentaje]));
  seccion("Piezas más vendidas", ["Pieza", "Categoría", "Condición", "Unidades", "Ingresos", "Utilidad estimada", "Margen (%)"],
    r.top_piezas.map((p) => [p.nombre, p.categoria, NOMBRE_CONDICION[p.condicion], p.unidades, pesos(p.ingresos), pesos(p.utilidad_estimada), p.margen]));
  seccion("Mejores clientes", ["Cliente", "Compras", "Ingresos", "Última compra"],
    r.top_clientes.map((c) => [c.nombre, c.compras, pesos(c.ingresos), c.ultima_compra.slice(0, 10)]));
  seccion("Compras a proveedores", ["Proveedor", "Lotes", "Unidades", "Monto"],
    r.compras.por_proveedor.map((p) => [p.proveedor, p.lotes, p.unidades, pesos(p.monto)]));
  seccion("Inventario actual", ["Indicador", "Valor"], [
    ["Referencias", r.inventario.referencias],
    ["Unidades en stock", r.inventario.unidades],
    ["Valor a costo", pesos(r.inventario.valor_costo)],
    ["Valor a precio de venta", pesos(r.inventario.valor_venta)],
    ["Utilidad potencial", pesos(r.inventario.utilidad_potencial)],
    ["Agotadas", r.inventario.agotadas],
    ["Con stock bajo", r.inventario.stock_bajo],
  ]);
  seccion("Piezas para reponer", ["Pieza", "Categoría", "Stock", "Precio"],
    r.inventario.criticas.map((p) => [p.nombre, p.categoria, p.stock, pesos(p.precio_venta)]));
  seccion("Piezas sin ventas en el periodo", ["Pieza", "Categoría", "Stock", "Valor en stock"],
    r.inventario.sin_movimiento.map((p) => [p.nombre, p.categoria, p.stock, pesos(p.valor_venta)]));

  const contenido = "﻿" + filas.map((f) => f.map(celda).join(";")).join("\r\n");
  const url = URL.createObjectURL(new Blob([contenido], { type: "text/csv;charset=utf-8" }));
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = `informe-pcstock_${r.rango.desde}_${r.rango.hasta}.csv`;
  enlace.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Gráficos (una sola serie, en el color del acento)
// ---------------------------------------------------------------------------

/** Ingresos por día: columnas con el valor al pasar el cursor o enfocar. */
function GraficoDiario({ dias }: { dias: Reporte["por_dia"] }) {
  const maximo = Math.max(...dias.map((d) => Number(d.ingresos)), 0);
  const medio = dias[Math.floor((dias.length - 1) / 2)];
  return (
    <figure className="grafico-diario">
      <div className="grafico-area" role="list" aria-label="Ingresos por día">
        <span className="grafico-max cifras">{maximo > 0 ? precio(maximo) : "Sin ventas"}</span>
        {dias.map((d) => {
          const alto = maximo > 0 ? (Number(d.ingresos) / maximo) * 100 : 0;
          return (
            <div key={d.fecha} className="columna" role="listitem" tabIndex={0}
              aria-label={`${fecha(d.fecha)}: ${precio(d.ingresos)} en ${d.ventas} ventas`}>
              <span className="barra" style={{ height: `${Math.max(alto, Number(d.ingresos) > 0 ? 2 : 0)}%` }} />
              <span className="tip cifras" aria-hidden="true">
                <strong>{fecha(d.fecha)}</strong>
                {precio(d.ingresos)} · {d.ventas === 1 ? "1 venta" : `${d.ventas} ventas`}
              </span>
            </div>
          );
        })}
      </div>
      <figcaption className="grafico-eje">
        <span>{fecha(dias[0].fecha)}</span>
        {dias.length > 2 && <span>{fecha(medio.fecha)}</span>}
        <span>{fecha(dias[dias.length - 1].fecha)}</span>
      </figcaption>
    </figure>
  );
}

/** Lista con barra de participación: nombre, barra y valores en texto. */
function Barras({ filas }: { filas: { clave: string; nombre: string; valor: string; detalle: string; parte: number | null }[] }) {
  if (filas.length === 0) return <p className="vacio">Sin ventas en este periodo.</p>;
  const maximo = Math.max(...filas.map((f) => f.parte ?? 0), 1);
  return (
    <ul className="barras">
      {filas.map((f) => (
        <li key={f.clave}>
          <div className="barras-texto">
            <span className="titulo">{f.nombre}</span>
            <span className="cifras">{f.valor}</span>
          </div>
          <div className="barras-pista" aria-hidden="true">
            <span style={{ width: `${((f.parte ?? 0) / maximo) * 100}%` }} />
          </div>
          <span className="sub secundario pequeno cifras">{f.detalle}</span>
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Página
// ---------------------------------------------------------------------------

export default function ReportesPage() {
  const usuario = useRequiereSesion(["administrador"]);

  const inicial = ATAJOS[1].rango();
  const [rango, setRango] = useState<Rango>(inicial);
  const [borrador, setBorrador] = useState<Rango>(inicial);
  const [atajo, setAtajo] = useState("30");

  const endpoint = usuario ? `/reportes/?desde=${rango.desde}&hasta=${rango.hasta}` : null;
  const reporte = useDatos<Reporte>(endpoint);
  const r = reporte.datos;

  function elegirAtajo(id: string) {
    const nuevo = ATAJOS.find((a) => a.id === id)!.rango();
    setAtajo(id);
    setBorrador(nuevo);
    setRango(nuevo);
  }

  function aplicar(e: FormEvent) {
    e.preventDefault();
    setAtajo("");
    setRango(borrador);
  }

  const sinVentas = r?.resumen.ventas === 0;

  const categorias = useMemo(
    () =>
      (r?.por_categoria ?? []).map((c) => ({
        clave: c.categoria,
        nombre: c.categoria,
        valor: precio(c.ingresos),
        parte: c.porcentaje,
        detalle: `${porcentaje(c.porcentaje)} de los ingresos · ${numero(c.unidades)} ud. · margen ${porcentaje(c.margen)}`,
      })),
    [r]
  );

  const metodos = useMemo(
    () =>
      (r?.por_metodo_pago ?? []).map((m) => ({
        clave: m.metodo,
        nombre: NOMBRE_PAGO[m.metodo],
        valor: precio(m.ingresos),
        parte: m.porcentaje,
        detalle: `${porcentaje(m.porcentaje)} · ${m.ventas === 1 ? "1 venta" : `${m.ventas} ventas`}`,
      })),
    [r]
  );

  if (!usuario) return null;

  return (
    <>
      <Encabezado
        titulo="Reportes"
        descripcion={
          r
            ? `Del ${fecha(r.rango.desde)} al ${fecha(r.rango.hasta)} · ${r.rango.dias} días · generado ${fechaConHora(r.generado)}`
            : "Ventas, utilidad, inventario y compras del periodo que elijas."
        }
      >
        <button type="button" className="boton secundario" disabled={!r} onClick={() => r && descargarCsv(r)}>
          Descargar CSV
        </button>
        <button type="button" className="boton" disabled={!r} onClick={() => window.print()}>
          Imprimir o PDF
        </button>
      </Encabezado>

      <form className="filtros-reporte" onSubmit={aplicar}>
        <div className="segmentado" role="group" aria-label="Periodo">
          {ATAJOS.map((a) => (
            <button key={a.id} type="button" aria-pressed={atajo === a.id} onClick={() => elegirAtajo(a.id)}>
              {a.texto}
            </button>
          ))}
        </div>
        <div className="rango-personalizado">
          <label className="visualmente-oculto" htmlFor="desde">Desde</label>
          <input id="desde" className="control cifras" type="date" required max={borrador.hasta}
            value={borrador.desde} onChange={(e) => setBorrador({ ...borrador, desde: e.target.value })} />
          <span className="secundario">a</span>
          <label className="visualmente-oculto" htmlFor="hasta">Hasta</label>
          <input id="hasta" className="control cifras" type="date" required min={borrador.desde}
            value={borrador.hasta} onChange={(e) => setBorrador({ ...borrador, hasta: e.target.value })} />
          <button type="submit" className="boton secundario">Aplicar</button>
        </div>
      </form>

      <EstadoCarga cargando={reporte.cargando && !r} error={reporte.error} />

      {r && (
        <div className={reporte.cargando ? "informe actualizando" : "informe"}>
          <p className="solo-impresion">
            Informe PC Stock · del {fecha(r.rango.desde)} al {fecha(r.rango.hasta)} · valores en pesos colombianos (COP)
          </p>

          {/* ------------------------------------------------ Indicadores */}
          <section className="cifras-resumen" aria-label="Indicadores principales">
            <div className="cifra">
              <span className="valor cifras">{precio(r.resumen.ingresos)}</span>
              <span className="nombre">Ingresos</span>
              <Variacion valor={r.resumen.variacion_ingresos} />
            </div>
            <div className="cifra">
              <span className="valor cifras">{numero(r.resumen.ventas)}</span>
              <span className="nombre">Ventas</span>
              <Variacion valor={r.resumen.variacion_ventas} />
            </div>
            <div className="cifra">
              <span className="valor cifras">{precio(r.resumen.ticket_promedio)}</span>
              <span className="nombre">Ticket promedio</span>
              <span className="detalle">{numero(r.resumen.unidades_vendidas)} unidades vendidas</span>
            </div>
            <div className="cifra">
              <span className="valor cifras">{precio(r.resumen.utilidad_estimada)}</span>
              <span className="nombre">Utilidad estimada</span>
              <span className="detalle">Margen {porcentaje(r.resumen.margen)}</span>
            </div>
          </section>

          <section className="indicadores-secundarios" aria-label="Otros indicadores">
            <div>
              <span className="secundario pequeno">Clientes distintos</span>
              <strong className="cifras">{numero(r.resumen.clientes_distintos)}</strong>
            </div>
            <div>
              <span className="secundario pequeno">Costo estimado de lo vendido</span>
              <strong className="cifras">{precio(r.resumen.costo_estimado)}</strong>
            </div>
            <div>
              <span className="secundario pequeno">Ventas anuladas</span>
              <strong className="cifras">
                {numero(r.resumen.anuladas)}
                {r.resumen.anuladas > 0 && <span className="secundario"> · {precio(r.resumen.monto_anulado)}</span>}
              </strong>
            </div>
            <div>
              <span className="secundario pequeno">Compras a proveedores</span>
              <strong className="cifras">
                {precio(r.compras.monto)}
                <span className="secundario"> · {numero(r.compras.unidades)} ud.</span>
              </strong>
            </div>
          </section>

          {/* ------------------------------------------------ Evolución */}
          <section className="seccion">
            <h2>Ingresos por día</h2>
            <div className="panel panel-interior">
              <GraficoDiario dias={r.por_dia} />
            </div>
          </section>

          <div className="columnas iguales">
            <section className="seccion">
              <h2>Por categoría</h2>
              <div className="panel panel-interior"><Barras filas={categorias} /></div>
            </section>
            <section className="seccion">
              <h2>Por método de pago</h2>
              <div className="panel panel-interior"><Barras filas={metodos} /></div>
            </section>
          </div>

          {/* ------------------------------------------------ Personas */}
          <section className="seccion">
            <h2>Desempeño por vendedor</h2>
            <div className="tabla-contenedor">
              {r.por_vendedor.length === 0 ? <p className="vacio">Sin ventas en este periodo.</p> : (
                <table>
                  <thead>
                    <tr>
                      <th>Vendedor</th>
                      <th className="num">Ventas</th>
                      <th className="num">Ingresos</th>
                      <th className="num">Ticket promedio</th>
                      <th className="num">Participación</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.por_vendedor.map((v) => (
                      <tr key={v.id_usuario}>
                        <td>
                          <span className="principal-celda">{v.nombre}</span>
                          <span className="sub">{v.rol === "administrador" ? "Administrador" : "Vendedor"}</span>
                        </td>
                        <td className="num">{numero(v.ventas)}</td>
                        <td className="num">{precio(v.ingresos)}</td>
                        <td className="num">{precio(v.ticket_promedio)}</td>
                        <td className="num">{porcentaje(v.porcentaje)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          <section className="seccion">
            <h2>Piezas más vendidas</h2>
            <div className="tabla-contenedor">
              {r.top_piezas.length === 0 ? <p className="vacio">Sin ventas en este periodo.</p> : (
                <table>
                  <thead>
                    <tr>
                      <th>Pieza</th>
                      <th className="num">Unidades</th>
                      <th className="num">Ingresos</th>
                      <th className="num">Utilidad estimada</th>
                      <th className="num">Margen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.top_piezas.map((p) => (
                      <tr key={p.id_pieza}>
                        <td>
                          <span className="principal-celda">{p.nombre}</span>
                          <span className="sub">{p.categoria} · {NOMBRE_CONDICION[p.condicion]}</span>
                        </td>
                        <td className="num">{numero(p.unidades)}</td>
                        <td className="num">{precio(p.ingresos)}</td>
                        <td className="num">{p.utilidad_estimada === null ? <span className="secundario">Sin costo</span> : precio(p.utilidad_estimada)}</td>
                        <td className="num">{porcentaje(p.margen)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          <div className="columnas iguales">
            <section className="seccion">
              <h2>Mejores clientes</h2>
              <div className="tabla-contenedor">
                {r.top_clientes.length === 0 ? <p className="vacio">Sin ventas en este periodo.</p> : (
                  <table>
                    <thead>
                      <tr>
                        <th>Cliente</th>
                        <th className="num">Compras</th>
                        <th className="num">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {r.top_clientes.map((c) => (
                        <tr key={c.id_cliente}>
                          <td>
                            <span className="principal-celda">{c.nombre}</span>
                            <span className="sub">
                              {c.con_cuenta ? "Con cuenta" : "En tienda"} · última {fecha(c.ultima_compra)}
                            </span>
                          </td>
                          <td className="num">{numero(c.compras)}</td>
                          <td className="num">{precio(c.ingresos)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </section>

            <section className="seccion">
              <h2>Compras a proveedores</h2>
              <div className="tabla-contenedor">
                {r.compras.por_proveedor.length === 0 ? <p className="vacio">No se registraron entradas en este periodo.</p> : (
                  <table>
                    <thead>
                      <tr>
                        <th>Proveedor</th>
                        <th className="num">Unidades</th>
                        <th className="num">Monto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {r.compras.por_proveedor.map((p) => (
                        <tr key={p.id_proveedor}>
                          <td>
                            <span className="principal-celda">{p.proveedor}</span>
                            <span className="sub">{p.lotes === 1 ? "1 lote" : `${p.lotes} lotes`}</span>
                          </td>
                          <td className="num">{numero(p.unidades)}</td>
                          <td className="num">{precio(p.monto)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </section>
          </div>

          {/* ------------------------------------------------ Inventario */}
          <section className="seccion">
            <h2>Inventario actual</h2>
            <p className="secundario nota-seccion">Foto de hoy; no depende del periodo elegido.</p>
            <div className="cifras-resumen">
              <div className="cifra">
                <span className="valor cifras">{precio(r.inventario.valor_costo)}</span>
                <span className="nombre">Valor a costo</span>
                <span className="detalle">{numero(r.inventario.unidades)} unidades · {r.inventario.referencias} referencias</span>
              </div>
              <div className="cifra">
                <span className="valor cifras">{precio(r.inventario.valor_venta)}</span>
                <span className="nombre">Valor a precio de venta</span>
                <span className="detalle">Si se vendiera todo hoy</span>
              </div>
              <div className="cifra">
                <span className="valor cifras">{precio(r.inventario.utilidad_potencial)}</span>
                <span className="nombre">Utilidad potencial</span>
                <span className="detalle">Solo piezas con costo conocido</span>
              </div>
              <div className={r.inventario.stock_bajo + r.inventario.agotadas > 0 ? "cifra alerta" : "cifra"}>
                <span className="valor cifras">{r.inventario.stock_bajo + r.inventario.agotadas}</span>
                <span className="nombre">Para reponer</span>
                <span className="detalle">
                  {r.inventario.agotadas} agotadas · {r.inventario.stock_bajo} con {r.inventario.umbral_stock_bajo} ud. o menos
                </span>
              </div>
            </div>
          </section>

          <div className="columnas iguales">
            <section className="seccion">
              <h2>Piezas para reponer</h2>
              <div className="tabla-contenedor">
                {r.inventario.criticas.length === 0 ? (
                  <p className="vacio">Todas las piezas tienen más de {r.inventario.umbral_stock_bajo} unidades.</p>
                ) : (
                  <table>
                    <thead>
                      <tr>
                        <th>Pieza</th>
                        <th className="num">Stock</th>
                      </tr>
                    </thead>
                    <tbody>
                      {r.inventario.criticas.map((p) => (
                        <tr key={p.id_pieza}>
                          <td>
                            <span className="principal-celda">{p.nombre}</span>
                            <span className="sub">{p.categoria}</span>
                          </td>
                          <td className="num">
                            <span className={`etiqueta ${p.stock === 0 ? "peligro" : "alerta"}`}>
                              {p.stock === 0 ? "Agotada" : `${p.stock} ud.`}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </section>

            <section className="seccion">
              <h2>Sin ventas en el periodo</h2>
              <div className="tabla-contenedor">
                {r.inventario.sin_movimiento.length === 0 ? (
                  <p className="vacio">Todas las piezas con stock se vendieron al menos una vez.</p>
                ) : (
                  <table>
                    <thead>
                      <tr>
                        <th>Pieza</th>
                        <th className="num">Stock</th>
                        <th className="num">Valor detenido</th>
                      </tr>
                    </thead>
                    <tbody>
                      {r.inventario.sin_movimiento.map((p) => (
                        <tr key={p.id_pieza}>
                          <td>
                            <span className="principal-celda">{p.nombre}</span>
                            <span className="sub">{p.categoria}</span>
                          </td>
                          <td className="num">{numero(p.stock)}</td>
                          <td className="num">{precio(p.valor_venta)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </section>
          </div>

          <p className="nota-metodo secundario pequeno">
            La utilidad es una estimación: usa el costo promedio de los lotes de cada pieza.
            {r.resumen.piezas_sin_costo > 0 &&
              ` ${r.resumen.piezas_sin_costo} ${r.resumen.piezas_sin_costo === 1 ? "pieza vendida no tiene" : "piezas vendidas no tienen"} lotes registrados (${precio(r.resumen.ingresos_sin_costo)} en ingresos) y no entran en el margen.`}
            {sinVentas && " No hubo ventas en este periodo."} Las ventas anuladas no suman en ningún indicador.
          </p>
        </div>
      )}
    </>
  );
}
