"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import PanelAcceso from "../../components/PanelAcceso";
import { Aviso, Campo } from "../../components/ui";
import { useSession } from "../../lib/session";

export default function LoginPage() {
  const router = useRouter();
  const { estado, iniciarSesion } = useSession();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  // Si ya hay sesión, no tiene sentido mostrar el login.
  useEffect(() => {
    if (estado === "autenticado") router.replace("/dashboard");
  }, [estado, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setEnviando(true);
    try {
      await iniciarSesion(username.trim(), password);
      router.replace("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo iniciar sesión.");
      setEnviando(false);
    }
  }

  return (
    <main className="acceso">
      <section className="acceso-form">
        <div className="acceso-form-interior">
          <Link href="/login" className="marca">PC Stock</Link>

          <h1>Iniciar sesión</h1>
          <p className="intro">Entra con el usuario que te asignó la tienda o con tu cuenta de cliente.</p>

          <form className="formulario" onSubmit={handleSubmit}>
            <Campo id="username" etiqueta="Usuario">
              <input
                id="username"
                className="control"
                autoComplete="username"
                autoCapitalize="none"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </Campo>

            <Campo id="password" etiqueta="Contraseña">
              <input
                id="password"
                className="control"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </Campo>

            <Aviso texto={error} />

            <button type="submit" className="boton bloque" disabled={enviando}>
              {enviando ? "Entrando…" : "Iniciar sesión"}
            </button>
          </form>

          <p className="acceso-pie">
            ¿Vas a comprar y no tienes cuenta? <Link href="/register">Crear cuenta de cliente</Link>
          </p>
        </div>
      </section>

      <PanelAcceso />
    </main>
  );
}
