import { useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";

function CreateGroup() {
  const navigate = useNavigate();
  const username = localStorage.getItem("username") || "usuario";
  const displayName = username.charAt(0).toUpperCase() + username.slice(1);
  const avatarLetter = username.charAt(0).toUpperCase();

  const [formData, setFormData] = useState({
    nombre: "",
    descripcion: "",
  });

  const [mensaje, setMensaje] = useState("");

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const nuevoGrupo = {
      id: Date.now(),
      nombre: formData.nombre,
      descripcion: formData.descripcion,
      fecha: new Date().toLocaleDateString(),
    };

    const gruposGuardados = JSON.parse(localStorage.getItem("grupos")) || [];

    localStorage.setItem(
      "grupos",
      JSON.stringify([...gruposGuardados, nuevoGrupo])
    );

    setMensaje("Grupo creado correctamente.");

    setFormData({
      nombre: "",
      descripcion: "",
    });

    setTimeout(() => {
      navigate("/dashboard");
    }, 1000);
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

            <button className="sidebar-link active">👥 Grupos</button>
            <button className="sidebar-link">↺ Historial</button>
            <button className="sidebar-link">♙ Perfil</button>
          </nav>
        </div>

        <div className="sidebar-bottom">
          <button className="btn btn-primary w-100 mb-3">Registrar pago</button>

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

          <strong>Crear nuevo grupo</strong>

          <button className="guide-button">ⓘ Guía de Grupos</button>
        </div>

        <header className="create-group-header">
          <h1>Crear nuevo grupo</h1>
          <p>
            Organiza gastos compartidos con amigos, familiares o compañeros de
            piso. Mantén la armonía financiera sin complicaciones.
          </p>
        </header>

        <section className="create-group-grid">
          <div className="create-group-card">
            {mensaje && (
              <div className="alert alert-success text-center" role="alert">
                {mensaje}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label">Nombre del grupo</label>
                <input
                  type="text"
                  name="nombre"
                  className="form-control"
                  placeholder="Ej: Viaje a la playa, Piso 302, Cena amigos..."
                  value={formData.nombre}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="mb-3">
                <label className="form-label">Descripción</label>
                <textarea
                  name="descripcion"
                  className="form-control"
                  rows="5"
                  placeholder="¿De qué trata este grupo? Añade detalles para tus amigos."
                  value={formData.descripcion}
                  onChange={handleChange}
                  required
                ></textarea>
              </div>

              <div className="create-group-footer">
                <small>
                  ⓘ Podrás añadir participantes en el siguiente paso.
                </small>

                <button type="submit" className="btn btn-primary">
                  Crear grupo
                </button>
              </div>
            </form>
          </div>

          <aside className="benefits-column">
            <div className="benefits-card">
              <h4>Beneficios de Grupos</h4>

              <ul>
                <li>División automática de cuentas 50/50 o personalizada.</li>
                <li>Recordatorios de pago amigables sin estrés.</li>
                <li>Reportes de gastos mensuales detallados.</li>
              </ul>
            </div>

            <div className="promo-card">
              <p>
                Únete a más de 10,000 grupos que ya gestionan sus gastos con
                SplitControl.
              </p>
            </div>
          </aside>
        </section>
      </main>
    </div>
  );
}

export default CreateGroup;