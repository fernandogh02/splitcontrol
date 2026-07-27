import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";
import "../Notifications.css";

const formatearMonto = (monto) =>
  new Intl.NumberFormat("es-EC", {
    style: "currency",
    currency: "USD",
  }).format(Number(monto) || 0);

const obtenerConfiguracionEstado = (estado) => {
  if (estado === "programada") {
    return {
      texto: "Programada",
      clase: "bg-info text-dark",
    };
  }

  if (estado === "activa") {
    return {
      texto: "Activa",
      clase: "bg-success",
    };
  }

  if (estado === "cerrada") {
    return {
      texto: "Cerrada",
      clase: "bg-secondary",
    };
  }

  return {
    texto: "Sin configurar",
    clase: "bg-warning text-dark",
  };
};

function Dashboard() {
  const navigate = useNavigate();

  const [grupos, setGrupos] = useState([]);
  const [cargandoGrupos, setCargandoGrupos] = useState(true);
  const [errorGrupos, setErrorGrupos] = useState("");
  const [notificacionesNoLeidas, setNotificacionesNoLeidas] =
    useState(0);
  const [resumenDeudas, setResumenDeudas] = useState({
    total_deudas: 0,
    monto_total_pendiente: "0.00",
    deudas: [],
  });
  const [cargandoResumenDeudas, setCargandoResumenDeudas] =
    useState(true);
  const [errorResumenDeudas, setErrorResumenDeudas] =
    useState("");
  const [
    solicitudesPendientesRevision,
    setSolicitudesPendientesRevision,
  ] = useState(0);
  const [
    cargandoSolicitudesRevision,
    setCargandoSolicitudesRevision,
  ] = useState(true);
  const [
    errorSolicitudesRevision,
    setErrorSolicitudesRevision,
  ] = useState("");

  const username = localStorage.getItem("username") || "usuario";
  const displayName =
    username.charAt(0).toUpperCase() + username.slice(1);
  const avatarLetter = username.charAt(0).toUpperCase();

  const gruposResponsableDeudas = grupos.filter(
    (grupo) =>
      grupo.responsable_deudas?.username === username
  );

  const primerGrupoResponsable =
    gruposResponsableDeudas[0] || null;

  useEffect(() => {
    const obtenerGrupos = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        setErrorGrupos(
          "Tu sesión ha expirado. Inicia sesión nuevamente."
        );
        setCargandoGrupos(false);
        return;
      }

      try {
        setCargandoGrupos(true);
        setErrorGrupos("");

        const response = await fetch(
          "http://127.0.0.1:8000/api/grupos/",
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        let data = [];

        try {
          data = await response.json();
        } catch {
          data = [];
        }

        if (!response.ok) {
          throw new Error(
            data.error ||
              data.detail ||
              "No se pudieron cargar las actividades."
          );
        }

        setGrupos(
          Array.isArray(data) ? data : []
        );
      } catch (errorCarga) {
        setGrupos([]);
        setErrorGrupos(
          errorCarga.message ||
            "No se pudieron cargar tus actividades."
        );
      } finally {
        setCargandoGrupos(false);
      }
    };

    obtenerGrupos();
  }, []);

  useEffect(() => {
    const obtenerResumenDeudas = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        setErrorResumenDeudas(
          "Tu sesión ha expirado. Inicia sesión nuevamente."
        );
        setCargandoResumenDeudas(false);
        return;
      }

      try {
        setCargandoResumenDeudas(true);
        setErrorResumenDeudas("");

        const response = await fetch(
          "http://127.0.0.1:8000/api/mis-deudas/",
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
              "No se pudo consultar el resumen de tus deudas."
          );
        }

        setResumenDeudas({
          total_deudas: Number(data.total_deudas) || 0,
          monto_total_pendiente:
            data.monto_total_pendiente || "0.00",
          deudas: Array.isArray(data.deudas)
            ? data.deudas
            : [],
        });
      } catch (errorDeudas) {
        setResumenDeudas({
          total_deudas: 0,
          monto_total_pendiente: "0.00",
          deudas: [],
        });
        setErrorResumenDeudas(
          errorDeudas.message ||
            "No se pudo consultar el resumen de tus deudas."
        );
      } finally {
        setCargandoResumenDeudas(false);
      }
    };

    obtenerResumenDeudas();
  }, []);

  useEffect(() => {
    let efectoCancelado = false;

    const obtenerSolicitudesPendientes = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        if (!efectoCancelado) {
          setSolicitudesPendientesRevision(0);
          setCargandoSolicitudesRevision(false);
        }
        return;
      }

      const gruposAsignados = grupos.filter(
        (grupo) =>
          grupo.responsable_deudas?.username === username
      );

      if (gruposAsignados.length === 0) {
        if (!efectoCancelado) {
          setSolicitudesPendientesRevision(0);
          setErrorSolicitudesRevision("");
          setCargandoSolicitudesRevision(false);
        }
        return;
      }

      try {
        setCargandoSolicitudesRevision(true);
        setErrorSolicitudesRevision("");

        const resultados = await Promise.all(
          gruposAsignados.map(async (grupo) => {
            const response = await fetch(
              `http://127.0.0.1:8000/api/grupos/${grupo.id}/solicitudes-deuda/`,
              {
                method: "GET",
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            );

            const data = await response
              .json()
              .catch(() => ({}));

            if (!response.ok) {
              throw new Error(
                data.error ||
                  data.detail ||
                  `No se pudieron consultar las solicitudes de ${grupo.nombre}.`
              );
            }

            return Number(data.total_pendientes) || 0;
          })
        );

        if (!efectoCancelado) {
          setSolicitudesPendientesRevision(
            resultados.reduce(
              (total, cantidad) => total + cantidad,
              0
            )
          );
        }
      } catch (errorRevision) {
        if (!efectoCancelado) {
          setSolicitudesPendientesRevision(0);
          setErrorSolicitudesRevision(
            errorRevision.message ||
              "No se pudieron consultar las solicitudes pendientes."
          );
        }
      } finally {
        if (!efectoCancelado) {
          setCargandoSolicitudesRevision(false);
        }
      }
    };

    obtenerSolicitudesPendientes();

    return () => {
      efectoCancelado = true;
    };
  }, [grupos, username]);

  useEffect(() => {
    const obtenerContadorNotificaciones = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        setNotificacionesNoLeidas(0);
        return;
      }

      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/notificaciones/",
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
              "No se pudo consultar el contador."
          );
        }

        setNotificacionesNoLeidas(
          Number(data.no_leidas) || 0
        );
      } catch (errorNotificaciones) {
        console.error(
          "No se pudo cargar el contador de notificaciones:",
          errorNotificaciones
        );
        setNotificacionesNoLeidas(0);
      }
    };

    obtenerContadorNotificaciones();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("username");
    navigate("/login");
  };

  const goToCreateGroup = () => {
    navigate("/grupos/crear");
  };

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div>
          <div className="sidebar-logo">
            <img src={logo} alt="SplitControl" />
          </div>

          <nav className="sidebar-menu">
            <button className="sidebar-link active">
              ▦ Dashboard
            </button>

            <button
              className="sidebar-link"
              onClick={goToCreateGroup}
            >
              👥 Grupos
            </button>

            <button
              className="sidebar-link"
              onClick={() => navigate("/mis-deudas")}
            >
              💳 Mis deudas
            </button>

            <button
              className="sidebar-link"
              onClick={() => navigate("/notificaciones")}
            >
              🔔 Notificaciones
              {notificacionesNoLeidas > 0 && (
                <span className="sidebar-notification-count">
                  {notificacionesNoLeidas > 99
                    ? "99+"
                    : notificacionesNoLeidas}
                </span>
              )}
            </button>

          </nav>
        </div>

        <div className="sidebar-bottom">
          <button
            type="button"
            className="btn btn-primary w-100 mb-3"
            onClick={() => navigate("/mis-deudas")}
          >
            Consultar mis deudas
          </button>

          <div className="user-box">
            <div className="avatar">
              {avatarLetter}
            </div>

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
        <header className="dashboard-header">
          <div>
            <h1>Panel General</h1>

            <p>
              Hola {displayName}, aquí puedes consultar tus
              actividades creadas y compartidas.
            </p>
          </div>

          <div className="header-actions">
            <button
              type="button"
              className="icon-button notification-bell-button"
              onClick={() => navigate("/notificaciones")}
              aria-label={`Abrir notificaciones. ${notificacionesNoLeidas} no leídas`}
              title="Centro de notificaciones"
            >
              🔔

              {notificacionesNoLeidas > 0 && (
                <span className="notification-count-badge">
                  {notificacionesNoLeidas > 99
                    ? "99+"
                    : notificacionesNoLeidas}
                </span>
              )}
            </button>

          </div>
        </header>

        <section className="summary-grid">
          <div className="summary-card debt">
            <div className="summary-icon red">
              ▣
            </div>

            <div className="w-100">
              <span>Mis obligaciones pendientes</span>

              <h2>
                {cargandoResumenDeudas
                  ? "Consultando..."
                  : formatearMonto(
                      resumenDeudas.monto_total_pendiente
                    )}
              </h2>

              <p>
                {cargandoResumenDeudas
                  ? "Cargando tu información económica"
                  : resumenDeudas.total_deudas > 0
                    ? `${resumenDeudas.total_deudas} deuda${
                        resumenDeudas.total_deudas === 1
                          ? ""
                          : "s"
                      } registrada${
                        resumenDeudas.total_deudas === 1
                          ? ""
                          : "s"
                      }`
                    : "No tienes deudas registradas"}
              </p>

              <button
                type="button"
                className="btn btn-outline-danger btn-sm"
                onClick={() => navigate("/mis-deudas")}
              >
                Ver mis deudas
              </button>
            </div>
          </div>

          <div className="summary-card income">
            <div className="summary-icon green">
              ✓
            </div>

            <div className="w-100">
              <span>Solicitudes por revisar</span>

              <h2>
                {cargandoSolicitudesRevision
                  ? "Consultando..."
                  : solicitudesPendientesRevision}
              </h2>

              <p>
                {gruposResponsableDeudas.length > 0
                  ? `Responsable en ${
                      gruposResponsableDeudas.length
                    } actividad${
                      gruposResponsableDeudas.length === 1
                        ? ""
                        : "es"
                    }`
                  : "No tienes revisiones asignadas"}
              </p>

              <button
                type="button"
                className="btn btn-outline-success btn-sm"
                onClick={() =>
                  primerGrupoResponsable &&
                  navigate(
                    `/grupos/${primerGrupoResponsable.id}/solicitudes-deuda`
                  )
                }
                disabled={!primerGrupoResponsable}
              >
                Revisar solicitudes
              </button>
            </div>
          </div>
        </section>

        {(errorResumenDeudas ||
          errorSolicitudesRevision) && (
          <div
            className="alert alert-warning mt-3"
            role="alert"
          >
            {errorResumenDeudas ||
              errorSolicitudesRevision}
          </div>
        )}

        <section className="quick-actions">
          <button
            className="btn btn-outline-primary"
            onClick={goToCreateGroup}
          >
            👥 Crear grupo
          </button>

          <button
            className="btn btn-outline-primary"
            onClick={() => navigate("/mis-deudas")}
          >
            💳 Mis deudas
          </button>

          <button
            className="btn btn-outline-primary"
            onClick={() => navigate("/notificaciones")}
          >
            🔔 Notificaciones
          </button>

          <button
            className="btn btn-outline-success"
            onClick={() =>
              primerGrupoResponsable &&
              navigate(
                `/grupos/${primerGrupoResponsable.id}/solicitudes-deuda`
              )
            }
            disabled={!primerGrupoResponsable}
          >
            ✓ Revisar solicitudes
          </button>

          <button
            className="btn btn-outline-primary"
            onClick={() => navigate("/resumen")}
          >
            📊 Ver resumen
          </button>
        </section>

        <section
          className="dashboard-content"
          style={{
            gridTemplateColumns: "minmax(0, 1fr)",
          }}
        >
          <div
            className="groups-section"
            style={{
              width: "100%",
              minWidth: 0,
            }}
          >
            <div className="section-title">
              <div>
                <h3 className="mb-1">
                  Mis actividades
                </h3>

                <small className="text-muted">
                  Creadas por ti o compartidas contigo
                </small>
              </div>

              <button onClick={goToCreateGroup}>
                Crear nueva
              </button>
            </div>

            {cargandoGrupos ? (
              <div className="empty-groups-card">
                <h5>Cargando actividades...</h5>

                <p>
                  Estamos consultando tus actividades
                  disponibles.
                </p>
              </div>
            ) : errorGrupos ? (
              <div className="empty-groups-card">
                <h5>
                  No se pudieron cargar las actividades
                </h5>

                <p>{errorGrupos}</p>

                <button
                  className="btn btn-primary"
                  onClick={goToCreateGroup}
                >
                  Crear actividad
                </button>
              </div>
            ) : grupos.length === 0 ? (
              <div className="empty-groups-card">
                <h5>
                  No tienes actividades disponibles
                </h5>

                <p>
                  Crea una actividad o espera a que otro usuario
                  te agregue como participante.
                </p>

                <button
                  className="btn btn-primary"
                  onClick={goToCreateGroup}
                >
                  Crear actividad
                </button>
              </div>
            ) : (
              grupos.map((grupo) => {
                const esCreador =
                  grupo.creador_username === username;

                const configuracionEstado =
                  obtenerConfiguracionEstado(
                    grupo.estado
                  );

                return (
                  <div
                    className="group-card"
                    key={grupo.id}
                    onClick={() =>
                      navigate(`/grupos/${grupo.id}`)
                    }
                    style={{ cursor: "pointer" }}
                  >
                    <div className="group-image beach" />

                    <div className="group-info">
                      <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
                        <strong>{grupo.nombre}</strong>

                        <span
                          className={`badge ${
                            esCreador
                              ? "bg-primary"
                              : "bg-dark"
                          }`}
                        >
                          {esCreador
                            ? "Creador"
                            : "Participante"}
                        </span>

                        <span
                          className={`badge ${configuracionEstado.clase}`}
                        >
                          {configuracionEstado.texto}
                        </span>

                        {grupo.responsable_deudas?.username ===
                          username && (
                          <span className="badge bg-warning text-dark">
                            Responsable de deudas
                          </span>
                        )}
                      </div>

                      <small>
                        Creado por{" "}
                        <strong>
                          @{grupo.creador_username}
                        </strong>
                      </small>

                      <small>
                        Fecha de creación:{" "}
                        {grupo.fecha_creacion
                          ? new Date(
                              grupo.fecha_creacion
                            ).toLocaleDateString(
                              "es-EC"
                            )
                          : "Sin fecha"}
                      </small>

                      <span>
                        {grupo.descripcion ||
                          "Sin descripción"}
                      </span>

                      <small className="text-muted">
                        Participantes actuales:{" "}
                        {grupo.participantes?.length || 0}
                      </small>
                    </div>

                    <div className="text-end">
                      <strong className="amount neutral">
                        {formatearMonto(grupo.total_gastos)}
                      </strong>

                      <small className="text-muted d-block">
                        Total de gastos
                      </small>

                      <small className="text-muted d-block mt-2">
                        Ver actividad →
                      </small>
                    </div>
                  </div>
                );
              })
            )}
          </div>

        </section>
      </main>
    </div>
  );
}

export default Dashboard;