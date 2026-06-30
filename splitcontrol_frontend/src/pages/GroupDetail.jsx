import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";

function GroupDetail() {
  const navigate = useNavigate();
  const { id } = useParams();

  const [grupo, setGrupo] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  const username = localStorage.getItem("username") || "usuario";
  const displayName = username.charAt(0).toUpperCase() + username.slice(1);
  const avatarLetter = username.charAt(0).toUpperCase();

  useEffect(() => {
    const obtenerDetalleGrupo = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        setError("Tu sesión ha expirado. Inicia sesión nuevamente.");
        setCargando(false);
        return;
      }

      try {
        const response = await fetch(`http://127.0.0.1:8000/api/grupos/${id}/`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error("No se pudo cargar el detalle del grupo.");
        }

        const data = await response.json();
        setGrupo(data);
      } catch (error) {
        setError("No se pudo cargar la información del grupo.");
      } finally {
        setCargando(false);
      }
    };

    obtenerDetalleGrupo();
  }, [id]);

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

            <button className="sidebar-link active">👥 Grupos</button>
            <button className="sidebar-link">↺ Historial</button>
            <button className="sidebar-link">♙ Perfil</button>
          </nav>
        </div>

        <div className="sidebar-bottom">
          <button className="btn btn-primary w-100 mb-3">
            Registrar pago
          </button>

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
        <div className="create-group-top">
          <button
            className="back-button"
            onClick={() => navigate("/dashboard")}
          >
            ← Grupos
          </button>

          <span>›</span>

          <strong>Detalle del grupo</strong>
        </div>

        {cargando ? (
          <div className="create-group-card">
            <h4>Cargando detalle...</h4>
            <p>Estamos consultando la información del grupo.</p>
          </div>
        ) : error ? (
          <div className="create-group-card">
            <div className="alert alert-danger" role="alert">
              {error}
            </div>

            <button
              className="btn btn-primary"
              onClick={() => navigate("/dashboard")}
            >
              Volver al dashboard
            </button>
          </div>
        ) : (
          <>
            <header className="create-group-header">
              <h1>{grupo.nombre}</h1>
              <p>
                Revisa la información general del grupo y prepara la gestión de
                participantes y gastos compartidos.
              </p>
            </header>

            <section className="create-group-grid">
              <div className="create-group-card">
                <h4>Información del grupo</h4>

                <div className="mt-4">
                  <label className="form-label">Nombre del grupo</label>
                  <div className="form-control bg-light">
                    {grupo.nombre}
                  </div>
                </div>

                <div className="mt-3">
                  <label className="form-label">Descripción</label>
                  <div className="form-control bg-light" style={{ minHeight: "110px" }}>
                    {grupo.descripcion || "Sin descripción"}
                  </div>
                </div>

                <div className="mt-3">
                  <label className="form-label">Creado por</label>
                  <div className="form-control bg-light">
                    {grupo.creador_username || username}
                  </div>
                </div>

                <div className="mt-3">
                  <label className="form-label">Fecha de creación</label>
                  <div className="form-control bg-light">
                    {grupo.fecha_creacion
                      ? new Date(grupo.fecha_creacion).toLocaleDateString()
                      : "Sin fecha"}
                  </div>
                </div>

                <div className="create-group-footer mt-4">
                  <small>
                    ⓘ La gestión de participantes se implementará en la siguiente historia.
                  </small>

                  <button
                    className="btn btn-primary"
                    onClick={() => navigate("/dashboard")}
                  >
                    Volver
                  </button>
                </div>
              </div>

              <aside className="benefits-column">
                <div className="benefits-card">
                  <h4>Próximas funciones</h4>

                  <ul>
                    <li>Añadir participantes al grupo.</li>
                    <li>Registrar gastos compartidos.</li>
                    <li>Consultar balances entre participantes.</li>
                  </ul>
                </div>
              </aside>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default GroupDetail;