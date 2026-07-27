import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  useNavigate,
  useParams,
} from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";
import {
  authFetch,
  limpiarSesion,
} from "../utils/authFetch";

const API_BASE_URL = "http://127.0.0.1:8000/api";
const SERVIDOR_BASE_URL = "http://127.0.0.1:8000";

const EXTENSIONES_PERMITIDAS = [
  "pdf",
  "jpg",
  "jpeg",
  "png",
];

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

const leerJsonSeguro = async (
  response,
  valorPredeterminado = {}
) =>
  response
    .json()
    .catch(() => valorPredeterminado);

const obtenerMensajeError = (
  data,
  mensajePredeterminado = "No se pudo completar la operación."
) => {
  if (!data || typeof data !== "object") {
    return mensajePredeterminado;
  }

  if (data.error) {
    return Array.isArray(data.error)
      ? data.error[0]
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

  if (
    typeof detalle === "object" &&
    detalle !== null
  ) {
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

const obtenerConfiguracionEstadoDeuda = (estado) => {
  if (estado === "pendiente") {
    return {
      texto: "Pendiente",
      clase: "bg-danger",
      descripcion:
        "La deuda mantiene un saldo pendiente.",
    };
  }

  if (estado === "en_revision") {
    return {
      texto: "En revisión",
      clase: "bg-warning text-dark",
      descripcion:
        "Existe una solicitud pendiente de decisión.",
    };
  }

  if (estado === "rechazada") {
    return {
      texto: "Solicitud rechazada",
      clase: "bg-danger",
      descripcion:
        "La deuda continúa pendiente después de la revisión.",
    };
  }

  if (estado === "resuelta") {
    return {
      texto: "Resuelta",
      clase: "bg-success",
      descripcion:
        "La deuda ya no mantiene saldo pendiente.",
    };
  }

  return {
    texto: "Sin estado",
    clase: "bg-secondary",
    descripcion:
      "No fue posible identificar el estado de la deuda.",
  };
};

const obtenerConfiguracionSolicitud = (estado) => {
  if (estado === "pendiente_revision") {
    return {
      texto: "Pendiente de revisión",
      clase: "bg-warning text-dark",
      alerta: "alert-warning",
    };
  }

  if (estado === "aprobada") {
    return {
      texto: "Aprobada",
      clase: "bg-success",
      alerta: "alert-success",
    };
  }

  if (estado === "rechazada") {
    return {
      texto: "Rechazada",
      clase: "bg-danger",
      alerta: "alert-danger",
    };
  }

  return {
    texto: "Sin estado",
    clase: "bg-secondary",
    alerta: "alert-secondary",
  };
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

  if (evidencia.startsWith("/")) {
    return `${SERVIDOR_BASE_URL}${evidencia}`;
  }

  return `${SERVIDOR_BASE_URL}/${evidencia}`;
};

function MyDebts() {
  const navigate = useNavigate();
  const { deudaId, solicitudId } = useParams();

  const [deudas, setDeudas] = useState([]);
  const [totalDeudas, setTotalDeudas] = useState(0);
  const [
    montoTotalPendiente,
    setMontoTotalPendiente,
  ] = useState("0.00");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [filtro, setFiltro] = useState("todas");

  const [
    formularioDeudaId,
    setFormularioDeudaId,
  ] = useState(null);
  const [descripcion, setDescripcion] = useState("");
  const [evidencia, setEvidencia] = useState(null);
  const [
    archivoInputKey,
    setArchivoInputKey,
  ] = useState(0);
  const [
    enviandoSolicitud,
    setEnviandoSolicitud,
  ] = useState(false);
  const [
    errorFormulario,
    setErrorFormulario,
  ] = useState("");

  const [
    solicitudSeleccionada,
    setSolicitudSeleccionada,
  ] = useState(null);
  const [
    cargandoSolicitud,
    setCargandoSolicitud,
  ] = useState(false);
  const [
    errorSolicitud,
    setErrorSolicitud,
  ] = useState("");

  const username =
    localStorage.getItem("username") || "usuario";
  const displayName =
    username.charAt(0).toUpperCase() +
    username.slice(1);
  const avatarLetter =
    username.charAt(0).toUpperCase();

  const deudasFiltradas = useMemo(() => {
    if (filtro === "pendientes") {
      return deudas.filter(
        (deuda) =>
          deuda.estado !== "resuelta" &&
          Number(deuda.saldo_pendiente) > 0
      );
    }

    if (filtro === "revision") {
      return deudas.filter(
        (deuda) =>
          deuda.estado === "en_revision" ||
          deuda.tiene_solicitud_pendiente
      );
    }

    if (filtro === "resueltas") {
      return deudas.filter(
        (deuda) =>
          deuda.estado === "resuelta" ||
          Number(deuda.saldo_pendiente) <= 0
      );
    }

    return deudas;
  }, [deudas, filtro]);

  const cantidadPendientes = deudas.filter(
    (deuda) =>
      deuda.estado !== "resuelta" &&
      Number(deuda.saldo_pendiente) > 0
  ).length;

  const cantidadEnRevision = deudas.filter(
    (deuda) =>
      deuda.estado === "en_revision" ||
      deuda.tiene_solicitud_pendiente
  ).length;

  const cantidadResueltas = deudas.filter(
    (deuda) =>
      deuda.estado === "resuelta" ||
      Number(deuda.saldo_pendiente) <= 0
  ).length;

  const obtenerDeudas = useCallback(async () => {
    try {
      setCargando(true);
      setError("");

      const response = await authFetch(
        `${API_BASE_URL}/mis-deudas/`,
        {
          method: "GET",
        }
      );

      const data = await leerJsonSeguro(response);

      if (!response.ok) {
        throw new Error(
          obtenerMensajeError(
            data,
            "No se pudieron cargar tus deudas."
          )
        );
      }

      setDeudas(
        Array.isArray(data.deudas)
          ? data.deudas
          : []
      );
      setTotalDeudas(
        Number(data.total_deudas) || 0
      );
      setMontoTotalPendiente(
        data.monto_total_pendiente || "0.00"
      );
    } catch (errorCarga) {
      setDeudas([]);
      setTotalDeudas(0);
      setMontoTotalPendiente("0.00");
      setError(
        errorCarga.message ||
          "No se pudieron cargar tus deudas."
      );
    } finally {
      setCargando(false);
    }
  }, []);

  const obtenerDetalleSolicitud = useCallback(
    async (
      deudaSeleccionadaId,
      solicitudSeleccionadaId
    ) => {
      try {
        setCargandoSolicitud(true);
        setErrorSolicitud("");
        setSolicitudSeleccionada(null);

        const response = await authFetch(
          `${API_BASE_URL}/mis-deudas/${deudaSeleccionadaId}/solicitudes/${solicitudSeleccionadaId}/`,
          {
            method: "GET",
          }
        );

        const data = await leerJsonSeguro(response);

        if (!response.ok) {
          throw new Error(
            obtenerMensajeError(
              data,
              "No se pudo cargar la solicitud."
            )
          );
        }

        setSolicitudSeleccionada(
          data.solicitud || null
        );
      } catch (errorDetalle) {
        setSolicitudSeleccionada(null);
        setErrorSolicitud(
          errorDetalle.message ||
            "No se pudo cargar la solicitud."
        );
      } finally {
        setCargandoSolicitud(false);
      }
    },
    []
  );

  useEffect(() => {
    const temporizador = setTimeout(() => {
      obtenerDeudas();
    }, 0);

    return () => {
      clearTimeout(temporizador);
    };
  }, [obtenerDeudas]);

  useEffect(() => {
    if (!deudaId || !solicitudId) {
      return undefined;
    }

    const temporizador = setTimeout(() => {
      obtenerDetalleSolicitud(
        deudaId,
        solicitudId
      );
    }, 0);

    return () => {
      clearTimeout(temporizador);
    };
  }, [
    deudaId,
    solicitudId,
    obtenerDetalleSolicitud,
  ]);

  const abrirFormularioSolicitud = (deuda) => {
    setFormularioDeudaId(deuda.id);
    setDescripcion("");
    setEvidencia(null);
    setArchivoInputKey(
      (claveActual) => claveActual + 1
    );
    setErrorFormulario("");
    setMensaje("");
    setError("");
  };

  const cerrarFormularioSolicitud = () => {
    if (enviandoSolicitud) {
      return;
    }

    setFormularioDeudaId(null);
    setDescripcion("");
    setEvidencia(null);
    setArchivoInputKey(
      (claveActual) => claveActual + 1
    );
    setErrorFormulario("");
  };

  const seleccionarEvidencia = (event) => {
    const archivo =
      event.target.files?.[0] || null;

    setErrorFormulario("");

    if (!archivo) {
      setEvidencia(null);
      return;
    }

    const extension =
      archivo.name.split(".").pop()?.toLowerCase() ||
      "";

    if (
      !EXTENSIONES_PERMITIDAS.includes(extension)
    ) {
      setEvidencia(null);
      setArchivoInputKey(
        (claveActual) => claveActual + 1
      );
      setErrorFormulario(
        "La evidencia debe estar en formato PDF, JPG, JPEG o PNG."
      );
      return;
    }

    setEvidencia(archivo);
  };

  const enviarSolicitud = async (
    event,
    deuda
  ) => {
    event.preventDefault();

    setErrorFormulario("");
    setMensaje("");
    setError("");

    const descripcionLimpia =
      descripcion.trim();

    if (!descripcionLimpia) {
      setErrorFormulario(
        "Escribe una descripción o explicación."
      );
      return;
    }

    if (descripcionLimpia.length > 2000) {
      setErrorFormulario(
        "La descripción no puede superar los 2000 caracteres."
      );
      return;
    }

    const formData = new FormData();

    formData.append(
      "descripcion",
      descripcionLimpia
    );
    if (evidencia) {
      formData.append("evidencia", evidencia);
    }

    try {
      setEnviandoSolicitud(true);

      const response = await authFetch(
        `${API_BASE_URL}/mis-deudas/${deuda.id}/solicitudes/`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await leerJsonSeguro(response);

      if (!response.ok) {
        throw new Error(
          obtenerMensajeError(
            data,
            "No se pudo enviar la solicitud."
          )
        );
      }

      setFormularioDeudaId(null);
      setDescripcion("");
      setEvidencia(null);
      setArchivoInputKey(
        (claveActual) => claveActual + 1
      );
      setErrorFormulario("");
      setMensaje(
        data.mensaje ||
          "Solicitud enviada correctamente y pendiente de revisión."
      );

      await obtenerDeudas();
    } catch (errorEnvio) {
      setErrorFormulario(
        errorEnvio.message ||
          "No se pudo enviar la solicitud."
      );
    } finally {
      setEnviandoSolicitud(false);
    }
  };

  const abrirSolicitud = (
    deuda,
    solicitud
  ) => {
    navigate(
      `/mis-deudas/${deuda.id}/solicitudes/${solicitud.id}`
    );
  };

  const cerrarDetalleSolicitud = () => {
    setSolicitudSeleccionada(null);
    setErrorSolicitud("");
    setCargandoSolicitud(false);
    navigate("/mis-deudas", {
      replace: true,
    });
  };

  const handleLogout = () => {
    limpiarSesion();
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
              onClick={() =>
                navigate("/dashboard")
              }
            >
              ▦ Dashboard
            </button>

            <button
              className="sidebar-link"
              onClick={() =>
                navigate("/dashboard")
              }
            >
              👥 Grupos
            </button>

            <button className="sidebar-link active">
              💳 Mis deudas
            </button>

            <button
              className="sidebar-link"
              onClick={() =>
                navigate("/notificaciones")
              }
            >
              🔔 Notificaciones
            </button>

            <button
              className="sidebar-link"
              onClick={() => navigate("/resumen")}
            >
              📊 Resumen
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
            <button
              type="button"
              className="back-button mb-3"
              onClick={() =>
                navigate("/dashboard")
              }
            >
              ← Volver al dashboard
            </button>

            <h1>Mis deudas</h1>

            <p>
              Consulta tus obligaciones históricas,
              revisa sus solicitudes y adjunta evidencia
              cuando corresponda.
            </p>
          </div>

          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={obtenerDeudas}
            disabled={cargando}
          >
            {cargando
              ? "Actualizando..."
              : "Actualizar"}
          </button>
        </header>

        <section className="summary-grid">
          <div className="summary-card debt">
            <div className="summary-icon red">
              $
            </div>

            <div>
              <span>Total pendiente</span>

              <h2>
                {cargando
                  ? "Consultando..."
                  : formatearMonto(
                      montoTotalPendiente
                    )}
              </h2>

              <p>
                {cantidadPendientes} obligación
                {cantidadPendientes === 1
                  ? ""
                  : "es"}{" "}
                con saldo.
              </p>
            </div>
          </div>

          <div className="summary-card income">
            <div className="summary-icon green">
              ✓
            </div>

            <div>
              <span>Deudas registradas</span>

              <h2>
                {cargando ? "..." : totalDeudas}
              </h2>

              <p>
                {cantidadResueltas} resuelta
                {cantidadResueltas === 1
                  ? ""
                  : "s"}{" "}
                y {cantidadEnRevision} en revisión.
              </p>
            </div>
          </div>
        </section>

        {mensaje && (
          <div
            className="alert alert-success mt-3"
            role="alert"
          >
            {mensaje}
          </div>
        )}

        {error && (
          <div
            className="alert alert-danger mt-3"
            role="alert"
          >
            {error}
          </div>
        )}

        <section className="create-group-card mt-4">
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-3">
            <div>
              <h4 className="mb-1">
                Obligaciones registradas
              </h4>

              <small className="text-muted">
                Las más recientes aparecen primero.
              </small>
            </div>

            <div
              className="btn-group"
              role="group"
              aria-label="Filtrar deudas"
            >
              <button
                type="button"
                className={`btn ${
                  filtro === "todas"
                    ? "btn-primary"
                    : "btn-outline-primary"
                }`}
                onClick={() =>
                  setFiltro("todas")
                }
              >
                Todas
              </button>

              <button
                type="button"
                className={`btn ${
                  filtro === "pendientes"
                    ? "btn-primary"
                    : "btn-outline-primary"
                }`}
                onClick={() =>
                  setFiltro("pendientes")
                }
              >
                Pendientes
              </button>

              <button
                type="button"
                className={`btn ${
                  filtro === "revision"
                    ? "btn-primary"
                    : "btn-outline-primary"
                }`}
                onClick={() =>
                  setFiltro("revision")
                }
              >
                En revisión
              </button>

              <button
                type="button"
                className={`btn ${
                  filtro === "resueltas"
                    ? "btn-primary"
                    : "btn-outline-primary"
                }`}
                onClick={() =>
                  setFiltro("resueltas")
                }
              >
                Resueltas
              </button>
            </div>
          </div>

          {cargando ? (
            <div
              className="alert alert-light border mt-4 mb-0"
              role="status"
            >
              Cargando tus deudas...
            </div>
          ) : error ? (
            <div
              className="alert alert-light border mt-4 mb-0"
              role="status"
            >
              No fue posible consultar tus deudas.
              Corrige el problema de sesión o conexión y
              vuelve a intentarlo.
            </div>
          ) : deudasFiltradas.length === 0 ? (
            <div className="empty-groups-card mt-4">
              <h5>
                No hay deudas para este filtro
              </h5>

              <p>
                No se encontraron obligaciones que
                coincidan con el estado seleccionado.
              </p>
            </div>
          ) : (
            <div className="d-flex flex-column gap-4 mt-4">
              {deudasFiltradas.map((deuda) => {
                const configuracionEstado =
                  obtenerConfiguracionEstadoDeuda(
                    deuda.estado
                  );

                const solicitudes = Array.isArray(
                  deuda.solicitudes
                )
                  ? deuda.solicitudes
                  : [];

                const puedeEnviarSolicitud =
                  deuda.estado === "pendiente" &&
                  Number(deuda.saldo_pendiente) > 0 &&
                  !deuda.tiene_solicitud_pendiente;

                return (
                  <article
                    key={deuda.id}
                    className="border rounded p-4"
                  >
                    <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
                      <div>
                        <div className="d-flex flex-wrap align-items-center gap-2">
                          <h4 className="mb-0">
                            {deuda.actividad?.nombre ||
                              deuda.grupo_nombre ||
                              "Actividad"}
                          </h4>

                          <span
                            className={`badge ${
                              configuracionEstado.clase
                            }`}
                          >
                            {deuda.estado_display ||
                              configuracionEstado.texto}
                          </span>
                        </div>

                        <small className="text-muted d-block mt-2">
                          Deuda #{deuda.id}
                        </small>

                        <small className="text-muted d-block">
                          Generada:{" "}
                          {formatearFechaHora(
                            deuda.fecha_generacion
                          )}
                        </small>
                      </div>

                      <div className="text-end">
                        <small className="text-muted d-block">
                          Saldo pendiente
                        </small>

                        <strong
                          className={`fs-3 ${
                            Number(
                              deuda.saldo_pendiente
                            ) > 0
                              ? "text-danger"
                              : "text-success"
                          }`}
                        >
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
                            Monto original
                          </small>

                          <strong className="fs-5">
                            {formatearMonto(
                              deuda.monto_original
                            )}
                          </strong>
                        </div>
                      </div>

                      <div className="col-md-4">
                        <div className="border rounded bg-light p-3 h-100">
                          <small className="text-muted d-block">
                            Estado de la actividad
                          </small>

                          <strong>
                            {deuda.actividad?.estado ||
                              "Sin información"}
                          </strong>
                        </div>
                      </div>

                      <div className="col-md-4">
                        <div className="border rounded bg-light p-3 h-100">
                          <small className="text-muted d-block">
                            Solicitudes realizadas
                          </small>

                          <strong className="fs-5">
                            {deuda.cantidad_solicitudes ??
                              solicitudes.length}
                          </strong>
                        </div>
                      </div>
                    </div>

                    <div
                      className="alert alert-light border mt-3 mb-0"
                      role="status"
                    >
                      {configuracionEstado.descripcion}
                    </div>

                    {deuda.tiene_solicitud_pendiente && (
                      <div
                        className="alert alert-warning mt-3 mb-0"
                        role="alert"
                      >
                        Ya existe una solicitud pendiente
                        de revisión para esta deuda. No se
                        puede enviar otra hasta que el
                        responsable tome una decisión.
                      </div>
                    )}

                    {puedeEnviarSolicitud &&
                      formularioDeudaId !==
                        deuda.id && (
                        <div className="d-flex justify-content-end mt-3">
                          <button
                            type="button"
                            className="btn btn-primary"
                            onClick={() =>
                              abrirFormularioSolicitud(
                                deuda
                              )
                            }
                          >
                            Enviar solicitud de resolución
                          </button>
                        </div>
                      )}

                    {formularioDeudaId ===
                      deuda.id && (
                      <form
                        className="border rounded p-4 mt-3 bg-light"
                        onSubmit={(event) =>
                          enviarSolicitud(
                            event,
                            deuda
                          )
                        }
                      >
                        <h5>
                          Solicitud de resolución
                        </h5>

                        <p className="text-muted">
                          Explica por qué consideras que
                          la deuda debe resolverse. Puedes
                          adjuntar una evidencia de manera
                          opcional.
                        </p>

                        {errorFormulario && (
                          <div
                            className="alert alert-danger"
                            role="alert"
                          >
                            {errorFormulario}
                          </div>
                        )}

                        <div className="mb-3">
                          <label className="form-label">
                            Descripción o explicación
                          </label>

                          <textarea
                            className="form-control"
                            rows="5"
                            maxLength="2000"
                            value={descripcion}
                            onChange={(event) =>
                              setDescripcion(
                                event.target.value
                              )
                            }
                            placeholder="Describe el pago realizado o la razón de la solicitud..."
                            disabled={
                              enviandoSolicitud
                            }
                          />

                          <small className="text-muted">
                            {descripcion.length}/2000
                            caracteres
                          </small>
                        </div>

                        <div className="mb-3">
                          <label className="form-label">
                            Evidencia (opcional)
                          </label>

                          <input
                            key={archivoInputKey}
                            type="file"
                            className="form-control"
                            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                            onChange={
                              seleccionarEvidencia
                            }
                            disabled={
                              enviandoSolicitud
                            }
                            required
                          />

                          <small className="text-muted">
                            Campo opcional. Formatos
                            permitidos: PDF, JPG, JPEG y PNG.
                          </small>

                          {evidencia && (
                            <div className="alert alert-info py-2 mt-2 mb-0">
                              Archivo seleccionado:{" "}
                              <strong>
                                {evidencia.name}
                              </strong>
                            </div>
                          )}
                        </div>

                        <div className="d-flex justify-content-end gap-2">
                          <button
                            type="button"
                            className="btn btn-outline-secondary"
                            onClick={
                              cerrarFormularioSolicitud
                            }
                            disabled={
                              enviandoSolicitud
                            }
                          >
                            Cancelar
                          </button>

                          <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={
                              enviandoSolicitud
                            }
                          >
                            {enviandoSolicitud
                              ? "Enviando..."
                              : "Enviar solicitud"}
                          </button>
                        </div>
                      </form>
                    )}

                    <div className="mt-4 pt-4 border-top">
                      <div className="d-flex justify-content-between align-items-center gap-3">
                        <div>
                          <h5 className="mb-1">
                            Historial de solicitudes
                          </h5>

                          <small className="text-muted">
                            Consulta evidencias,
                            decisiones y observaciones.
                          </small>
                        </div>

                        <span className="badge bg-light text-dark border">
                          {solicitudes.length}
                        </span>
                      </div>

                      {solicitudes.length === 0 ? (
                        <div className="alert alert-light border mt-3 mb-0">
                          Esta deuda todavía no tiene
                          solicitudes de resolución.
                        </div>
                      ) : (
                        <div className="d-flex flex-column gap-3 mt-3">
                          {solicitudes.map(
                            (solicitud) => {
                              const configuracionSolicitud =
                                obtenerConfiguracionSolicitud(
                                  solicitud.estado
                                );

                              return (
                                <div
                                  key={solicitud.id}
                                  className="border rounded p-3"
                                >
                                  <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
                                    <div>
                                      <div className="d-flex flex-wrap align-items-center gap-2">
                                        <strong>
                                          Solicitud #
                                          {solicitud.id}
                                        </strong>

                                        <span
                                          className={`badge ${
                                            configuracionSolicitud.clase
                                          }`}
                                        >
                                          {solicitud.estado_display ||
                                            configuracionSolicitud.texto}
                                        </span>
                                      </div>

                                      <small className="text-muted d-block mt-2">
                                        Enviada:{" "}
                                        {formatearFechaHora(
                                          solicitud.fecha_envio
                                        )}
                                      </small>
                                    </div>

                                    <button
                                      type="button"
                                      className="btn btn-outline-primary btn-sm"
                                      onClick={() =>
                                        abrirSolicitud(
                                          deuda,
                                          solicitud
                                        )
                                      }
                                    >
                                      Ver detalle
                                    </button>
                                  </div>

                                  <p className="mt-3 mb-2">
                                    {
                                      solicitud.descripcion
                                    }
                                  </p>

                                  {solicitud.evidencia && (
                                    <a
                                      href={construirUrlEvidencia(
                                        solicitud.evidencia
                                      )}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="btn btn-outline-secondary btn-sm"
                                    >
                                      Abrir evidencia
                                    </a>
                                  )}

                                  {solicitud.resultado_deuda && (
                                    <div
                                      className={`alert ${
                                        configuracionSolicitud.alerta
                                      } py-2 mt-3 mb-0`}
                                      role="status"
                                    >
                                      {
                                        solicitud.resultado_deuda
                                      }
                                    </div>
                                  )}
                                </div>
                              );
                            }
                          )}
                        </div>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </main>

      {(deudaId && solicitudId) && (
        <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{
            backgroundColor:
              "rgba(0, 0, 0, 0.58)",
            zIndex: 1090,
          }}
          role="dialog"
          aria-modal="true"
          aria-label="Detalle de solicitud"
          onClick={cerrarDetalleSolicitud}
        >
          <div
            className="bg-white rounded shadow-lg w-100"
            style={{
              maxWidth: "760px",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <div className="d-flex justify-content-between align-items-start border-bottom p-4">
              <div>
                <h4 className="mb-1">
                  Detalle de la solicitud
                </h4>

                <small className="text-muted">
                  Deuda #{deudaId} · Solicitud #
                  {solicitudId}
                </small>
              </div>

              <button
                type="button"
                className="btn-close"
                aria-label="Cerrar"
                onClick={
                  cerrarDetalleSolicitud
                }
              />
            </div>

            <div className="p-4">
              {cargandoSolicitud ? (
                <div
                  className="alert alert-light border mb-0"
                  role="status"
                >
                  Cargando solicitud...
                </div>
              ) : errorSolicitud ? (
                <div
                  className="alert alert-danger mb-0"
                  role="alert"
                >
                  {errorSolicitud}
                </div>
              ) : solicitudSeleccionada ? (
                <>
                  <div className="d-flex justify-content-between align-items-start flex-wrap gap-3">
                    <div>
                      <h5 className="mb-1">
                        {solicitudSeleccionada
                          .actividad?.nombre ||
                          solicitudSeleccionada
                            .grupo_nombre}
                      </h5>

                      <small className="text-muted">
                        Enviada el{" "}
                        {formatearFechaHora(
                          solicitudSeleccionada
                            .fecha_envio
                        )}
                      </small>
                    </div>

                    <span
                      className={`badge ${
                        obtenerConfiguracionSolicitud(
                          solicitudSeleccionada.estado
                        ).clase
                      }`}
                    >
                      {solicitudSeleccionada
                        .estado_display ||
                        obtenerConfiguracionSolicitud(
                          solicitudSeleccionada
                            .estado
                        ).texto}
                    </span>
                  </div>

                  <div className="border rounded p-3 bg-light mt-4">
                    <small className="text-muted d-block">
                      Descripción
                    </small>

                    <p className="mb-0 mt-1">
                      {
                        solicitudSeleccionada.descripcion
                      }
                    </p>
                  </div>

                  <div className="row g-3 mt-1">
                    <div className="col-md-6">
                      <div className="border rounded p-3 h-100">
                        <small className="text-muted d-block">
                          Monto original
                        </small>

                        <strong>
                          {formatearMonto(
                            solicitudSeleccionada
                              .deuda?.monto_original
                          )}
                        </strong>
                      </div>
                    </div>

                    <div className="col-md-6">
                      <div className="border rounded p-3 h-100">
                        <small className="text-muted d-block">
                          Saldo pendiente actual
                        </small>

                        <strong>
                          {formatearMonto(
                            solicitudSeleccionada
                              .deuda?.saldo_pendiente
                          )}
                        </strong>
                      </div>
                    </div>
                  </div>

                  {solicitudSeleccionada.evidencia && (
                    <div className="mt-4">
                      <a
                        href={construirUrlEvidencia(
                          solicitudSeleccionada.evidencia
                        )}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-outline-primary"
                      >
                        Abrir evidencia:{" "}
                        {solicitudSeleccionada
                          .evidencia_nombre_original ||
                          "archivo adjunto"}
                      </a>
                    </div>
                  )}

                  {solicitudSeleccionada
                    .observacion_revision && (
                    <div className="border rounded p-3 mt-4">
                      <small className="text-muted d-block">
                        Observación del responsable
                      </small>

                      <p className="mb-0 mt-1">
                        {
                          solicitudSeleccionada
                            .observacion_revision
                        }
                      </p>

                      <small className="text-muted d-block mt-2">
                        Revisada por @
                        {solicitudSeleccionada
                          .revisado_por?.username ||
                          solicitudSeleccionada
                            .revisado_por_username ||
                          "responsable"}
                        {" · "}
                        {formatearFechaHora(
                          solicitudSeleccionada
                            .fecha_revision
                        )}
                      </small>
                    </div>
                  )}

                  <div
                    className={`alert ${
                      obtenerConfiguracionSolicitud(
                        solicitudSeleccionada.estado
                      ).alerta
                    } mt-4 mb-0`}
                    role="status"
                  >
                    {solicitudSeleccionada
                      .resultado_deuda ||
                      "La solicitud está pendiente de revisión."}
                  </div>
                </>
              ) : (
                <div
                  className="alert alert-warning mb-0"
                  role="alert"
                >
                  No se encontró información de la
                  solicitud.
                </div>
              )}
            </div>

            <div className="d-flex justify-end border-top p-4">
              <button
                type="button"
                className="btn btn-primary ms-auto"
                onClick={
                  cerrarDetalleSolicitud
                }
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MyDebts;