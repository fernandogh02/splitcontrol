import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";

function ExpenseSummary() {
  const navigate = useNavigate();
  const [grupos, setGrupos] = useState([]);

  const username = localStorage.getItem("username") || "usuario";
  const displayName = username.charAt(0).toUpperCase() + username.slice(1);
  const avatarLetter = username.charAt(0).toUpperCase();

  useEffect(() => {
    const gruposGuardados = JSON.parse(localStorage.getItem("grupos")) || [];
    setGrupos(gruposGuardados);
  }, []);

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
              onClick={() => navigate("/grupos/crear")}
            >
              👥 Grupos
            </button>

            <button className="sidebar-link active">
              📊 Resumen
            </button>

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
        <header className="dashboard-header">
          <div>
            <h1>Resumen general de gastos</h1>
            <p>
              Consulta una vista rápida de tus deudas, montos por recibir y
              grupos registrados.
            </p>
          </div>

          <button
            className="btn btn-outline-primary"
            onClick={() => navigate("/dashboard")}
          >
            Volver al dashboard
          </button>
        </header>

        <section className="summary-grid">
          <div className="summary-card debt">
            <div className="summary-icon red">↘</div>

            <div>
              <span>Total pendiente por pagar</span>
              <h2>€0.00</h2>
              <p>No existen deudas registradas actualmente.</p>
            </div>
          </div>

          <div className="summary-card income">
            <div className="summary-icon green">↗</div>

            <div>
              <span>Total pendiente por recibir</span>
              <h2>€0.00</h2>
              <p>No existen montos pendientes por cobrar actualmente.</p>
            </div>
          </div>
        </section>

        <section className="summary-detail-grid">
          <div className="summary-info-card">
            <h3>Información general de grupos</h3>

            <div className="summary-stat">
              <span>Grupos creados</span>
              <strong>{grupos.length}</strong>
            </div>

            <div className="summary-stat">
              <span>Gastos registrados</span>
              <strong>0</strong>
            </div>

            <div className="summary-stat">
              <span>Pagos registrados</span>
              <strong>0</strong>
            </div>
          </div>

          <div className="summary-info-card">
            <h3>Estado actual</h3>

            <div className="empty-summary-message">
              <strong>No existen gastos registrados todavía.</strong>
              <p>
                Cuando se agreguen gastos al sistema, aquí se mostrarán los
                valores pendientes por pagar, los montos por recibir y el
                resumen relacionado con tus grupos.
              </p>

              <button
                className="btn btn-primary"
                onClick={() => navigate("/dashboard")}
              >
                Volver al panel general
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default ExpenseSummary;