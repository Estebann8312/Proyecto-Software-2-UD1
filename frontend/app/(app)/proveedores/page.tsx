"use client";

import { FormEvent, useState } from "react";

import Eliminar from "../../../components/Eliminar";
import { Aviso, Campo, Dialogo, Encabezado, EstadoCarga } from "../../../components/ui";
import { enviar, type Proveedor } from "../../../lib/api";
import { useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

export default function ProveedoresPage() {
  const usuario = useRequiereSesion(["administrador", "vendedor"]);
  const esAdmin = usuario?.rol === "administrador";
  const proveedores = useDatos<Proveedor[]>(usuario ? "/proveedores/" : null);

  const [editando, setEditando] = useState<Proveedor | "nuevo" | null>(null);
  const [eliminando, setEliminando] = useState<Proveedor | null>(null);
  const [mensaje, setMensaje] = useState("");

  if (!usuario) return null;

  return (
    <>
      <Encabezado
        titulo="Proveedores"
        descripcion={esAdmin ? "A quién se le compran las piezas. Se eligen al registrar una entrada en el inventario." : "Consulta de proveedores. Solo un administrador puede modificarlos."}
      >
        {esAdmin && (
          <button type="button" className="boton" onClick={() => { setMensaje(""); setEditando("nuevo"); }}>Nuevo proveedor</button>
        )}
      </Encabezado>

      <Aviso texto={mensaje} tipo="exito" />

      <div className="tabla-contenedor" style={{ marginTop: mensaje ? 14 : 0 }}>
        <EstadoCarga cargando={proveedores.cargando} error={proveedores.error}
          vacio={proveedores.datos?.length === 0} textoVacio="Todavía no hay proveedores." />
        {!!proveedores.datos?.length && (
          <table>
            <thead>
              <tr>
                <th>Proveedor</th>
                <th>Persona de contacto</th>
                <th>Teléfono</th>
                {esAdmin && <th><span className="visualmente-oculto">Acciones</span></th>}
              </tr>
            </thead>
            <tbody>
              {proveedores.datos.map((p) => (
                <tr key={p.id_proveedor}>
                  <td className="principal-celda">{p.nombre}</td>
                  <td>{p.contacto ?? "—"}</td>
                  <td className="cifras">{p.telefono ?? "—"}</td>
                  {esAdmin && (
                    <td className="num">
                      <button type="button" className="boton-texto" onClick={() => { setMensaje(""); setEditando(p); }}>Editar</button>
                      <button type="button" className="boton-texto peligro" style={{ marginLeft: 12 }}
                        onClick={() => { setMensaje(""); setEliminando(p); }}>Eliminar</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {esAdmin && (
        <>
          <Dialogo abierto={!!editando} titulo={editando === "nuevo" ? "Nuevo proveedor" : "Editar proveedor"} alCerrar={() => setEditando(null)}>
            {editando && (
              <FormProveedor
                proveedor={editando === "nuevo" ? undefined : editando}
                alGuardar={(p) => {
                  setEditando(null);
                  setMensaje(`${p.nombre} quedó guardado.`);
                  proveedores.recargar();
                }}
              />
            )}
          </Dialogo>

          <Eliminar
            endpoint={eliminando ? `/proveedores/${eliminando.id_proveedor}/` : null}
            nombre={eliminando?.nombre ?? ""}
            explicacion="Si ya tiene entradas registradas en el inventario, no se podrá eliminar."
            alCerrar={() => setEliminando(null)}
            alEliminar={() => {
              setMensaje(`${eliminando?.nombre} fue eliminado.`);
              setEliminando(null);
              proveedores.recargar();
            }}
          />
        </>
      )}
    </>
  );
}

function FormProveedor({ proveedor, alGuardar }: { proveedor?: Proveedor; alGuardar: (p: Proveedor) => void }) {
  const [form, setForm] = useState({
    nombre: proveedor?.nombre ?? "",
    contacto: proveedor?.contacto ?? "",
    telefono: proveedor?.telefono ?? "",
  });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    const cuerpo = { nombre: form.nombre, contacto: form.contacto || null, telefono: form.telefono || null };
    try {
      alGuardar(
        proveedor
          ? await enviar<Proveedor>(`/proveedores/${proveedor.id_proveedor}/`, "PATCH", cuerpo)
          : await enviar<Proveedor>("/proveedores/", "POST", cuerpo)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar.");
      setEnviando(false);
    }
  }

  return (
    <form className="formulario" onSubmit={guardar}>
      <Campo id="pr-nombre" etiqueta="Nombre">
        <input id="pr-nombre" className="control" required maxLength={150} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
      </Campo>
      <div className="fila-campos">
        <Campo id="pr-contacto" etiqueta="Persona de contacto (opcional)">
          <input id="pr-contacto" className="control" maxLength={100} value={form.contacto} onChange={(e) => setForm({ ...form, contacto: e.target.value })} />
        </Campo>
        <Campo id="pr-telefono" etiqueta="Teléfono (opcional)">
          <input id="pr-telefono" className="control" type="tel" maxLength={20} value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} />
        </Campo>
      </div>
      <Aviso texto={error} />
      <div className="pie-dialogo">
        <button type="submit" className="boton" disabled={enviando}>{enviando ? "Guardando…" : "Guardar"}</button>
      </div>
    </form>
  );
}
