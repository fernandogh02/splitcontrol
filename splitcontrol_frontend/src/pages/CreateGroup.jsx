import { useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";

const convertirFechaLocalAISO = (valor) => {
  if (!valor) {
    return null;
  }

  const fecha = new Date(valor);

  if (Number.isNaN(fecha.getTime())) {
    return null;
  }

  return fecha.toISOString();
};

const obtenerMensajeError = (
  data,
  mensajePredeterminado = "No se pudo crear la actividad."
) => {
  if (!data || typeof data !== "object") {
    return mensajePredeterminado;
  }

  if (data.error) {
    return data.error;
  }

  if (data.detail) {
    return data.detail;
  }

  const primeraClave = Object.keys(data)[0];

  if (!primeraClave) {
    return mensajePredeterminado;
  }

  const detalle = data[primeraClave];

  if (Array.isArray(detalle)) {
    return detalle[0];
  }

  if (typeof detalle === "object" && detalle !== null) {
    const subClave = Object.keys(detalle)[0];

    if (!subClave) {
      return mensajePredeterminado;
    }

    const subDetalle = detalle[subClave];

    if (Array.isArray(subDetalle)) {
      return subDetalle[0];
    }

    return String(subDetalle);
  }

  return String(detalle);
};

function CreateGroup() {
  const navigate = useNavigate();

  const username =
    localStorage.getItem("username") || "usuario";

  const displayName =
    username.charAt(0).toUpperCase() + username.slice(1);

  const avatarLetter = username.charAt(0).toUpperCase();

  const [formData, setFormData] = useState({
    nombre: "",
    descripcion: "",
    fecha_inicio: "",
    fecha_fin: "",
  });

  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  const handleChange = (e) => {
    setFormData((datosActuales) => ({
      ...datosActuales,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setMensaje("");
    setError("");

    if (!formData.nombre.trim()) {
      setError("Escribe un nombre para la actividad.");
      return;
    }

    if (!formData.fecha_inicio) {
      setError(
        "Selecciona la fecha y hora de inicio."
      );
      return;
    }

    if (!formData.fecha_fin) {
      setError(
        "Selecciona la fecha y hora de finalización."
      );
      return;
    }

    const fechaInicio = new Date(
      formData.fecha_inicio
    );

    const fechaFin = new Date(
      formData.fecha_fin
    );

    if (
      Number.isNaN(fechaInicio.getTime()) ||
      Number.isNaN(fechaFin.getTime())
    ) {
      setError(
        "Las fechas ingresadas no son válidas."
      );
      return;
    }

    if (fechaFin <= fechaInicio) {
      setError(
        "La fecha y hora de finalización debe ser posterior al inicio."
      );
      return;
    }

    const token = localStorage.getItem("access");

    if (!token) {
      setError(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      return;
    }

    try {
      setCargando(true);

      const response = await fetch(
        "http://127.0.0.1:8000/api/grupos/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            nombre: formData.nombre.trim(),
            descripcion: formData.descripcion.trim(),
            fecha_inicio: convertirFechaLocalAISO(
              formData.fecha_inicio
            ),
            fecha_fin: convertirFechaLocalAISO(
              formData.fecha_fin
            ),
          }),
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
          obtenerMensajeError(
            data,
            "No se pudo crear la actividad."
          )
        );
      }

      setMensaje(
        "Actividad creada correctamente."
      );

      setFormData({
        nombre: "",
        descripcion: "",
        fecha_inicio: "",
        fecha_fin: "",
      });

      setTimeout(() => {
        navigate("/dashboard");
      }, 1000);
    } catch (errorCreacion) {
      setError(
        errorCreacion.message ||
          "No se pudo crear la actividad."
      );
    } finally {
      setCargando(false);
    }
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

            <button className="sidebar-link active">
              👥 Grupos
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
          <button className="btn btn-primary w-100 mb-3">
            Registrar pago
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
        <div className="create-group-top">
          <button
            className="back-button"
            onClick={() => navigate("/dashboard")}
          >
            ← Grupos
          </button>

          <span>›</span>

          <strong>Crear nueva actividad</strong>

          <button className="guide-button">
            ⓘ Guía de Grupos
          </button>
        </div>

        <header className="create-group-header">
          <h1>Crear nueva actividad</h1>

          <p>
            Define la actividad, su periodo de duración y
            organiza los gastos compartidos con todos sus
            participantes.
          </p>
        </header>

        <section className="create-group-grid">
          <div className="create-group-card">
            {mensaje && (
              <div
                className="alert alert-success text-center"
                role="alert"
              >
                {mensaje}
              </div>
            )}

            {error && (
              <div
                className="alert alert-danger text-center"
                role="alert"
              >
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label">
                  Nombre de la actividad
                </label>

                <input
                  type="text"
                  name="nombre"
                  className="form-control"
                  placeholder="Ej: Viaje a la playa, Parrillada entre amigos..."
                  value={formData.nombre}
                  onChange={handleChange}
                  maxLength="100"
                  disabled={cargando}
                  required
                />
              </div>

              <div className="mb-3">
                <label className="form-label">
                  Descripción
                </label>

                <textarea
                  name="descripcion"
                  className="form-control"
                  rows="5"
                  placeholder="Describe brevemente la actividad."
                  value={formData.descripcion}
                  onChange={handleChange}
                  disabled={cargando}
                />
              </div>

              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label">
                    Fecha y hora de inicio
                  </label>

                  <input
                    type="datetime-local"
                    name="fecha_inicio"
                    className="form-control"
                    value={formData.fecha_inicio}
                    onChange={handleChange}
                    disabled={cargando}
                    required
                  />

                  <small className="text-muted">
                    Antes de esta fecha la actividad
                    aparecerá como programada.
                  </small>
                </div>

                <div className="col-md-6 mb-3">
                  <label className="form-label">
                    Fecha y hora de finalización
                  </label>

                  <input
                    type="datetime-local"
                    name="fecha_fin"
                    className="form-control"
                    value={formData.fecha_fin}
                    onChange={handleChange}
                    min={formData.fecha_inicio || undefined}
                    disabled={cargando}
                    required
                  />

                  <small className="text-muted">
                    Después de esta fecha la actividad
                    aparecerá como cerrada.
                  </small>
                </div>
              </div>

              <div
                className="alert alert-light border mt-2"
                role="alert"
              >
                <strong>Estado automático:</strong>{" "}
                SplitControl determinará si la actividad está
                programada, activa o cerrada según las fechas
                seleccionadas.
              </div>

              <div className="create-group-footer">
                <small>
                  ⓘ Podrás añadir participantes después de
                  crear la actividad.
                </small>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={cargando}
                >
                  {cargando
                    ? "Creando..."
                    : "Crear actividad"}
                </button>
              </div>
            </form>
          </div>

          <aside className="benefits-column">
            <div className="benefits-card">
              <h4>Gestión de actividades</h4>

              <ul>
                <li>
                  Define una fecha y hora de inicio y
                  finalización.
                </li>

                <li>
                  Consulta automáticamente si está programada,
                  activa o cerrada.
                </li>

                <li>
                  Organiza y divide equitativamente los gastos
                  entre los participantes.
                </li>
              </ul>
            </div>
          </aside>
        </section>
      </main>
    </div>
  );
}

export default CreateGroup;