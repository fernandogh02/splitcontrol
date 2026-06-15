import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import logo from "../assets/splitcontrol-logo.png";

function Login() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    username: "",
    password: "",
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
        "http://127.0.0.1:8000/api/auth/login/",
        formData
      );

      localStorage.setItem("access", response.data.access);
      localStorage.setItem("refresh", response.data.refresh);
      localStorage.setItem("username", formData.username);

      setMensaje("Inicio de sesión correcto.");

      setFormData({
        username: "",
        password: "",
      });

      navigate("/dashboard");
    } catch (error) {
      setError("Usuario o contraseña incorrectos.");
    }
  };

  return (
    <div className="container d-flex justify-content-center align-items-center min-vh-100">
      <div
        className="card shadow border-0"
        style={{ maxWidth: "430px", width: "100%" }}
      >
        <div className="card-body p-4">
          <div className="text-center mb-3">
            <img
              src={logo}
              alt="Logo SplitControl"
              className="img-fluid mb-3"
              style={{ maxWidth: "230px" }}
            />

            <h3 className="fw-bold">Iniciar sesión</h3>

            <p className="text-muted mb-0">
              Ingresa a tu cuenta de SplitControl
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
                required
              />
            </div>

            <button type="submit" className="btn btn-primary w-100">
              Entrar
            </button>
          </form>

          <div className="text-center mt-4">
            <span className="text-muted">¿No tienes cuenta? </span>
            <Link to="/registro" className="text-decoration-none fw-bold">
              Regístrate
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;