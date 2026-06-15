import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";

function Dashboard() {
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
            <button className="sidebar-link active">▦ Dashboard</button>

            <button className="sidebar-link" onClick={goToCreateGroup}>
              👥 Grupos
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
            <h1>Panel General</h1>
            <p>
              Hola {displayName}, aquí tienes un resumen de tus cuentas hoy.
            </p>
          </div>

          <div className="header-actions">
            <button className="icon-button">🔔</button>
            <button className="icon-button">⚙️</button>
          </div>
        </header>

        <section className="summary-grid">
          <div className="summary-card debt">
            <div className="summary-icon red">▣</div>

            <div>
              <span>Debes a otros</span>
              <h2>€0.00</h2>
              <p>Sin deudas registradas por ahora</p>
            </div>
          </div>

          <div className="summary-card income">
            <div className="summary-icon green">▣</div>

            <div>
              <span>Te deben</span>
              <h2>€0.00</h2>
              <p>Sin cobros pendientes por ahora</p>
            </div>
          </div>
        </section>

        <section className="quick-actions">
          <button className="btn btn-primary" onClick={goToCreateGroup}>
            👥 Crear grupo
          </button>

          <button className="btn btn-primary">
            💳 Registrar gasto
          </button>

          <button className="btn btn-success">
            💵 Registrar pago
          </button>

          <button
            className="btn btn-outline-primary"
            onClick={() => navigate("/resumen")}
          >
            📊 Ver resumen
          </button>
        </section>

        <section className="dashboard-content">
          <div className="groups-section">
            <div className="section-title">
              <h3>Mis grupos</h3>

              <button onClick={goToCreateGroup}>
                Crear nuevo
              </button>
            </div>

            {grupos.length === 0 ? (
              <div className="empty-groups-card">
                <h5>No tienes grupos creados todavía</h5>
                <p>
                  Crea tu primer grupo para organizar gastos compartidos.
                </p>

                <button className="btn btn-primary" onClick={goToCreateGroup}>
                  Crear grupo
                </button>
              </div>
            ) : (
              grupos.map((grupo) => (
                <div className="group-card" key={grupo.id}>
                  <div className="group-image beach"></div>

                  <div className="group-info">
                    <strong>{grupo.nombre}</strong>
                    <small>Creado el {grupo.fecha}</small>
                    <span>{grupo.descripcion}</span>
                  </div>

                  <strong className="amount neutral">€0.00</strong>
                </div>
              ))
            )}
          </div>

          <div className="movements-section">
            <div className="section-title">
              <h3>Últimos movimientos</h3>

              <button>Filtrar</button>
            </div>

            <div className="movements-table">
              <div className="table-header">
                <span>Concepto</span>
                <span>Pagado por</span>
                <span>Grupo</span>
                <span>Monto</span>
              </div>

              <div className="empty-movements">
                Todavía no existen movimientos registrados.
              </div>
            </div>

            <button className="history-link">
              Ver historial completo
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

export default Dashboard;