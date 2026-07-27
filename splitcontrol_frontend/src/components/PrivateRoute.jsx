import {
  useEffect,
  useState,
} from "react";
import {
  Navigate,
} from "react-router-dom";
import {
  asegurarTokenAcceso,
  limpiarSesion,
} from "../utils/authFetch";

function PrivateRoute({ children }) {
  const [estadoSesion, setEstadoSesion] =
    useState("validando");

  useEffect(() => {
    const validarSesion = async () => {
      try {
        const token =
          await asegurarTokenAcceso();

        setEstadoSesion(
          token
            ? "autenticada"
            : "expirada"
        );
      } catch {
        limpiarSesion();
        setEstadoSesion("expirada");
      }
    };

    const temporizador = setTimeout(() => {
      validarSesion();
    }, 0);

    const manejarSesionExpirada = () => {
      setEstadoSesion("expirada");
    };

    window.addEventListener(
      "auth:expired",
      manejarSesionExpirada
    );

    return () => {
      clearTimeout(temporizador);

      window.removeEventListener(
        "auth:expired",
        manejarSesionExpirada
      );
    };
  }, []);

  if (estadoSesion === "validando") {
    return (
      <div className="min-vh-100 d-flex align-items-center justify-content-center">
        <div
          className="alert alert-light border"
          role="status"
        >
          Validando tu sesión...
        </div>
      </div>
    );
  }

  if (estadoSesion === "expirada") {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          mensaje:
            "Tu sesión expiró. Inicia sesión nuevamente.",
        }}
      />
    );
  }

  return children;
}

export default PrivateRoute;