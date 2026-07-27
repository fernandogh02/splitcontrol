const API_BASE_URL = "http://127.0.0.1:8000/api";

let solicitudRenovacion = null;

const decodificarPayload = (token) => {
  try {
    const partePayload = token.split(".")[1];

    if (!partePayload) {
      return null;
    }

    const base64 = partePayload
      .replace(/-/g, "+")
      .replace(/_/g, "/");

    const relleno = "=".repeat(
      (4 - (base64.length % 4)) % 4
    );

    return JSON.parse(
      window.atob(base64 + relleno)
    );
  } catch {
    return null;
  }
};

export const limpiarSesion = () => {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  localStorage.removeItem("username");
};

const notificarSesionExpirada = () => {
  window.dispatchEvent(
    new CustomEvent("auth:expired")
  );
};

export const tokenEstaVencido = (token) => {
  if (!token) {
    return true;
  }

  const payload = decodificarPayload(token);

  if (!payload?.exp) {
    return true;
  }

  const margenSeguridad = 30;
  const tiempoActual = Math.floor(
    Date.now() / 1000
  );

  return (
    payload.exp <=
    tiempoActual + margenSeguridad
  );
};

export const renovarTokenAcceso = async () => {
  if (solicitudRenovacion) {
    return solicitudRenovacion;
  }

  solicitudRenovacion = (async () => {
    const refresh =
      localStorage.getItem("refresh");

    if (!refresh) {
      limpiarSesion();
      return null;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/token/refresh/`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            refresh,
          }),
        }
      );

      const data = await response
        .json()
        .catch(() => ({}));

      if (!response.ok || !data.access) {
        limpiarSesion();
        return null;
      }

      localStorage.setItem(
        "access",
        data.access
      );

      if (data.refresh) {
        localStorage.setItem(
          "refresh",
          data.refresh
        );
      }

      return data.access;
    } catch {
      return null;
    }
  })();

  try {
    return await solicitudRenovacion;
  } finally {
    solicitudRenovacion = null;
  }
};

export const asegurarTokenAcceso = async () => {
  const access =
    localStorage.getItem("access");

  if (
    access &&
    !tokenEstaVencido(access)
  ) {
    return access;
  }

  return renovarTokenAcceso();
};

const construirHeaders = (
  headersIniciales,
  token
) => {
  const headers = new Headers(
    headersIniciales || {}
  );

  headers.set(
    "Authorization",
    `Bearer ${token}`
  );

  return headers;
};

export const authFetch = async (
  recurso,
  opciones = {}
) => {
  let access =
    await asegurarTokenAcceso();

  if (!access) {
    limpiarSesion();
    notificarSesionExpirada();

    throw new Error(
      "Tu sesión ha expirado. Inicia sesión nuevamente."
    );
  }

  let response = await fetch(recurso, {
    ...opciones,
    headers: construirHeaders(
      opciones.headers,
      access
    ),
  });

  if (response.status !== 401) {
    return response;
  }

  access = await renovarTokenAcceso();

  if (!access) {
    limpiarSesion();
    notificarSesionExpirada();

    throw new Error(
      "Tu sesión ha expirado. Inicia sesión nuevamente."
    );
  }

  response = await fetch(recurso, {
    ...opciones,
    headers: construirHeaders(
      opciones.headers,
      access
    ),
  });

  if (response.status === 401) {
    limpiarSesion();
    notificarSesionExpirada();
  }

  return response;
};