import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";
import {
  authFetch,
  limpiarSesion,
} from "../utils/authFetch";

const API_BASE_URL = "http://127.0.0.1:8000/api";
const SERVIDOR_BASE_URL = "http://127.0.0.1:8000";

const formatearMonto = (monto) =>
  new Intl.NumberFormat("es-EC", {
    style: "currency",
    currency: "USD",
  }).format(Number(monto) || 0);

const formatearFechaHora = (fecha) => {
  if (!fecha) {
    return "Sin fecha";
  }

  const fechaConvertida = new Date(fecha);

  if (Number.isNaN(fechaConvertida.getTime())) {
    return "Sin fecha";
  }

  return fechaConvertida.toLocaleString("es-EC", {
    dateStyle: "medium",
    timeStyle: "short",
  });
};

const leerJsonSeguro = async (response) =>
  response.json().catch(() => ({}));

const obtenerMensajeError = (
  data,
  mensajePredeterminado = "No se pudo completar la operación."
) => {
  if (!data || typeof data !== "object") {
    return mensajePredeterminado;
  }

  if (data.error) {
    return Array.isArray(data.error)
      ? String(data.error[0])
      : String(data.error);
  }

  if (data.detail) {
    return String(data.detail);
  }

  const primeraClave = Object.keys(data)[0];

  if (!primeraClave) {
    return mensajePredeterminado;
  }

  const detalle = data[primeraClave];

  if (Array.isArray(detalle)) {
    return String(detalle[0]);
  }

  if (typeof detalle === "object" && detalle !== null) {
    const subClave = Object.keys(detalle)[0];

    if (!subClave) {
      return mensajePredeterminado;
    }

    const subDetalle = detalle[subClave];

    return Array.isArray(subDetalle)
      ? String(subDetalle[0])
      : String(subDetalle);
  }

  return String(detalle);
};

const construirUrlEvidencia = (evidencia) => {
  if (!evidencia) {
    return "";
  }

  if (
    evidencia.startsWith("http://") ||
    evidencia.startsWith("https://")
  ) {
    return evidencia;
  }

  return evidencia.startsWith("/")
    ? `${SERVIDOR_BASE_URL}${evidencia}`
    : `${SERVIDOR_BASE_URL}/${evidencia}`;
};

const obtenerNombreUsuario = (usuario) =>
  usuario?.nombre_completo ||
  usuario?.username ||
  "Usuario";

const obtenerConfiguracionActividad = (estado) => {
  if (estado === "cerrada") {
    return {
      texto: "Cerrada",
      clase: "bg-secondary",
    };
  }

  if (estado === "activa") {
    return {
      texto: "Activa",
      clase: "bg-success",
    };
  }

  if (estado === "programada") {
    return {
      texto: "Programada",
      clase: "bg-info text-dark",
    };
  }

  return {
    texto: "Sin configurar",
    clase: "bg-warning text-dark",
  };
};

