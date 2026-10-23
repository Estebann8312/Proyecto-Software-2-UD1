"use client";

// ---------------------------------------------------------------------------
// Sesión compartida
// Un solo lugar sabe quién está conectado y con qué rol. Las páginas lo leen
// con useSession() en lugar de revisar el token cada una por su cuenta.
// ---------------------------------------------------------------------------

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";
import { useRouter } from "next/navigation";

import {
  EVENTO_SESION_EXPIRADA,
  isAuthenticated,
  login,
  logout,
  obtenerMe,
  type Me,
  type Rol,
} from "./api";

const EVENTO_SESION_CAMBIO = "sesion-cambio";

type Estado = "cargando" | "anonimo" | "autenticado";

type Sesion = {
  estado: Estado;
  usuario: Me | null;
  iniciarSesion: (username: string, password: string) => Promise<Me>;
  cerrarSesion: () => void;
};

const SesionContext = createContext<Sesion | null>(null);

// --- ¿Hay tokens guardados? (se lee de localStorage, solo en el navegador) ---

function suscribir(avisar: () => void) {
  window.addEventListener("storage", avisar); // otra pestaña inició o cerró sesión
  window.addEventListener(EVENTO_SESION_CAMBIO, avisar);
  window.addEventListener(EVENTO_SESION_EXPIRADA, avisar);
  return () => {
    window.removeEventListener("storage", avisar);
    window.removeEventListener(EVENTO_SESION_CAMBIO, avisar);
    window.removeEventListener(EVENTO_SESION_EXPIRADA, avisar);
  };
}

function avisarCambio() {
  window.dispatchEvent(new Event(EVENTO_SESION_CAMBIO));
}

// En el servidor no hay localStorage: null significa "todavía no se sabe".
const leerEnServidor = () => null;

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const haySesion = useSyncExternalStore<boolean | null>(
    suscribir,
    isAuthenticated,
    leerEnServidor
  );
  const [usuario, setUsuario] = useState<Me | null>(null);

  // Al abrir la app con una sesión guardada, se pregunta al backend quién es.
  useEffect(() => {
    if (!haySesion || usuario) return;
    let activo = true;
    obtenerMe()
      .then((me) => {
        if (activo) setUsuario(me);
      })
      .catch(() => {
        // Token inválido o backend caído: se trata como sesión cerrada.
        if (activo) {
          logout();
          avisarCambio();
        }
      });
    return () => {
      activo = false;
    };
  }, [haySesion, usuario]);

  // Si la sesión vence en medio del uso, vuelve al login.
  useEffect(() => {
    const alExpirar = () => {
      setUsuario(null);
      router.replace("/login");
    };
    window.addEventListener(EVENTO_SESION_EXPIRADA, alExpirar);
    return () => window.removeEventListener(EVENTO_SESION_EXPIRADA, alExpirar);
  }, [router]);

  const iniciarSesion = useCallback(async (username: string, password: string) => {
    await login(username, password);
    const me = await obtenerMe();
    setUsuario(me);
    avisarCambio();
    return me;
  }, []);

  const cerrarSesion = useCallback(() => {
    logout();
    setUsuario(null);
    avisarCambio();
    router.replace("/login");
  }, [router]);

  const estado: Estado =
    haySesion === null
      ? "cargando"
      : !haySesion
        ? "anonimo"
        : usuario
          ? "autenticado"
          : "cargando";

  const valor = useMemo(
    () => ({
      estado,
      usuario: haySesion ? usuario : null,
      iniciarSesion,
      cerrarSesion,
    }),
    [estado, haySesion, usuario, iniciarSesion, cerrarSesion]
  );

  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>;
}

export function useSession() {
  const sesion = useContext(SesionContext);
  if (!sesion) {
    throw new Error("useSession debe usarse dentro de <SessionProvider>.");
  }
  return sesion;
}

/**
 * Para páginas protegidas: si no hay sesión manda al login y, si el rol no
 * está permitido, manda al inicio. Devuelve el usuario cuando ya puede mostrarse.
 */
export function useRequiereSesion(roles?: Rol[]) {
  const { estado, usuario } = useSession();
  const router = useRouter();
  const permitido = !roles || (usuario !== null && roles.includes(usuario.rol));

  useEffect(() => {
    if (estado === "anonimo") router.replace("/login");
    else if (estado === "autenticado" && !permitido) router.replace("/dashboard");
  }, [estado, permitido, router]);

  return estado === "autenticado" && permitido ? usuario : null;
}

/** Nombre corto para mostrar: "Carlos Mendoza" o, si no hay nombre, el usuario. */
export function nombreVisible(me: Me) {
  const nombre = me.nombres.split(" ")[0];
  const apellido = me.apellidos.split(" ")[0];
  return [nombre, apellido].filter(Boolean).join(" ") || me.username;
}

export const NOMBRE_ROL: Record<Rol, string> = {
  administrador: "Administrador",
  vendedor: "Vendedor",
  cliente: "Cliente",
};
