"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

import type { Me, Rol } from "../lib/api";
import { NOMBRE_ROL, nombreVisible, useRequiereSesion, useSession } from "../lib/session";
import { Icono, type NombreIcono } from "./Iconos";

type Enlace = { href: string; texto: string; icono: NombreIcono; roles: Rol[] };
type Grupo = { titulo?: string; enlaces: Enlace[] };

const EMPLEADOS: Rol[] = ["administrador", "vendedor"];

/** Menú por temas. Un grupo sin enlaces para el rol no se muestra. */
const GRUPOS: Grupo[] = [
  {
    enlaces: [
      { href: "/dashboard", texto: "Inicio", icono: "inicio", roles: EMPLEADOS },
      { href: "/dashboard", texto: "Catálogo", icono: "catalogo", roles: ["cliente"] },
      { href: "/mis-compras", texto: "Mis compras", icono: "compras", roles: ["cliente"] },
    ],
  },
  {
    titulo: "Operación",
    enlaces: [
      { href: "/ventas", texto: "Ventas", icono: "ventas", roles: EMPLEADOS },
      { href: "/inventario", texto: "Inventario", icono: "inventario", roles: EMPLEADOS },
    ],
  },
  {
    titulo: "Personas",
    enlaces: [
      { href: "/clientes", texto: "Clientes", icono: "clientes", roles: EMPLEADOS },
      { href: "/proveedores", texto: "Proveedores", icono: "proveedores", roles: EMPLEADOS },
      { href: "/empleados", texto: "Empleados", icono: "empleados", roles: ["administrador"] },
    ],
  },
  {
    titulo: "Análisis",
    enlaces: [
      { href: "/reportes", texto: "Reportes", icono: "reportes", roles: ["administrador"] },
      { href: "/sedes", texto: "Sedes", icono: "sedes", roles: ["administrador"] },
    ],
  },
];

function iniciales(usuario: Me) {
  const letras = nombreVisible(usuario)
    .split(" ")
    .filter(Boolean)
    .map((p) => p[0])
    .join("");
  return (letras || usuario.username[0] || "?").slice(0, 2).toUpperCase();
}

/** Estructura de toda pantalla con sesión: barra lateral según el rol y contenido. */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const usuario = useRequiereSesion();
  const { cerrarSesion } = useSession();
  const ruta = usePathname();
  const navegacion = useRef<HTMLElement>(null);

  // En celular el menú se desplaza de lado: deja visible la opción activa.
  useEffect(() => {
    navegacion.current
      ?.querySelector('[aria-current="page"]')
      ?.scrollIntoView({ block: "nearest", inline: "center" });
  }, [ruta, usuario]);

  if (!usuario) return <p className="cargando">Cargando…</p>;

  const grupos = GRUPOS.map((g) => ({ ...g, enlaces: g.enlaces.filter((e) => e.roles.includes(usuario.rol)) }))
    .filter((g) => g.enlaces.length > 0);
  const activo = (href: string) =>
    href === "/dashboard" ? ruta === href : ruta === href || ruta.startsWith(`${href}/`);

  return (
    <div className="app">
      <aside className="lateral">
        <div className="lateral-interior">
          <Link href="/dashboard" className="marca">PC Stock</Link>

          <nav ref={navegacion} className="navegacion" aria-label="Principal">
            {grupos.map((g) => (
              <div key={g.titulo ?? "inicio"} className="grupo-navegacion">
                {g.titulo && <span className="titulo-grupo">{g.titulo}</span>}
                {g.enlaces.map((e) => (
                  <Link key={e.texto} href={e.href} aria-current={activo(e.href) ? "page" : undefined}>
                    <Icono nombre={e.icono} />
                    <span>{e.texto}</span>
                  </Link>
                ))}
              </div>
            ))}
          </nav>

          <div className="cuenta-usuario">
            <span className="avatar" aria-hidden="true">{iniciales(usuario)}</span>
            <div className="datos-cuenta">
              <strong>{nombreVisible(usuario)}</strong>
              <span>{NOMBRE_ROL[usuario.rol]} · {usuario.username}</span>
            </div>
            <button type="button" className="boton-salir" onClick={cerrarSesion} title="Cerrar sesión">
              <Icono nombre="salir" />
              <span className="visualmente-oculto">Cerrar sesión</span>
            </button>
          </div>
        </div>
      </aside>

      <main className="principal">{children}</main>
    </div>
  );
}
