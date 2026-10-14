const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000/api";

type LoginResponse = {
  access: string;
  refresh: string;
};

type RegisterData = {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  documento?: string;
  telefono?: string;
};

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/auth/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      password,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail || "Usuario o contraseña incorrectos"
    );
  }

  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);

  return data;
}

export async function register(
  data: RegisterData
) {
  const response = await fetch(
    `${API_URL}/auth/register/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    }
  );

  const result = await response.json();

  if (!response.ok) {
    const errors = Object.values(result);

    const firstError = errors[0];

    if (Array.isArray(firstError)) {
      throw new Error(String(firstError[0]));
    }

    throw new Error(
      "No se pudo crear la cuenta"
    );
  }

  return result;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export function getAccessToken() {
  if (typeof window === "undefined") {
    return null;
  }

  return localStorage.getItem("access_token");
}

export function isAuthenticated() {
  return Boolean(getAccessToken());
}

export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
) {
  const token = getAccessToken();

  const headers = new Headers(options.headers);

  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set(
      "Authorization",
      `Bearer ${token}`
    );
  }

  const response = await fetch(
    `${API_URL}${endpoint}`,
    {
      ...options,
      headers,
    }
  );

  if (response.status === 401) {
    logout();

    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  return response;
}