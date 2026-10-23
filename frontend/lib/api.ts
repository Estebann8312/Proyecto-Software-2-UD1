// ---------------------------------------------------------------------------
// Cliente de la API de Django
// - Guarda los tokens JWT y los renueva solo cuando el de acceso vence.
// - Convierte cualquier error de DRF en un mensaje legible.
// - Define los tipos de lo que devuelve el backend.
// ---------------------------------------------------------------------------

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

/** Evento que se emite cuando la sesión vence y no se pudo renovar. */
export const EVENTO_SESION_EXPIRADA = "sesion-expirada";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export type Rol = "administrador" | "vendedor" | "cliente";

export type Me = {
  username: string;
  email: string;
  nombres: string;
  apellidos: string;
  rol: Rol;
  id_usuario: number | null;
  id_cliente: number | null;
};

export type Condicion = "nueva" | "reacondicionada";

export type MetodoPago =
  | "efectivo"
  | "tarjeta_debito"
  | "tarjeta_credito"
  | "transferencia";

export type Categoria = {
  id_categoria: number;
  nombre: string;
};

/** Lo que ve un cliente o un visitante: sin stock exacto ni costos. */
export type PiezaPublica = {
  id_pieza: number;
  nombre: string;
  categoria_nombre: string;
  condicion: Condicion;
  precio_venta: string;
  descripcion: string | null;
  en_stock: boolean;
};

export type Lote = {
  id_lote: number;
  id_proveedor: number;
  id_pieza: number;
  cantidad: number;
  costo_unitario: string;
  fecha_compra: string;
};

/** Lo que ve un empleado: stock real e historial de lotes. */
export type Pieza = {
  id_pieza: number;
  nombre: string;
  id_categoria: number;
  condicion: Condicion;
  precio_venta: string;
  stock_actual: number;
  descripcion: string | null;
  lotes: Lote[];
};

export type Proveedor = {
  id_proveedor: number;
  nombre: string;
  telefono: string | null;
  contacto: string | null;
};

export type Cliente = {
  id_cliente: number;
  user: number | null;
  nombres: string;
  apellidos: string;
  documento: string | null;
  telefono: string | null;
  email: string | null;
  fecha_registro: string;
};

export type Empleado = {
  id_usuario: number;
  username: string;
  nombres: string;
  apellidos: string;
  documento: string | null;
  telefono: string | null;
  email: string;
  rol: Exclude<Rol, "cliente">;
  fecha_registro: string;
};

export type DetalleVenta = {
  id_pieza: number;
  pieza_nombre: string;
  cantidad: number;
  precio_unitario: string;
  subtotal: string;
};

export type Venta = {
  id_venta: number;
  id_cliente: number;
  id_vendedor: number;
  fecha: string;
  metodo_pago: MetodoPago;
  total: string;
  estado: "activa" | "anulada";
  detalles: DetalleVenta[];
};

export type RegistroData = {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  documento?: string;
  telefono?: string;
};

// ---------------------------------------------------------------------------
// Tokens
// ---------------------------------------------------------------------------

const ACCESS = "access_token";
const REFRESH = "refresh_token";

function leer(clave: string) {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(clave);
}

function guardarTokens(access: string, refresh?: string) {
  localStorage.setItem(ACCESS, access);
  if (refresh) localStorage.setItem(REFRESH, refresh);
}

export function logout() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
}

export function getAccessToken() {
  return leer(ACCESS);
}

/**
 * Hay sesión si existe el token de renovación (dura 1 día).
 * El de acceso dura 5 minutos y se renueva solo en apiFetch.
 */
export function isAuthenticated() {
  return Boolean(leer(REFRESH));
}

