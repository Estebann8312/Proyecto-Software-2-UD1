"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Rol } from "../lib/api";
import { NOMBRE_ROL, nombreVisible, useRequiereSesion, useSession } from "../lib/session";

type Enlace = { href: string; texto: string; roles: Rol[] };

const ENLACES: Enlace[] = [
  { href: "/dashboard", texto: "Inicio", roles: ["administrador", "vendedor"] },
  { href: "/dashboard", texto: "Catálogo", roles: ["cliente"] },
  { href: "/ventas", texto: "Ventas", roles: ["administrador", "vendedor"] },
  { href: "/inventario", texto: "Inventario", roles: ["administrador", "vendedor"] },
  { href: "/clientes", texto: "Clientes", roles: ["administrador", "vendedor"] },
  { href: "/proveedores", texto: "Proveedores", roles: ["administrador", "vendedor"] },
  { href: "/empleados", texto: "Empleados", roles: ["administrador"] },
];

/** Estructura de toda pantalla con sesión: barra lateral según el rol y contenido. */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const usuario = useRequiereSesion();
  const { cerrarSesion } = useSession();
  const ruta = usePathname();

  if (!usuario) return <p className="cargando">Cargando…</p>;

  const enlaces = ENLACES.filter((e) => e.roles.includes(usuario.rol));
  const activo = (href: string) =>
    href === "/dashboard" ? ruta === href : ruta === href || ruta.startsWith(`${href}/`);

  return (
    <div className="app">
      <aside className="lateral">
        <div className="lateral-interior">
          <Link href="/dashboard" className="marca">PC Stock</Link>

          <nav className="navegacion" aria-label="Principal">
            {enlaces.map((e) => (
              <Link key={e.texto} href={e.href} aria-current={activo(e.href) ? "page" : undefined}>
                {e.texto}
              </Link>
            ))}
          </nav>

          <div className="cuenta-usuario">
            <strong>{nombreVisible(usuario)}</strong>
            <span>{NOMBRE_ROL[usuario.rol]} · {usuario.username}</span>
            <button type="button" className="boton secundario" onClick={cerrarSesion}>
              Cerrar sesión
            </button>
          </div>
        </div>
      </aside>

      <main className="principal">{children}</main>
    </div>
  );
}
