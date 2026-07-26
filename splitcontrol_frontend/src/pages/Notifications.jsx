import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";
import "../Notifications.css";

const API_NOTIFICACIONES =
  "http://127.0.0.1:8000/api/notificaciones/";

const formatearFechaHora = (fecha) => {
  if (!fecha) {
    return "Sin fecha";
  }

  return new Date(fecha).toLocaleString("es-EC", {
    dateStyle: "medium",
    timeStyle: "short",
  });
};

function Notifications() {
  const navigate = useNavigate();

  const [notificaciones, setNotificaciones] = useState([]);
  const [totalNotificaciones, setTotalNotificaciones] = useState(0);
  const [noLeidas, setNoLeidas] = useState(0);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(true);
  const [marcandoTodas, setMarcandoTodas] = useState(false);
  const [notificacionActualizando, setNotificacionActualizando] =
    useState(null);

  const username = localStorage.getItem("username") || "usuario";
  const displayName =
    username.charAt(0).toUpperCase() + username.slice(1);
  const avatarLetter = username.charAt(0).toUpperCase();

  const obtenerNotificaciones = useCallback(async () => {
    const token = localStorage.getItem("access");

    if (!token) {
      setError(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      setCargando(false);
      return;
    }

    try {
      setCargando(true);
      setError("");

      const response = await fetch(
        API_NOTIFICACIONES,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      let data = {};

      try {
        data = await response.json();
      } catch {
        data = {};
      }

      if (!response.ok) {
        throw new Error(
          data.error ||
            data.detail ||
            "No se pudieron cargar las notificaciones."
        );
      }

      setNotificaciones(
        Array.isArray(data.notificaciones)
          ? data.notificaciones
          : []
      );

      setTotalNotificaciones(
        Number(data.total_notificaciones) || 0
      );

      setNoLeidas(
        Number(data.no_leidas) || 0
      );

      setMensaje(data.mensaje || "");
    } catch (errorCarga) {
      setNotificaciones([]);
      setTotalNotificaciones(0);
      setNoLeidas(0);
      setMensaje("");
      setError(
        errorCarga.message ||
          "No se pudieron cargar tus notificaciones."
      );
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    const temporizador = setTimeout(() => {
      obtenerNotificaciones();
    }, 0);

    return () => {
      clearTimeout(temporizador);
    };
  }, [obtenerNotificaciones]);

  const marcarComoLeida = async (notificacion) => {
    if (notificacion.leida) {
      return true;
    }

    const token = localStorage.getItem("access");

    if (!token) {
      setError(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      return false;
    }

    try {
      setNotificacionActualizando(notificacion.id);
      setError("");

      const response = await fetch(
        `${API_NOTIFICACIONES}${notificacion.id}/leer/`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({}),
        }
      );

      let data = {};

      try {
        data = await response.json();
      } catch {
        data = {};
      }

      if (!response.ok) {
        throw new Error(
          data.error ||
            data.detail ||
            "No se pudo marcar la notificación como leída."
        );
      }

      const notificacionLeida =
        data.notificacion || {
          ...notificacion,
          leida: true,
          estado: "leida",
          fecha_lectura: new Date().toISOString(),
        };

      setNotificaciones((notificacionesActuales) =>
        notificacionesActuales.map((item) =>
          item.id === notificacion.id
            ? notificacionLeida
            : item
        )
      );

      setNoLeidas(Number(data.no_leidas) || 0);
      setMensaje(data.mensaje || "");

      return true;
    } catch (errorLectura) {
      setError(
        errorLectura.message ||
          "No se pudo actualizar la notificación."
      );

      return false;
    } finally {
      setNotificacionActualizando(null);
    }
  };

  const marcarTodasComoLeidas = async () => {
    const token = localStorage.getItem("access");

    if (!token) {
      setError(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      return;
    }

    try {
      setMarcandoTodas(true);
      setError("");

      const response = await fetch(
        `${API_NOTIFICACIONES}marcar-todas-leidas/`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({}),
        }
      );

      let data = {};

      try {
        data = await response.json();
      } catch {
        data = {};
      }

      if (!response.ok) {
        throw new Error(
          data.error ||
            data.detail ||
            "No se pudieron actualizar las notificaciones."
        );
      }

      const fechaLectura = new Date().toISOString();

      setNotificaciones((notificacionesActuales) =>
        notificacionesActuales.map((item) => ({
          ...item,
          leida: true,
          estado: "leida",
          fecha_lectura:
            item.fecha_lectura || fechaLectura,
        }))
      );

      setNoLeidas(0);
      setMensaje(data.mensaje || "");
    } catch (errorLectura) {
      setError(
        errorLectura.message ||
          "No se pudieron marcar todas como leídas."
      );
    } finally {
      setMarcandoTodas(false);
    }
  };

  const abrirNotificacion = async (notificacion) => {
    const actualizada = await marcarComoLeida(
      notificacion
    );

    if (!actualizada || !notificacion.enlace) {
      return;
    }

    if (notificacion.enlace.startsWith("/")) {
      navigate(notificacion.enlace);
      return;
    }

    window.location.assign(notificacion.enlace);
  };

  const handleLogout = () => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("username");
    navigate("/login");
  };

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div>
          <div className="sidebar-logo">
            <img src={logo} alt="SplitControl" />
          </div>

          <nav className="sidebar-menu">
            <button
              className="sidebar-link"
              onClick={() => navigate("/dashboard")}
            >
              ▦ Dashboard
            </button>

            <button
              className="sidebar-link"
              onClick={() => navigate("/dashboard")}
            >
              👥 Grupos
            </button>

            <button className="sidebar-link active">
              🔔 Notificaciones
              {noLeidas > 0 && (
                <span className="sidebar-notification-count">
                  {noLeidas > 99 ? "99+" : noLeidas}
                </span>
              )}
            </button>

            <button className="sidebar-link">
              ↺ Historial
            </button>

            <button className="sidebar-link">
              ♙ Perfil
            </button>
          </nav>
        </div>

        <div className="sidebar-bottom">
          <div className="user-box">
            <div className="avatar">{avatarLetter}</div>

            <div>
              <strong>{displayName}</strong>
              <small>@{username}</small>
            </div>
          </div>

          <button
            className="btn btn-outline-danger w-100 mt-3"
            onClick={handleLogout}
          >
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="dashboard-main">
        <header className="notifications-page-header">
          <div>
            <button
              type="button"
              className="back-button mb-3"
              onClick={() => navigate("/dashboard")}
            >
              ← Volver al dashboard
            </button>

            <h1>Centro de notificaciones</h1>

            <p>
              Revisa las novedades relacionadas con tus
              actividades y movimientos.
            </p>
          </div>

          <div className="notifications-header-actions">
            <button
              type="button"
              className="btn btn-outline-primary"
              onClick={obtenerNotificaciones}
              disabled={cargando}
            >
              {cargando ? "Actualizando..." : "Actualizar"}
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={marcarTodasComoLeidas}
              disabled={
                marcandoTodas ||
                noLeidas === 0
              }
            >
              {marcandoTodas
                ? "Marcando..."
                : "Marcar todas como leídas"}
            </button>
          </div>
        </header>

        <section className="notifications-summary-grid">
          <div className="notifications-summary-card">
            <small>Total de notificaciones</small>
            <strong>{totalNotificaciones}</strong>
          </div>

          <div className="notifications-summary-card unread">
            <small>No leídas</small>
            <strong>{noLeidas}</strong>
          </div>
        </section>

        {mensaje && !error && (
          <div
            className="alert alert-info"
            role="alert"
          >
            {mensaje}
          </div>
        )}

        {error && (
          <div
            className="alert alert-danger"
            role="alert"
          >
            {error}
          </div>
        )}

        <section className="notifications-panel">
          {cargando ? (
            <div className="notifications-empty">
              <h4>Cargando notificaciones...</h4>
              <p>
                Estamos consultando tus novedades más recientes.
              </p>
            </div>
          ) : notificaciones.length === 0 ? (
            <div className="notifications-empty">
              <div className="notifications-empty-icon">
                🔔
              </div>

              <h4>No tienes notificaciones todavía</h4>

              <p>
                Cuando exista una novedad relacionada con tus
                actividades, aparecerá en esta sección.
              </p>
            </div>
          ) : (
            <div className="notifications-list">
              {notificaciones.map((notificacion) => (
                <article
                  key={notificacion.id}
                  className={`notification-item ${
                    notificacion.leida
                      ? "read"
                      : "unread"
                  }`}
                >
                  <div className="notification-item-icon">
                    {notificacion.leida ? "✓" : "🔔"}
                  </div>

                  <div className="notification-item-content">
                    <div className="notification-item-heading">
                      <div>
                        <div className="d-flex flex-wrap align-items-center gap-2">
                          <h4>{notificacion.titulo}</h4>

                          <span
                            className={`badge ${
                              notificacion.leida
                                ? "bg-secondary"
                                : "bg-primary"
                            }`}
                          >
                            {notificacion.leida
                              ? "Leída"
                              : "No leída"}
                          </span>
                        </div>

                        <small>
                          {formatearFechaHora(
                            notificacion.fecha_creacion
                          )}
                        </small>
                      </div>

                      {!notificacion.leida && (
                        <span
                          className="notification-unread-dot"
                          aria-label="Notificación no leída"
                        />
                      )}
                    </div>

                    <p>{notificacion.mensaje}</p>

                    {notificacion.leida &&
                      notificacion.fecha_lectura && (
                        <small className="notification-read-date">
                          Leída el{" "}
                          {formatearFechaHora(
                            notificacion.fecha_lectura
                          )}
                        </small>
                      )}

                    <div className="notification-item-actions">
                      {!notificacion.leida && (
                        <button
                          type="button"
                          className="btn btn-outline-primary btn-sm"
                          onClick={() =>
                            marcarComoLeida(notificacion)
                          }
                          disabled={
                            notificacionActualizando ===
                            notificacion.id
                          }
                        >
                          {notificacionActualizando ===
                          notificacion.id
                            ? "Marcando..."
                            : "Marcar como leída"}
                        </button>
                      )}

                      {notificacion.enlace && (
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={() =>
                            abrirNotificacion(notificacion)
                          }
                          disabled={
                            notificacionActualizando ===
                            notificacion.id
                          }
                        >
                          Abrir recurso relacionado
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default Notifications;