// ---------------------------------------------------------------------------
// Errores
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, data: unknown) {
    super(mensajeDeError(data, status));
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

/**
 * DRF responde errores con formas distintas:
 *   {"detail": "..."}              {"error": "..."}
 *   {"email": ["Ya existe..."]}    {"detalles": "Stock insuficiente..."}
 *   {"password": ["a", "b"]}       ["mensaje"]
 * Esta función devuelve el primer mensaje legible que encuentre.
 */
export function mensajeDeError(data: unknown, status = 400): string {
  const primero = (valor: unknown): string | null => {
    if (typeof valor === "string") return valor;
    if (Array.isArray(valor)) {
      for (const item of valor) {
        const m = primero(item);
        if (m) return m;
      }
    }
    if (valor && typeof valor === "object") {
      const obj = valor as Record<string, unknown>;
      for (const clave of ["detail", "error", "mensaje", "non_field_errors"]) {
        if (clave in obj) {
          const m = primero(obj[clave]);
          if (m) return m;
        }
      }
      for (const v of Object.values(obj)) {
        const m = primero(v);
        if (m) return m;
      }
    }
    return null;
  };

  const mensaje = primero(data);
  if (mensaje) return mensaje;
  if (status === 429) return "Demasiados intentos. Espera un minuto.";
  if (status >= 500) return "El servidor tuvo un problema. Intenta de nuevo.";
  return "No se pudo completar la solicitud.";
}

// ---------------------------------------------------------------------------
// Peticiones
// ---------------------------------------------------------------------------

async function leerCuerpo(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const texto = await response.text();
  if (!texto) return null;
  try {
    return JSON.parse(texto);
  } catch {
    return texto;
  }
}

// Si varias peticiones vencen a la vez, todas esperan la misma renovación.
let renovando: Promise<boolean> | null = null;

async function renovarAccess(): Promise<boolean> {
  const refresh = leer(REFRESH);
  if (!refresh) return false;

  if (!renovando) {
    renovando = fetch(`${API_URL}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })
      .then(async (r) => {
        if (!r.ok) return false;
        const data = (await r.json()) as { access: string; refresh?: string };
        guardarTokens(data.access, data.refresh);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        renovando = null;
      });
  }
  return renovando;
}

function sesionExpirada() {
  logout();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(EVENTO_SESION_EXPIRADA));
  }
}

/** fetch con el token; si el de acceso venció, lo renueva y reintenta una vez. */
export async function apiFetch(
  endpoint: string,
  options: RequestInit = {},
  reintento = true
): Promise<Response> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });

  if (response.status === 401 && token && reintento) {
    if (await renovarAccess()) {
      return apiFetch(endpoint, options, false);
    }
    sesionExpirada();
  }
  return response;
}

/** Petición que devuelve JSON tipado o lanza ApiError con un mensaje legible. */
export async function api<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetch(endpoint, options);
  const data = await leerCuerpo(response);
  if (!response.ok) throw new ApiError(response.status, data);
  return data as T;
}

/** Atajo para enviar un objeto como JSON. */
export function enviar<T>(endpoint: string, metodo: "POST" | "PATCH" | "PUT" | "DELETE", cuerpo?: unknown) {
  return api<T>(endpoint, {
    method: metodo,
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });
}

// ---------------------------------------------------------------------------
// Autenticación
// ---------------------------------------------------------------------------

export async function login(username: string, password: string): Promise<Rol> {
  const response = await fetch(`${API_URL}/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await leerCuerpo(response);

  if (!response.ok) {
    if (response.status === 401) {
      throw new ApiError(401, "Usuario o contraseña incorrectos.");
    }
    throw new ApiError(response.status, data);
  }

  const tokens = data as { access: string; refresh: string; rol: Rol };
  guardarTokens(tokens.access, tokens.refresh);
  return tokens.rol;
}

export async function register(datos: RegistroData) {
  const response = await fetch(`${API_URL}/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  });
  const data = await leerCuerpo(response);
  if (!response.ok) throw new ApiError(response.status, data);
  return data as { message: string; username: string };
}

export function obtenerMe() {
  return api<Me>("/auth/me/");
}