function DebtResolutionReview() {
  const navigate = useNavigate();
  const { id } = useParams();

  const [grupoNombre, setGrupoNombre] = useState("");
  const [estadoActividad, setEstadoActividad] = useState("");
  const [responsable, setResponsable] = useState(null);
  const [solicitudes, setSolicitudes] = useState([]);
  const [totalSolicitudes, setTotalSolicitudes] = useState(0);
  const [totalPendientes, setTotalPendientes] = useState(0);
  const [mensajeListado, setMensajeListado] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  const [modalAbierto, setModalAbierto] = useState(false);
  const [solicitudSeleccionada, setSolicitudSeleccionada] =
    useState(null);
  const [decision, setDecision] = useState("");
  const [observacion, setObservacion] = useState("");
  const [errorDecision, setErrorDecision] = useState("");
  const [guardandoDecision, setGuardandoDecision] =
    useState(false);
  const [resultadoDecision, setResultadoDecision] =
    useState(null);

  const username =
    localStorage.getItem("username") || "usuario";
  const displayName =
    username.charAt(0).toUpperCase() + username.slice(1);
  const avatarLetter = username.charAt(0).toUpperCase();

  const obtenerSolicitudes = useCallback(async () => {
    try {
      setCargando(true);
      setError("");

      const response = await authFetch(
        `${API_BASE_URL}/grupos/${id}/solicitudes-deuda/`,
        {
          method: "GET",
        }
      );

      const data = await leerJsonSeguro(response);

      if (!response.ok) {
        throw new Error(
          obtenerMensajeError(
            data,
            "No se pudieron cargar las solicitudes."
          )
        );
      }

      setGrupoNombre(data.grupo_nombre || "");
      setEstadoActividad(data.estado_actividad || "");
      setResponsable(data.responsable || null);
      setTotalSolicitudes(
        Number(data.total_solicitudes) || 0
      );
      setTotalPendientes(
        Number(data.total_pendientes) || 0
      );
      setMensajeListado(data.mensaje || "");
      setSolicitudes(
        Array.isArray(data.solicitudes)
          ? data.solicitudes
          : []
      );
    } catch (errorCarga) {
      setGrupoNombre("");
      setEstadoActividad("");
      setResponsable(null);
      setTotalSolicitudes(0);
      setTotalPendientes(0);
      setMensajeListado("");
      setSolicitudes([]);
      setError(
        errorCarga.message ||
          "No se pudieron cargar las solicitudes."
      );
    } finally {
      setCargando(false);
    }
  }, [id]);

  useEffect(() => {
    const temporizador = setTimeout(() => {
      obtenerSolicitudes();
    }, 0);

    return () => {
      clearTimeout(temporizador);
    };
  }, [obtenerSolicitudes]);

  const abrirDecision = (solicitud, nuevaDecision) => {
    setSolicitudSeleccionada(solicitud);
    setDecision(nuevaDecision);
    setObservacion("");
    setErrorDecision("");
    setResultadoDecision(null);
    setModalAbierto(true);
  };

  const cerrarDecision = () => {
    if (guardandoDecision) {
      return;
    }

    setModalAbierto(false);
    setSolicitudSeleccionada(null);
    setDecision("");
    setObservacion("");
    setErrorDecision("");
  };

  const guardarDecision = async (event) => {
    event.preventDefault();
    setErrorDecision("");

    const observacionLimpia = observacion.trim();

    if (!solicitudSeleccionada) {
      setErrorDecision(
        "No se pudo identificar la solicitud."
      );
      return;
    }

    if (
      decision !== "aprobada" &&
      decision !== "rechazada"
    ) {
      setErrorDecision("La decisión seleccionada no es válida.");
      return;
    }

    if (!observacionLimpia) {
      setErrorDecision(
        "La observación o justificación es obligatoria."
      );
      return;
    }

    if (observacionLimpia.length > 2000) {
      setErrorDecision(
        "La observación no puede superar los 2000 caracteres."
      );
      return;
    }

    try {
      setGuardandoDecision(true);

      const response = await authFetch(
        `${API_BASE_URL}/grupos/${id}/solicitudes-deuda/${solicitudSeleccionada.id}/`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            decision,
            observacion: observacionLimpia,
          }),
        }
      );

      const data = await leerJsonSeguro(response);

      if (!response.ok) {
        throw new Error(
          obtenerMensajeError(
            data,
            "No se pudo guardar la decisión."
          )
        );
      }

      setSolicitudes((solicitudesActuales) =>
        solicitudesActuales.filter(
          (solicitud) =>
            solicitud.id !== solicitudSeleccionada.id
        )
      );

      const pendientesActualizados =
        Number(data.solicitudes_pendientes_actividad) || 0;

      setTotalPendientes(pendientesActualizados);
      setMensajeListado(
        pendientesActualizados > 0
          ? "Quedan solicitudes pendientes de revisión."
          : "No existen solicitudes pendientes de revisión en esta actividad."
      );

      setResultadoDecision({
        mensaje:
          data.mensaje ||
          "Decisión guardada correctamente.",
        solicitud: data.solicitud || null,
        deuda: data.deuda || null,
        advertencia:
          data.advertencia_actualizada || null,
        notificacion: data.notificacion || null,
      });

      setModalAbierto(false);
      setSolicitudSeleccionada(null);
      setDecision("");
      setObservacion("");
      setErrorDecision("");
    } catch (errorGuardado) {
      setErrorDecision(
        errorGuardado.message ||
          "No se pudo guardar la decisión."
      );
    } finally {
      setGuardandoDecision(false);
    }
  };

  const handleLogout = () => {
    limpiarSesion();
    navigate("/login");
  };

  const configuracionActividad =
    obtenerConfiguracionActividad(estadoActividad);

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
              onClick={() => navigate(`/grupos/${id}`)}
            >
              👥 Actividad
            </button>

            <button
              className="sidebar-link"
              onClick={() => navigate("/mis-deudas")}
            >
              💳 Mis deudas
            </button>

            <button className="sidebar-link active">
              ✓ Revisar solicitudes
            </button>

            <button
              className="sidebar-link"
              onClick={() => navigate("/notificaciones")}
            >
              🔔 Notificaciones
            </button>

            <button
              className="sidebar-link"
              onClick={() => navigate("/resumen")}
            >
              📊 Resumen
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
        <header className="dashboard-header">
          <div>
            <button
              type="button"
              className="back-button mb-3"
              onClick={() => navigate(`/grupos/${id}`)}
            >
              ← Volver a la actividad
            </button>

            <div className="d-flex flex-wrap align-items-center gap-3">
              <h1 className="mb-0">
                Solicitudes de resolución
              </h1>

              {estadoActividad && (
                <span
                  className={`badge ${configuracionActividad.clase}`}
                >
                  {configuracionActividad.texto}
                </span>
              )}
            </div>

            <p className="mt-2">
              Revisa las evidencias y decide si corresponde
              resolver cada deuda.
            </p>
          </div>

          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={obtenerSolicitudes}
            disabled={cargando}
          >
            {cargando ? "Actualizando..." : "Actualizar"}
          </button>
        </header>

        {grupoNombre && (
          <section className="create-group-card mb-4">
            <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
              <div>
                <small className="text-muted d-block">
                  Actividad
                </small>

                <h4 className="mb-1">{grupoNombre}</h4>

                <small className="text-muted">
                  Responsable:{" "}
                  <strong>
                    {obtenerNombreUsuario(responsable)}
                  </strong>
                  {responsable?.username && (
                    <> (@{responsable.username})</>
                  )}
                </small>
              </div>

              <div className="d-flex flex-wrap gap-2">
                <span className="badge bg-light text-dark border fs-6">
                  Históricas: {totalSolicitudes}
                </span>

                <span className="badge bg-warning text-dark fs-6">
                  Pendientes: {totalPendientes}
                </span>
              </div>
            </div>

            {estadoActividad === "cerrada" && (
              <div className="alert alert-info mt-3 mb-0">
                La actividad está cerrada, pero sus solicitudes
                pendientes todavía pueden revisarse.
              </div>
            )}
          </section>
        )}

        {resultadoDecision && (
          <section
            className={`alert ${
              resultadoDecision.solicitud?.decision ===
              "aprobada"
                ? "alert-success"
                : "alert-warning"
            }`}
            role="status"
          >
            <div className="d-flex justify-content-between align-items-start gap-3">
              <div>
                <h5 className="mb-1">
                  {resultadoDecision.mensaje}
                </h5>

                <p className="mb-0">
                  {resultadoDecision.solicitud
                    ?.resultado_deuda ||
                    "La decisión fue registrada."}
                </p>
              </div>

              <button
                type="button"
                className="btn-close"
                aria-label="Cerrar"
                onClick={() => setResultadoDecision(null)}
              />
            </div>

            <div className="row g-3 mt-1">
              <div className="col-md-4">
                <div className="bg-white border rounded p-3 h-100">
                  <small className="text-muted d-block">
                    Estado de la deuda
                  </small>

                  <strong>
                    {resultadoDecision.deuda?.estado_display ||
                      resultadoDecision.deuda?.estado ||
                      "Sin información"}
                  </strong>
                </div>
              </div>

              <div className="col-md-4">
                <div className="bg-white border rounded p-3 h-100">
                  <small className="text-muted d-block">
                    Saldo pendiente
                  </small>

                  <strong>
                    {formatearMonto(
                      resultadoDecision.deuda?.saldo_pendiente
                    )}
                  </strong>
                </div>
              </div>

              <div className="col-md-4">
                <div className="bg-white border rounded p-3 h-100">
                  <small className="text-muted d-block">
                    Deudas activas del solicitante
                  </small>

                  <strong>
                    {resultadoDecision.advertencia
                      ?.cantidad_deudas_pendientes ?? 0}
                  </strong>

                  <small className="text-muted d-block">
                    {formatearMonto(
                      resultadoDecision.advertencia
                        ?.monto_total_pendiente
                    )}
                  </small>
                </div>
              </div>
            </div>

            {resultadoDecision.notificacion && (
              <div className="bg-white border rounded p-3 mt-3">
                <small className="text-muted d-block">
                  Notificación enviada
                </small>

                <strong>
                  {resultadoDecision.notificacion.titulo}
                </strong>

                <p className="mb-0 mt-1">
                  {resultadoDecision.notificacion.mensaje}
                </p>
              </div>
            )}
          </section>
        )}

        {error && (
          <div className="alert alert-danger" role="alert">
            {error}
          </div>
        )}

        <section className="create-group-card">
          <div className="d-flex justify-content-between align-items-center gap-3">
            <div>
              <h4 className="mb-1">
                Pendientes de revisión
              </h4>

              <small className="text-muted">
                Las solicitudes más recientes aparecen primero.
              </small>
            </div>

            <span className="badge bg-warning text-dark fs-6">
              {totalPendientes}
            </span>
          </div>

          {cargando ? (
            <div className="alert alert-light border mt-4 mb-0">
              Cargando solicitudes pendientes...
            </div>
          ) : error ? (
            <div className="alert alert-light border mt-4 mb-0">
              No fue posible consultar las solicitudes.
              Corrige el problema de sesión o conexión y
              vuelve a intentarlo.
            </div>
          ) : solicitudes.length === 0 ? (
            <div className="empty-groups-card mt-4">
              <h5>No hay solicitudes pendientes</h5>

              <p>
                {mensajeListado ||
                  "Todas las solicitudes ya fueron revisadas."}
              </p>

              <button
                type="button"
                className="btn btn-primary"
                onClick={() => navigate(`/grupos/${id}`)}
              >
                Volver a la actividad
              </button>
            </div>
          ) : (
            <div className="d-flex flex-column gap-4 mt-4">
              {solicitudes.map((solicitud) => {
                const deuda = solicitud.deuda || {};
                const solicitante =
                  solicitud.solicitante ||
                  deuda.participante ||
                  null;

                return (
                  <article
                    key={solicitud.id}
                    className="border rounded p-4"
                  >
                    <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
                      <div>
                        <div className="d-flex flex-wrap align-items-center gap-2">
                          <h5 className="mb-0">
                            Solicitud #{solicitud.id}
                          </h5>

                          <span className="badge bg-warning text-dark">
                            {solicitud.estado_display ||
                              "Pendiente de revisión"}
                          </span>
                        </div>

                        <small className="text-muted d-block mt-2">
                          Enviada:{" "}
                          {formatearFechaHora(
                            solicitud.fecha_envio
                          )}
                        </small>
                      </div>

                      <div className="text-end">
                        <small className="text-muted d-block">
                          Saldo pendiente
                        </small>

                        <strong className="fs-3 text-danger">
                          {formatearMonto(
                            deuda.saldo_pendiente
                          )}
                        </strong>
                      </div>
                    </div>

                    <div className="row g-3 mt-1">
                      <div className="col-md-4">
                        <div className="border rounded bg-light p-3 h-100">
                          <small className="text-muted d-block">
                            Solicitante
                          </small>

                          <strong>
                            {obtenerNombreUsuario(solicitante)}
                          </strong>

                          {(solicitante?.username ||
                            solicitud.solicitante_username) && (
                            <small className="text-muted d-block">
                              @
                              {solicitante?.username ||
                                solicitud.solicitante_username}
                            </small>
                          )}
                        </div>
                      </div>

                      <div className="col-md-4">
                        <div className="border rounded bg-light p-3 h-100">
                          <small className="text-muted d-block">
                            Deuda
                          </small>

                          <strong>#{solicitud.deuda_id}</strong>

                          <small className="text-muted d-block">
                            Original:{" "}
                            {formatearMonto(
                              deuda.monto_original
                            )}
                          </small>
                        </div>
                      </div>

                      <div className="col-md-4">
                        <div className="border rounded bg-light p-3 h-100">
                          <small className="text-muted d-block">
                            Estado actual
                          </small>

                          <strong>
                            {deuda.estado_display ||
                              deuda.estado ||
                              "Pendiente"}
                          </strong>

                          <small className="text-muted d-block">
                            Generada:{" "}
                            {formatearFechaHora(
                              deuda.fecha_generacion
                            )}
                          </small>
                        </div>
                      </div>
                    </div>

                    <div className="border rounded p-3 mt-3">
                      <small className="text-muted d-block">
                        Descripción del solicitante
                      </small>

                      <p className="mb-0 mt-2">
                        {solicitud.descripcion}
                      </p>
                    </div>

                    <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mt-3">
                      {solicitud.evidencia ? (
                        <a
                          href={construirUrlEvidencia(
                            solicitud.evidencia
                          )}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-outline-secondary"
                        >
                          Abrir evidencia:{" "}
                          {solicitud.evidencia_nombre_original ||
                            "archivo adjunto"}
                        </a>
                      ) : (
                        <span className="text-muted">
                          Sin evidencia disponible
                        </span>
                      )}

                      <div className="d-flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="btn btn-outline-danger"
                          onClick={() =>
                            abrirDecision(
                              solicitud,
                              "rechazada"
                            )
                          }
                          disabled={!solicitud.puede_revisar}
                        >
                          Rechazar
                        </button>

                        <button
                          type="button"
                          className="btn btn-success"
                          onClick={() =>
                            abrirDecision(
                              solicitud,
                              "aprobada"
                            )
                          }
                          disabled={!solicitud.puede_revisar}
                        >
                          Aprobar y resolver deuda
                        </button>
                      </div>
                    </div>

                    {!solicitud.puede_revisar && (
                      <div className="alert alert-warning mt-3 mb-0">
                        Esta solicitud no puede revisarse con el
                        usuario actual o ya dejó de estar pendiente.
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </main>

      {modalAbierto && solicitudSeleccionada && (
        <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.58)",
            zIndex: 1090,
          }}
          role="dialog"
          aria-modal="true"
          aria-label="Registrar decisión"
          onClick={cerrarDecision}
        >
          <div
            className="bg-white rounded shadow-lg w-100"
            style={{
              maxWidth: "700px",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="d-flex justify-content-between align-items-start border-bottom p-4">
              <div>
                <span
                  className={`badge ${
                    decision === "aprobada"
                      ? "bg-success"
                      : "bg-danger"
                  } mb-2`}
                >
                  {decision === "aprobada"
                    ? "Aprobar solicitud"
                    : "Rechazar solicitud"}
                </span>

                <h4 className="mb-1">
                  Solicitud #{solicitudSeleccionada.id}
                </h4>

                <small className="text-muted">
                  La decisión quedará registrada con tu usuario
                  y la fecha exacta.
                </small>
              </div>

              <button
                type="button"
                className="btn-close"
                aria-label="Cerrar"
                onClick={cerrarDecision}
                disabled={guardandoDecision}
              />
            </div>

            <form onSubmit={guardarDecision}>
              <div className="p-4">
                {errorDecision && (
                  <div
                    className="alert alert-danger"
                    role="alert"
                  >
                    {errorDecision}
                  </div>
                )}

                <div
                  className={`alert ${
                    decision === "aprobada"
                      ? "alert-success"
                      : "alert-warning"
                  }`}
                >
                  {decision === "aprobada"
                    ? "Al aprobar, la deuda quedará resuelta y su saldo pendiente cambiará a $0.00."
                    : "Al rechazar, la solicitud quedará revisada, pero la deuda continuará pendiente."}
                </div>

                <div className="row g-3">
                  <div className="col-md-6">
                    <div className="border rounded p-3 h-100 bg-light">
                      <small className="text-muted d-block">
                        Solicitante
                      </small>

                      <strong>
                        {obtenerNombreUsuario(
                          solicitudSeleccionada.solicitante
                        )}
                      </strong>
                    </div>
                  </div>

                  <div className="col-md-6">
                    <div className="border rounded p-3 h-100 bg-light">
                      <small className="text-muted d-block">
                        Saldo pendiente
                      </small>

                      <strong>
                        {formatearMonto(
                          solicitudSeleccionada.deuda
                            ?.saldo_pendiente
                        )}
                      </strong>
                    </div>
                  </div>
                </div>

                <div className="mt-3">
                  <label className="form-label">
                    Observación o justificación
                  </label>

                  <textarea
                    className="form-control"
                    rows="5"
                    maxLength="2000"
                    value={observacion}
                    onChange={(event) =>
                      setObservacion(event.target.value)
                    }
                    placeholder={
                      decision === "aprobada"
                        ? "Explica por qué la evidencia permite resolver la deuda..."
                        : "Explica por qué la evidencia no permite resolver la deuda..."
                    }
                    disabled={guardandoDecision}
                    required
                  />

                  <small className="text-muted">
                    {observacion.length}/2000 caracteres
                  </small>
                </div>

                <div className="alert alert-light border mt-3 mb-0">
                  El solicitante recibirá una notificación no
                  leída con la decisión, esta observación y el
                  resultado de la deuda.
                </div>
              </div>

              <div className="d-flex justify-content-end gap-2 border-top p-4">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={cerrarDecision}
                  disabled={guardandoDecision}
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  className={`btn ${
                    decision === "aprobada"
                      ? "btn-success"
                      : "btn-danger"
                  }`}
                  disabled={guardandoDecision}
                >
                  {guardandoDecision
                    ? "Guardando decisión..."
                    : decision === "aprobada"
                      ? "Aprobar y resolver"
                      : "Confirmar rechazo"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default DebtResolutionReview;