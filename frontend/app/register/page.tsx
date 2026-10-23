"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import PanelAcceso from "../../components/PanelAcceso";
import { Aviso, Campo } from "../../components/ui";
import { register } from "../../lib/api";
import { useSession } from "../../lib/session";

const VACIO = {
  first_name: "",
  last_name: "",
  documento: "",
  telefono: "",
  email: "",
  username: "",
  password: "",
};

export default function RegisterPage() {
  const router = useRouter();
  const { iniciarSesion } = useSession();

  const [form, setForm] = useState(VACIO);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  function cambiar(event: ChangeEvent<HTMLInputElement>) {
    const { name, value } = event.target;
    setForm((actual) => ({ ...actual, [name]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setEnviando(true);
    try {
      await register({ ...form, username: form.username.trim(), email: form.email.trim() });
      // Cuenta creada: se entra directamente, sin volver a escribir la contraseña.
      await iniciarSesion(form.username.trim(), form.password);
      router.replace("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo crear la cuenta.");
      setEnviando(false);
    }
  }

  return (
    <main className="acceso">
      <section className="acceso-form">
        <div className="acceso-form-interior ancho">
          <Link href="/login" className="marca">PC Stock</Link>

          <h1>Crear cuenta de cliente</h1>
          <p className="intro">Con tu cuenta puedes consultar el catálogo y los precios actualizados.</p>

          <form className="formulario" onSubmit={handleSubmit}>
            <div className="fila-campos">
              <Campo id="first_name" etiqueta="Nombres">
                <input id="first_name" name="first_name" className="control" autoComplete="given-name"
                  value={form.first_name} onChange={cambiar} required />
              </Campo>
              <Campo id="last_name" etiqueta="Apellidos">
                <input id="last_name" name="last_name" className="control" autoComplete="family-name"
                  value={form.last_name} onChange={cambiar} required />
              </Campo>
            </div>

            <div className="fila-campos">
              <Campo id="documento" etiqueta="Documento (opcional)">
                <input id="documento" name="documento" className="control" inputMode="numeric"
                  value={form.documento} onChange={cambiar} />
              </Campo>
              <Campo id="telefono" etiqueta="Teléfono (opcional)">
                <input id="telefono" name="telefono" className="control" type="tel" autoComplete="tel"
                  value={form.telefono} onChange={cambiar} />
              </Campo>
            </div>

            <Campo id="email" etiqueta="Correo electrónico">
              <input id="email" name="email" className="control" type="email" autoComplete="email"
                value={form.email} onChange={cambiar} required />
            </Campo>

            <div className="fila-campos">
              <Campo id="username" etiqueta="Usuario">
                <input id="username" name="username" className="control" autoComplete="username"
                  autoCapitalize="none" value={form.username} onChange={cambiar} required />
              </Campo>
              <Campo id="password" etiqueta="Contraseña" ayuda="Mínimo 8 caracteres, no solo números.">
                <input id="password" name="password" className="control" type="password"
                  autoComplete="new-password" minLength={8} value={form.password} onChange={cambiar} required />
              </Campo>
            </div>

            <Aviso texto={error} />

            <button type="submit" className="boton bloque" disabled={enviando}>
              {enviando ? "Creando cuenta…" : "Crear cuenta"}
            </button>
          </form>

          <p className="acceso-pie">
            ¿Ya tienes cuenta? <Link href="/login">Iniciar sesión</Link>
          </p>
        </div>
      </section>

      <PanelAcceso />
    </main>
  );
}
