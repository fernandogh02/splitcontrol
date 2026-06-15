import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import logo from "../assets/splitcontrol-logo.png";

function Register() {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    password2: "",
  });

  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setMensaje("");
    setError("");

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/api/auth/registro/",
        formData
      );

      setMensaje(response.data.mensaje);

      setFormData({
        username: "",
        email: "",
        password: "",
        password2: "",
      });
    } catch (error) {
      if (error.response && error.response.data) {
        const errores = error.response.data;
        const textoErrores = Object.values(errores).flat().join(" ");
        setError(textoErrores);
      } else {
        setError("No se pudo conectar con el servidor.");
      }
    }
  };

  return (
    <div className="container d-flex justify-content-center align-items-center min-vh-100">
      <div
        className="card shadow border-0"
        style={{ maxWidth: "460px", width: "100%" }}
      >
        <div className="card-body p-4">
          <div className="text-center mb-3">
            <img
              src={logo}
              alt="Logo SplitControl"
              className="img-fluid mb-3"
              style={{ maxWidth: "230px" }}
            />

            <h3 className="fw-bold">Crear cuenta</h3>

            <p className="text-muted mb-0">
              Regístrate para empezar a usar SplitControl
            </p>
          </div>

          {mensaje && (
            <div className="alert alert-success text-center" role="alert">
              {mensaje}
            </div>
          )}

          {error && (
            <div className="alert alert-danger text-center" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Usuario</label>
              <input
                type="text"
                name="username"
                className="form-control"
                value={formData.username}
                onChange={handleChange}
                placeholder="Ej: fernando"
                required
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Correo electrónico</label>
              <input
                type="email"
                name="email"
                className="form-control"
                value={formData.email}
                onChange={handleChange}
                placeholder="Ej: correo@ejemplo.com"
                required
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Contraseña</label>
              <input
                type="password"
                name="password"
                className="form-control"
                value={formData.password}
                onChange={handleChange}
                placeholder="Mínimo 8 caracteres"
                required
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Confirmar contraseña</label>
              <input
                type="password"
                name="password2"
                className="form-control"
                value={formData.password2}
                onChange={handleChange}
                placeholder="Repite tu contraseña"
                required
              />
            </div>

            <button type="submit" className="btn btn-primary w-100">
              Registrarse
            </button>
          </form>

          <div className="text-center mt-4">
            <span className="text-muted">¿Ya tienes cuenta? </span>
            <Link to="/login" className="text-decoration-none fw-bold">
              Inicia sesión
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Register;