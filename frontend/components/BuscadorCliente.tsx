"use client";

import { useId, useMemo, useRef, useState } from "react";

import type { Cliente } from "../lib/api";
import { normalizar } from "../lib/formato";

const MAXIMO = 8;

function nombre(c: Cliente) {
  return `${c.nombres} ${c.apellidos}`;
}

/**
 * Buscador de clientes (combobox accesible): se escribe nombre, documento, teléfono o correo
 * y se elige de la lista con el mouse o con las flechas y Enter.
 */
export default function BuscadorCliente({
  clientes,
  seleccionado,
  alElegir,
  alCrear,
}: {
  clientes: Cliente[];
  seleccionado: Cliente | null;
  alElegir: (c: Cliente | null) => void;
  alCrear?: (texto: string) => void;
}) {
  const id = useId();
  const entrada = useRef<HTMLInputElement>(null);
  const [texto, setTexto] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [activo, setActivo] = useState(0);

  const resultados = useMemo(() => {
    const palabras = normalizar(texto.trim()).split(/\s+/).filter(Boolean);
    const lista = clientes.filter((c) => {
      const fuente = normalizar(`${nombre(c)} ${c.documento ?? ""} ${c.telefono ?? ""} ${c.email ?? ""}`);
      return palabras.every((p) => fuente.includes(p));
    });
    lista.sort((a, b) => nombre(a).localeCompare(nombre(b), "es"));
    return lista;
  }, [clientes, texto]);

  const visibles = resultados.slice(0, MAXIMO);

  function elegir(c: Cliente) {
    alElegir(c);
    setTexto("");
    setAbierto(false);
  }

  if (seleccionado) {
    return (
      <div className="cliente-elegido">
        <span>
          <span className="titulo">{nombre(seleccionado)}</span>
          <span className="secundario pequeno" style={{ display: "block" }}>
            {[seleccionado.documento && `Doc. ${seleccionado.documento}`, seleccionado.telefono, seleccionado.email]
              .filter(Boolean)
              .join(" · ") || "Sin datos de contacto"}
          </span>
        </span>
        <button type="button" className="boton-texto"
          onClick={() => { alElegir(null); setTimeout(() => entrada.current?.focus(), 0); }}>
          Cambiar
        </button>
      </div>
    );
  }

  return (
    <div className="buscador-cliente">
      <input
        ref={entrada}
        id="cliente"
        className="control"
        type="search"
        role="combobox"
        aria-expanded={abierto}
        aria-controls={`${id}-lista`}
        aria-autocomplete="list"
        aria-activedescendant={abierto && visibles[activo] ? `${id}-${visibles[activo].id_cliente}` : undefined}
        autoComplete="off"
        placeholder="Nombre, documento, teléfono o correo"
        value={texto}
        onChange={(e) => { setTexto(e.target.value); setActivo(0); setAbierto(true); }}
        onFocus={() => setAbierto(true)}
        onBlur={() => setTimeout(() => setAbierto(false), 120)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setAbierto(true); setActivo((a) => Math.min(a + 1, visibles.length - 1)); }
          if (e.key === "ArrowUp") { e.preventDefault(); setActivo((a) => Math.max(a - 1, 0)); }
          if (e.key === "Enter" && abierto && visibles[activo]) { e.preventDefault(); elegir(visibles[activo]); }
          if (e.key === "Escape") setAbierto(false);
        }}
      />
      {abierto && (
        <ul id={`${id}-lista`} className="opciones-cliente" role="listbox" aria-label="Clientes">
          {visibles.map((c, i) => (
            <li
              key={c.id_cliente}
              id={`${id}-${c.id_cliente}`}
              role="option"
              aria-selected={i === activo}
              className={i === activo ? "activa" : undefined}
              onMouseDown={(e) => { e.preventDefault(); elegir(c); }}
              onMouseEnter={() => setActivo(i)}
            >
              <span className="titulo">{nombre(c)}</span>
              <span className="secundario pequeno cifras">
                {[c.documento && `Doc. ${c.documento}`, c.telefono].filter(Boolean).join(" · ") || "Sin documento"}
              </span>
            </li>
          ))}
          {resultados.length === 0 && (
            <li className="sin-resultados secundario pequeno" role="presentation">
              Ningún cliente coincide con “{texto}”.
            </li>
          )}
          {resultados.length > MAXIMO && (
            <li className="sin-resultados secundario pequeno" role="presentation">
              {resultados.length - MAXIMO} más: escribe más para afinar la búsqueda.
            </li>
          )}
          {alCrear && (
            <li className="crear" role="presentation">
              <button type="button" className="boton-texto" onMouseDown={(e) => { e.preventDefault(); alCrear(texto); }}>
                + Registrar cliente nuevo{texto.trim() ? ` “${texto.trim()}”` : ""}
              </button>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
