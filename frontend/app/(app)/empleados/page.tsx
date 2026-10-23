"use client";

import { FormEvent, useState } from "react";

import Eliminar from "../../../components/Eliminar";
import { Aviso, Campo, Dialogo, Encabezado, EstadoCarga } from "../../../components/ui";
import { enviar, type Empleado } from "../../../lib/api";
import { fecha } from "../../../lib/formato";
import { NOMBRE_ROL, useRequiereSesion } from "../../../lib/session";
import { useDatos } from "../../../lib/useDatos";

export default function EmpleadosPage() {
  const usuario = useRequiereSesion(["administrador"]);
  const empleados = useDatos<Empleado[]>(usuario ? "/usuarios/" : null);

  const [editando, setEditando] = useState<Empleado | "nuevo" | null>(null);
  const [eliminando, setEliminando] = useState<Empleado | null>(null);
  const [mensaje, setMensaje] = useState("");

  if (!usuario) return null;

  return (
    <>
      <Encabezado titulo="Empleados" descripcion="Quién puede entrar al sistema y con qué permisos.">
        <button type="button" className="boton" onClick={() => { setMensaje(""); setEditando("nuevo"); }}>Nuevo empleado</button>
      </Encabezado>

      <Aviso texto={mensaje} tipo="exito" />

      <div className="tabla-contenedor" style={{ marginTop: mensaje ? 14 : 0 }}>
        <EstadoCarga cargando={empleados.cargando} error={empleados.error} vacio={empleados.datos?.length === 0} />
        {!!empleados.datos?.length && (
          <table>
            <thead>
              <tr>
                <th>Empleado</th>
                <th>Rol</th>
                <th>Contacto</th>
                <th>Desde</th>
                <th><span className="visualmente-oculto">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {empleados.datos.map((e) => {
                const soyYo = e.id_usuario === usuario.id_usuario;
                return (
                  <tr key={e.id_usuario}>
                    <td>
                      <span className="principal-celda">{e.nombres} {e.apellidos}{soyYo ? " (tú)" : ""}</span>
                      <span className="sub">Usuario: {e.username}</span>
                    </td>
                    <td>
                      <span className={e.rol === "administrador" ? "etiqueta ok" : "etiqueta"}>{NOMBRE_ROL[e.rol]}</span>
                    </td>
                    <td>
                      {e.email}
                      <span className="sub cifras">{e.telefono ?? "Sin teléfono"}</span>
                    </td>
                    <td>{fecha(e.fecha_registro)}</td>
                    <td className="num">
                      <button type="button" className="boton-texto" onClick={() => { setMensaje(""); setEditando(e); }}>Editar</button>
                      {!soyYo && (
                        <button type="button" className="boton-texto peligro" style={{ marginLeft: 12 }}
                          onClick={() => { setMensaje(""); setEliminando(e); }}>Eliminar</button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <p className="secundario pequeno" style={{ marginTop: 14, maxWidth: "70ch" }}>
        El vendedor registra ventas y clientes y consulta el inventario. El administrador además gestiona piezas,
        entradas de proveedor, anulaciones y empleados.
      </p>

      <Dialogo abierto={!!editando} titulo={editando === "nuevo" ? "Nuevo empleado" : "Editar empleado"} alCerrar={() => setEditando(null)}>
        {editando && (
          <FormEmpleado
            empleado={editando === "nuevo" ? undefined : editando}
            esUnoMismo={editando !== "nuevo" && editando.id_usuario === usuario.id_usuario}
            alGuardar={(e) => {
              setEditando(null);
              setMensaje(`${e.nombres} ${e.apellidos} quedó guardado.`);
              empleados.recargar();
            }}
          />
        )}
      </Dialogo>

      <Eliminar
        endpoint={eliminando ? `/usuarios/${eliminando.id_usuario}/` : null}
        nombre={eliminando ? `${eliminando.nombres} ${eliminando.apellidos}` : ""}
        explicacion="Perderá el acceso al sistema. Si ya registró ventas, no se podrá eliminar."
        alCerrar={() => setEliminando(null)}
        alEliminar={() => {
          setMensaje(`${eliminando?.nombres} ${eliminando?.apellidos} fue eliminado.`);
          setEliminando(null);
          empleados.recargar();
        }}
      />
    </>
  );
}

function FormEmpleado({
  empleado,
  esUnoMismo,
  alGuardar,
}: {
  empleado?: Empleado;
  esUnoMismo: boolean;
  alGuardar: (e: Empleado) => void;
}) {
  const [form, setForm] = useState({
    nombres: empleado?.nombres ?? "",
    apellidos: empleado?.apellidos ?? "",
    documento: empleado?.documento ?? "",
    telefono: empleado?.telefono ?? "",
    email: empleado?.email ?? "",
    username: empleado?.username ?? "",
    password: "",
    rol: empleado?.rol ?? "vendedor",
  });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    const cuerpo: Record<string, unknown> = {
      ...form,
      documento: form.documento || null,
      telefono: form.telefono || null,
    };
    if (!form.password) delete cuerpo.password;
    try {
      alGuardar(
        empleado
          ? await enviar<Empleado>(`/usuarios/${empleado.id_usuario}/`, "PATCH", cuerpo)
          : await enviar<Empleado>("/usuarios/", "POST", cuerpo)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar.");
      setEnviando(false);
    }
  }

  return (
    <form className="formulario" onSubmit={guardar}>
      <div className="fila-campos">
        <Campo id="e-nombres" etiqueta="Nombres">
          <input id="e-nombres" className="control" required value={form.nombres} onChange={(e) => setForm({ ...form, nombres: e.target.value })} />
        </Campo>
        <Campo id="e-apellidos" etiqueta="Apellidos">
          <input id="e-apellidos" className="control" required value={form.apellidos} onChange={(e) => setForm({ ...form, apellidos: e.target.value })} />
        </Campo>
      </div>
      <div className="fila-campos">
        <Campo id="e-documento" etiqueta="Documento (opcional)">
          <input id="e-documento" className="control" inputMode="numeric" value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} />
        </Campo>
        <Campo id="e-telefono" etiqueta="Teléfono (opcional)">
          <input id="e-telefono" className="control" type="tel" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} />
        </Campo>
      </div>
      <Campo id="e-email" etiqueta="Correo">
        <input id="e-email" className="control" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </Campo>
      <div className="fila-campos">
        <Campo id="e-username" etiqueta="Usuario para entrar">
          <input id="e-username" className="control" required autoCapitalize="none" autoComplete="off"
            value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </Campo>
        <Campo id="e-password" etiqueta={empleado ? "Nueva contraseña (opcional)" : "Contraseña"}
          ayuda={empleado ? "Déjala vacía para no cambiarla." : "Mínimo 8 caracteres, no solo números."}>
          <input id="e-password" className="control" type="password" autoComplete="new-password" minLength={8}
            required={!empleado} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Campo>
      </div>
      <Campo id="e-rol" etiqueta="Rol" ayuda={esUnoMismo ? "No puedes cambiar tu propio rol." : undefined}>
        <select id="e-rol" className="control" value={form.rol} disabled={esUnoMismo}
          onChange={(e) => setForm({ ...form, rol: e.target.value as Empleado["rol"] })}>
          <option value="vendedor">Vendedor</option>
          <option value="administrador">Administrador</option>
        </select>
      </Campo>
      <Aviso texto={error} />
      <div className="pie-dialogo">
        <button type="submit" className="boton" disabled={enviando}>{enviando ? "Guardando…" : "Guardar"}</button>
      </div>
    </form>
  );
}
