import { useNavigate } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";

function Dashboard() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
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
            <button className="sidebar-link active">▦ Dashboard</button>
            <button className="sidebar-link">👥 Grupos</button>
            <button className="sidebar-link">↺ Historial</button>
            <button className="sidebar-link">♙ Perfil</button>
          </nav>
        </div>

        <div className="sidebar-bottom">
          <button className="btn btn-primary w-100 mb-3">Registrar pago</button>

          <div className="user-box">
            <div className="avatar">C</div>
            <div>
              <strong>Carlita</strong>
              <small>@carlita</small>
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
            <p>Hola Carlita, aquí tienes un resumen de tus cuentas hoy.</p>
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
              <h2>€1,240.50</h2>
              <p>Repartido en 4 grupos diferentes</p>
            </div>
          </div>

          <div className="summary-card income">
            <div className="summary-icon green">▣</div>
            <div>
              <span>Te deben</span>
              <h2>€856.20</h2>
              <p>Pendiente de cobro de 8 personas</p>
            </div>
          </div>
        </section>

        <section className="quick-actions">
          <button className="btn btn-primary">👥 Crear grupo</button>
          <button className="btn btn-primary">💳 Registrar gasto</button>
          <button className="btn btn-success">💵 Registrar pago</button>
        </section>

        <section className="dashboard-content">
          <div className="groups-section">
            <div className="section-title">
              <h3>Mis grupos</h3>
              <button>Ver todos</button>
            </div>

            <div className="group-card">
              <div className="group-image beach"></div>
              <div className="group-info">
                <strong>Viaje a la playa</strong>
                <small>3 miembros · Hace 2h</small>
                <span>Tú debes</span>
              </div>
              <strong className="amount negative">€45.00</strong>
            </div>

            <div className="group-card">
              <div className="group-image apartment"></div>
              <div className="group-info">
                <strong>Apartamento</strong>
                <small>4 miembros · Hace 1d</small>
                <span>Te deben</span>
              </div>
              <strong className="amount positive">€230.15</strong>
            </div>

            <div className="group-card">
              <div className="group-image dinner"></div>
              <div className="group-info">
                <strong>Cena Viernes</strong>
                <small>6 miembros · Hace 3d</small>
                <span>Saldado</span>
              </div>
              <strong className="amount neutral">€0.00</strong>
            </div>
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

              <div className="movement-row">
                <div>
                  <strong>Compra Supermercado</strong>
                  <small>Hoy, 14:30</small>
                </div>
                <span>Marta</span>
                <span className="tag">Apartamento</span>
                <strong className="negative">€84.20</strong>
              </div>

              <div className="movement-row">
                <div>
                  <strong>Cena Sushi</strong>
                  <small>Ayer, 21:15</small>
                </div>
                <span>Tú</span>
                <span className="tag">Cena Viernes</span>
                <strong className="positive">€120.00</strong>
              </div>

              <div className="movement-row">
                <div>
                  <strong>Gasolina Viaje</strong>
                  <small>12 Oct, 10:00</small>
                </div>
                <span>Carlos</span>
                <span className="tag">Viaje a la playa</span>
                <strong className="negative">€65.00</strong>
              </div>

              <div className="movement-row">
                <div>
                  <strong>Internet Septiembre</strong>
                  <small>10 Oct, 09:00</small>
                </div>
                <span>Tú</span>
                <span className="tag">Apartamento</span>
                <strong className="positive">€40.00</strong>
              </div>
            </div>

            <button className="history-link">Ver historial completo</button>
          </div>
        </section>
      </main>
    </div>
  );
}

export default Dashboard;