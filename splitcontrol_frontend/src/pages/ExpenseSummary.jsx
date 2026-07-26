import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";

const API_BASE_URL = "http://127.0.0.1:8000/api";

const formatearMonto = (monto) =>
  new Intl.NumberFormat("es-EC", {
    style: "currency",
    currency: "USD",
  }).format(Number(monto) || 0);

const obtenerMensajeError = (
  data,
  mensajePredeterminado = "No se pudo completar la operación."
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

const leerJsonSeguro = async (response, valorPredeterminado = {}) => {
  try {
    return await response.json();
  } catch {
    return valorPredeterminado;
  }
};

function ExpenseSummary() {
  const navigate = useNavigate();

  const [grupos, setGrupos] = useState([]);
  const [deudas, setDeudas] = useState([]);
  const [totalPendientePagar, setTotalPendientePagar] =
    useState("0.00");
  const [totalPendienteRecibir, setTotalPendienteRecibir] =
    useState("0.00");
  const [totalGastosRegistrados, setTotalGastosRegistrados] =
    useState(0);
  const [totalPagosRegistrados, setTotalPagosRegistrados] =
    useState(0);
  const [totalGeneralGastos, setTotalGeneralGastos] =
    useState("0.00");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  const username =
    localStorage.getItem("username") || "usuario";

  const displayName =
    username.charAt(0).toUpperCase() + username.slice(1);

  const avatarLetter =
    username.charAt(0).toUpperCase();

  const obtenerDatosResumen = useCallback(async () => {
    const token = localStorage.getItem("access");

    if (!token) {
      setError(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      setCargando(false);
      return;
    }

    try {
      setCargando(true);
      setError("");

      const headers = {
        Authorization: `Bearer ${token}`,
      };

      const [respuestaGrupos, respuestaDeudas] =
        await Promise.all([
          fetch(`${API_BASE_URL}/grupos/`, {
            method: "GET",
            headers,
          }),
          fetch(`${API_BASE_URL}/mis-deudas/`, {
            method: "GET",
            headers,
          }),
        ]);

      const datosGrupos = await leerJsonSeguro(
        respuestaGrupos,
        []
      );

      const datosDeudas = await leerJsonSeguro(
        respuestaDeudas,
        {}
      );

      if (!respuestaGrupos.ok) {
        throw new Error(
          obtenerMensajeError(
            datosGrupos,
            "No se pudieron cargar tus actividades."
          )
        );
      }

      if (!respuestaDeudas.ok) {
        throw new Error(
          obtenerMensajeError(
            datosDeudas,
            "No se pudo cargar el resumen de tus deudas."
          )
        );
      }

      const gruposDisponibles = Array.isArray(datosGrupos)
        ? datosGrupos
        : [];

      const deudasDisponibles = Array.isArray(
        datosDeudas.deudas
      )
        ? datosDeudas.deudas
        : [];

      setGrupos(gruposDisponibles);
      setDeudas(deudasDisponibles);
      setTotalPendientePagar(
        datosDeudas.monto_total_pendiente || "0.00"
      );

      const totalGastosGrupos = gruposDisponibles.reduce(
        (total, grupo) =>
          total + Number(grupo.total_gastos || 0),
        0
      );

      setTotalGeneralGastos(
        totalGastosGrupos.toFixed(2)
      );

      const resultadosPorGrupo = await Promise.allSettled(
        gruposDisponibles.map(async (grupo) => {
          const [
            respuestaBalances,
            respuestaGastos,
            respuestaPagos,
          ] = await Promise.all([
            fetch(
              `${API_BASE_URL}/grupos/${grupo.id}/balances/`,
              {
                method: "GET",
                headers,
              }
            ),
            fetch(
              `${API_BASE_URL}/grupos/${grupo.id}/gastos/`,
              {
                method: "GET",
                headers,
              }
            ),
            fetch(
              `${API_BASE_URL}/grupos/${grupo.id}/pagos/`,
              {
                method: "GET",
                headers,
              }
            ),
          ]);

          const datosBalances = await leerJsonSeguro(
            respuestaBalances,
            {}
          );

          const datosGastos = await leerJsonSeguro(
            respuestaGastos,
            {}
          );

          const datosPagos = await leerJsonSeguro(
            respuestaPagos,
            {}
          );

          const balances = respuestaBalances.ok &&
            Array.isArray(datosBalances.balances)
            ? datosBalances.balances
            : [];

          const gastos = respuestaGastos.ok &&
            Array.isArray(datosGastos.gastos)
            ? datosGastos.gastos
            : [];

          const pagos = respuestaPagos.ok &&
            Array.isArray(datosPagos.pagos)
            ? datosPagos.pagos
            : [];

          const balanceUsuario = balances.find(
            (balance) =>
              balance.participante?.username === username
          );

          const saldoAFavor =
            balanceUsuario?.estado === "a_favor"
              ? Math.max(
                  Number(balanceUsuario.balance || 0),
                  0
                )
              : 0;

          return {
            saldoAFavor,
            cantidadGastos: gastos.length,
            cantidadPagos: pagos.length,
          };
        })
      );

      const resumenCalculado = resultadosPorGrupo.reduce(
        (acumulado, resultado) => {
          if (resultado.status !== "fulfilled") {
            return acumulado;
          }

          return {
            saldoAFavor:
              acumulado.saldoAFavor +
              resultado.value.saldoAFavor,
            cantidadGastos:
              acumulado.cantidadGastos +
              resultado.value.cantidadGastos,
            cantidadPagos:
              acumulado.cantidadPagos +
              resultado.value.cantidadPagos,
          };
        },
        {
          saldoAFavor: 0,
          cantidadGastos: 0,
          cantidadPagos: 0,
        }
      );

      setTotalPendienteRecibir(
        resumenCalculado.saldoAFavor.toFixed(2)
      );
      setTotalGastosRegistrados(
        resumenCalculado.cantidadGastos
      );
      setTotalPagosRegistrados(
        resumenCalculado.cantidadPagos
      );
    } catch (errorCarga) {
      setGrupos([]);
      setDeudas([]);
      setTotalPendientePagar("0.00");
      setTotalPendienteRecibir("0.00");
      setTotalGastosRegistrados(0);
      setTotalPagosRegistrados(0);
      setTotalGeneralGastos("0.00");
      setError(
        errorCarga.message ||
          "No se pudo cargar el resumen general."
      );
    } finally {
      setCargando(false);
    }
  }, [username]);

  useEffect(() => {
    const temporizador = setTimeout(() => {
      obtenerDatosResumen();
    }, 0);

    return () => {
      clearTimeout(temporizador);
    };
  }, [obtenerDatosResumen]);

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

            <button
              className="sidebar-link"
              onClick={() => navigate("/mis-deudas")}
            >
              💳 Mis deudas
            </button>

            <button
              className="sidebar-link"
              onClick={() => navigate("/notificaciones")}
            >
              🔔 Notificaciones
            </button>

            <button className="sidebar-link active">
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
          <button
            type="button"
            className="btn btn-primary w-100 mb-3"
            onClick={() => navigate("/mis-deudas")}
          >
            Consultar mis deudas
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
              Consulta tus obligaciones, saldos a favor y la
              actividad económica registrada en tus grupos.
            </p>
          </div>

          <div className="d-flex gap-2">
            <button
              type="button"
              className="btn btn-outline-primary"
              onClick={obtenerDatosResumen}
              disabled={cargando}
            >
              {cargando
                ? "Actualizando..."
                : "Actualizar resumen"}
            </button>

            <button
              className="btn btn-outline-secondary"
              onClick={() => navigate("/dashboard")}
            >
              Volver al dashboard
            </button>
          </div>
        </header>

        {error && (
          <div
            className="alert alert-danger"
            role="alert"
          >
            {error}
          </div>
        )}

        <section className="summary-grid">
          <div className="summary-card debt">
            <div className="summary-icon red">↘</div>

            <div className="w-100">
              <span>Total pendiente por pagar</span>

              <h2>
                {cargando
                  ? "Consultando..."
                  : formatearMonto(totalPendientePagar)}
              </h2>

              <p>
                {cargando
                  ? "Cargando tus obligaciones pendientes."
                  : deudas.length > 0
                    ? `${deudas.length} deuda${
                        deudas.length === 1 ? "" : "s"
                      } pendiente${
                        deudas.length === 1 ? "" : "s"
                      }.`
                    : "No tienes deudas pendientes actualmente."}
              </p>

              <button
                type="button"
                className="btn btn-outline-danger btn-sm"
                onClick={() => navigate("/mis-deudas")}
              >
                Ver mis deudas
              </button>
            </div>
          </div>

          <div className="summary-card income">
            <div className="summary-icon green">↗</div>

            <div className="w-100">
              <span>Total pendiente por recibir</span>

              <h2>
                {cargando
                  ? "Consultando..."
                  : formatearMonto(totalPendienteRecibir)}
              </h2>

              <p>
                {cargando
                  ? "Consultando tus balances."
                  : Number(totalPendienteRecibir) > 0
                    ? "Tienes saldos a favor en tus actividades."
                    : "No tienes montos pendientes por recibir."}
              </p>
            </div>
          </div>
        </section>

        <section className="summary-detail-grid">
          <div className="summary-info-card">
            <h3>Información general</h3>

            <div className="summary-stat">
              <span>Actividades disponibles</span>
              <strong>
                {cargando ? "..." : grupos.length}
              </strong>
            </div>

            <div className="summary-stat">
              <span>Gastos registrados</span>
              <strong>
                {cargando
                  ? "..."
                  : totalGastosRegistrados}
              </strong>
            </div>

            <div className="summary-stat">
              <span>Pagos registrados</span>
              <strong>
                {cargando
                  ? "..."
                  : totalPagosRegistrados}
              </strong>
            </div>

            <div className="summary-stat">
              <span>Total común acumulado</span>
              <strong>
                {cargando
                  ? "..."
                  : formatearMonto(totalGeneralGastos)}
              </strong>
            </div>
          </div>

          <div className="summary-info-card">
            <h3>Estado actual</h3>

            {cargando ? (
              <div className="empty-summary-message">
                <strong>Cargando información económica...</strong>

                <p>
                  Estamos consultando tus actividades, gastos,
                  pagos, balances y obligaciones pendientes.
                </p>
              </div>
            ) : deudas.length === 0 &&
              Number(totalPendienteRecibir) <= 0 ? (
              <div className="empty-summary-message">
                <strong>
                  Tu situación económica está al día.
                </strong>

                <p>
                  No tienes deudas pendientes ni saldos por
                  recibir en las actividades consultadas.
                </p>

                <button
                  className="btn btn-primary"
                  onClick={() => navigate("/dashboard")}
                >
                  Volver al panel general
                </button>
              </div>
            ) : (
              <div className="empty-summary-message">
                <strong>
                  Tienes información económica pendiente.
                </strong>

                <p>
                  Revisa tus deudas y los balances de tus
                  actividades para conocer el detalle de cada
                  valor.
                </p>

                <div className="d-flex flex-wrap gap-2 justify-content-center">
                  <button
                    className="btn btn-primary"
                    onClick={() => navigate("/mis-deudas")}
                  >
                    Revisar mis deudas
                  </button>

                  <button
                    className="btn btn-outline-primary"
                    onClick={() => navigate("/dashboard")}
                  >
                    Ver actividades
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>

        {!cargando && grupos.length > 0 && (
          <section className="summary-info-card mt-4">
            <div className="d-flex justify-content-between align-items-center gap-3 mb-3">
              <div>
                <h3 className="mb-1">
                  Actividades incluidas en el resumen
                </h3>

                <small className="text-muted">
                  Los totales se calculan con las actividades
                  creadas por ti o compartidas contigo.
                </small>
              </div>

              <span className="badge bg-light text-dark border">
                {grupos.length}
              </span>
            </div>

            <div className="d-flex flex-column gap-2">
              {grupos.map((grupo) => (
                <button
                  key={grupo.id}
                  type="button"
                  className="btn btn-light border text-start d-flex justify-content-between align-items-center gap-3 p-3"
                  onClick={() =>
                    navigate(`/grupos/${grupo.id}`)
                  }
                >
                  <div>
                    <strong className="d-block">
                      {grupo.nombre}
                    </strong>

                    <small className="text-muted">
                      Creado por @{grupo.creador_username}
                    </small>
                  </div>

                  <div className="text-end">
                    <strong>
                      {formatearMonto(
                        grupo.total_gastos
                      )}
                    </strong>

                    <small className="text-muted d-block">
                      Total de gastos
                    </small>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default ExpenseSummary;