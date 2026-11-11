"use client";

import { FormEvent, useMemo, useState } from "react";

import { Encabezado, EstadoCarga } from "../../../components/ui";
import type { Consolidado, FacturaSede, TipoFactura } from "../../../lib/api";
import { fecha, fechaConHora, normalizar, precio } from "../../../lib/formato";
import { atajo as rangoDeAtajo, ATAJOS, descargarCsv, type Rango } from "../../../lib/rangos";
import { useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

const ESTADO_SEDE = {
  ok: { texto: "En línea", clase: "ok" },
  error: { texto: "Sin conexión", clase: "peligro" },
  sin_configurar: { texto: "Sin configurar", clase: "alerta" },
} as const;

const NOMBRE_TIPO: Record<TipoFactura, string> = { venta: "Venta", compra: "Compra" };

function pesos(valor: string) {
  return Math.round(Number(valor)).toString();
}

function exportar(c: Consolidado) {
  const filas: (string | number | null)[][] = [
    ["Consolidado entre sedes"],
    ["Desde", c.desde],
    ["Hasta", c.hasta],
    ["Moneda", c.moneda],
    [],
    ["Sede", "Estado", "Ventas", "Total ventas", "Compras", "Total compras"],
    ...c.sedes.map((s) => [
      s.sucursal, ESTADO_SEDE[s.estado].texto,
      s.resumen.venta.cantidad, pesos(s.resumen.venta.total),
      s.resumen.compra.cantidad, pesos(s.resumen.compra.total),
    ]),
    ["Total", "", c.total.venta.cantidad, pesos(c.total.venta.total), c.total.compra.cantidad, pesos(c.total.compra.total)],
    [],
    ["Sede", "Tipo", "Número", "Fecha", "Documento", "Tercero", "Subtotal", "IVA", "Total"],
    ...c.facturas.map((f) => [
      f.sucursal, NOMBRE_TIPO[f.tipo], f.numero, f.fecha.slice(0, 10),
      f.tercero.documento, f.tercero.nombre, pesos(f.subtotal), pesos(f.iva), pesos(f.total),
    ]),
  ];
  descargarCsv(`consolidado-sedes_${c.desde}_${c.hasta}.csv`, filas);
}

export default function SedesPage() {
  const usuario = useRequiereSesion(["administrador"]);

  const inicial = rangoDeAtajo("mes");
  const [rango, setRango] = useState<Rango>(inicial);
  const [borrador, setBorrador] = useState<Rango>(inicial);
  const [atajo, setAtajo] = useState("mes");
  const [tipo, setTipo] = useState<"" | TipoFactura>("");
  const [sede, setSede] = useState("");
  const [busqueda, setBusqueda] = useState("");

  const consolidado = useDatos<Consolidado>(
    usuario ? `/consolidado/?desde=${rango.desde}&hasta=${rango.hasta}` : null
  );
  const c = consolidado.datos;

  function elegirAtajo(id: string) {
    const nuevo = rangoDeAtajo(id);
    setAtajo(id);
    setBorrador(nuevo);
    setRango(nuevo);
  }

  function aplicar(e: FormEvent) {
    e.preventDefault();
    setAtajo("");
    setRango(borrador);
  }

  const facturas = useMemo(() => {
    const q = normalizar(busqueda.trim());
    return (c?.facturas ?? [])
      .filter((f) => !tipo || f.tipo === tipo)
      .filter((f) => !sede || f.sucursal === sede)
      .filter((f) => !q || normalizar(`${f.numero} ${f.tercero.nombre} ${f.tercero.documento ?? ""}`).includes(q))
      .slice()
      .reverse(); // la más reciente primero
  }, [c, tipo, sede, busqueda]);

  const totalVentas = Number(c?.total.venta.total ?? 0);
  const aliadaCaida = c?.sedes.some((s) => !s.propia && s.estado !== "ok");

  if (!usuario) return null;

  return (
    <>
      <Encabezado
        titulo="Sedes"
        descripcion={
          c
            ? `Ventas y compras de las dos sedes, del ${fecha(c.desde)} al ${fecha(c.hasta)}.`
            : "Ventas y compras de las dos sedes en un solo lugar."
        }
      >
        <button type="button" className="boton secundario" onClick={consolidado.recargar}>
          Actualizar
        </button>
        <button type="button" className="boton" disabled={!c} onClick={() => c && exportar(c)}>
          Descargar CSV
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

      <EstadoCarga cargando={consolidado.cargando && !c} error={consolidado.error} />

      {c && (
        <div className={consolidado.cargando ? "informe actualizando" : "informe"}>
          {aliadaCaida && (
            <p className="aviso" role="status" style={{ marginBottom: 20 }}>
              Los totales solo incluyen las sedes en línea. {c.sedes.find((s) => !s.propia)?.error}
            </p>
          )}

          {/* ------------------------------------------------ Totales */}
          <section className="cifras-resumen" aria-label="Totales de las dos sedes">
            <div className="cifra">
              <span className="valor cifras">{precio(c.total.venta.total)}</span>
              <span className="nombre">Ventas de las dos sedes</span>
              <span className="detalle">{c.total.venta.cantidad} facturas · IVA {precio(c.total.venta.iva)}</span>
            </div>
            <div className="cifra">
              <span className="valor cifras">{precio(c.total.compra.total)}</span>
              <span className="nombre">Compras a proveedores</span>
              <span className="detalle">{c.total.compra.cantidad} facturas · IVA {precio(c.total.compra.iva)}</span>
            </div>
            <div className="cifra">
              <span className="valor cifras">
                {precio(Number(c.total.venta.total) - Number(c.total.compra.total))}
              </span>
              <span className="nombre">Ventas menos compras</span>
              <span className="detalle">Flujo del periodo, con IVA</span>
            </div>
            <div className="cifra">
              <span className="valor cifras">
                {precio(Number(c.total.venta.iva) - Number(c.total.compra.iva))}
              </span>
              <span className="nombre">IVA por pagar</span>
              <span className="detalle">IVA de ventas menos el de compras</span>
            </div>
          </section>

          {/* ------------------------------------------------ Por sede */}
          <section className="seccion">
            <h2>Por sede</h2>
            <div className="sedes">
              {c.sedes.map((s) => {
                const estado = ESTADO_SEDE[s.estado];
                const parte = totalVentas > 0 ? (Number(s.resumen.venta.total) / totalVentas) * 100 : 0;
                return (
                  <article key={s.sucursal} className="panel panel-interior sede">
                    <header>
                      <div>
                        <h3>{s.sucursal}</h3>
                        <span className="secundario pequeno">{s.propia ? "Esta sede" : "Sede aliada"}</span>
                      </div>
                      <span className={`etiqueta ${estado.clase}`}>{estado.texto}</span>
                    </header>
                    {s.estado === "ok" ? (
                      <>
                        <dl className="datos-sede">
                          <div>
                            <dt>Ventas</dt>
                            <dd className="cifras">{precio(s.resumen.venta.total)}</dd>
                            <span className="secundario pequeno">{s.resumen.venta.cantidad} facturas</span>
                          </div>
                          <div>
                            <dt>Compras</dt>
                            <dd className="cifras">{precio(s.resumen.compra.total)}</dd>
                            <span className="secundario pequeno">{s.resumen.compra.cantidad} facturas</span>
                          </div>
                        </dl>
                        <div className="barras-pista" aria-hidden="true">
                          <span style={{ width: `${parte}%` }} />
                        </div>
                        <span className="secundario pequeno cifras">
                          {parte.toLocaleString("es-CO", { maximumFractionDigits: 1 })} % de las ventas de las dos sedes
                        </span>
                      </>
                    ) : (
                      <p className="secundario pequeno">{s.error}</p>
                    )}
                  </article>
                );
              })}
            </div>
          </section>

          {/* ------------------------------------------------ Facturas */}
          <section className="seccion">
            <h2>Facturas</h2>
            <div className="filtros">
              <input className="control buscar" type="search" aria-label="Buscar factura"
                placeholder="Buscar por número, nombre o documento" value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)} />
              <select className="control" aria-label="Tipo de factura" value={tipo}
                onChange={(e) => setTipo(e.target.value as "" | TipoFactura)}>
                <option value="">Ventas y compras</option>
                <option value="venta">Solo ventas</option>
                <option value="compra">Solo compras</option>
              </select>
              <select className="control" aria-label="Sede" value={sede} onChange={(e) => setSede(e.target.value)}>
                <option value="">Las dos sedes</option>
                {c.sedes.filter((s) => s.estado === "ok").map((s) => (
                  <option key={s.sucursal} value={s.sucursal}>{s.sucursal}</option>
                ))}
              </select>
            </div>
            <div className="tabla-contenedor">
              {facturas.length === 0 ? (
                <p className="vacio">No hay facturas con esos filtros.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Factura</th>
                      <th>Tercero</th>
                      <th className="num">Subtotal</th>
                      <th className="num">IVA</th>
                      <th className="num">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {facturas.map((f: FacturaSede) => (
                      <tr key={`${f.sucursal}-${f.numero}`}>
                        <td>
                          <span className="principal-celda cifras">{f.numero}</span>
                          <span className="sub">
                            {f.sucursal} · {NOMBRE_TIPO[f.tipo]} · {fechaConHora(f.fecha)}
                          </span>
                        </td>
                        <td>
                          {f.tercero.nombre}
                          <span className="sub cifras">
                            {f.tercero.documento === "222222222222"
                              ? "Consumidor final"
                              : f.tercero.documento ?? "Sin documento"}
                          </span>
                        </td>
                        <td className="num">{precio(f.subtotal)}</td>
                        <td className="num">{precio(f.iva)}</td>
                        <td className="num">{precio(f.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          <p className="nota-metodo secundario pequeno">
            Cada sede entrega sus facturas en el formato acordado (CONTRATO-INTEGRACION.md): ventas
            completadas y compras a proveedores, con el IVA incluido en el total. Las ventas anuladas no se envían.
          </p>
        </div>
      )}
    </>
  );
}
