import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import logo from "../assets/splitcontrol-logo.png";

const obtenerFechaActual = () => {
  const fecha = new Date();
  const diferenciaZonaHoraria = fecha.getTimezoneOffset() * 60000;

  return new Date(fecha.getTime() - diferenciaZonaHoraria)
    .toISOString()
    .split("T")[0];
};

const formatearMonto = (monto) =>
  new Intl.NumberFormat("es-EC", {
    style: "currency",
    currency: "USD",
  }).format(Number(monto) || 0);

const formatearBalance = (balance) => {
  const valor = Number(balance) || 0;

  if (valor > 0) {
    return `+${formatearMonto(valor)}`;
  }

  if (valor < 0) {
    return `-${formatearMonto(Math.abs(valor))}`;
  }

  return formatearMonto(0);
};

const obtenerTextoEstadoBalance = (estado) => {
  if (estado === "a_favor") {
    return "A favor";
  }

  if (estado === "debe") {
    return "Debe";
  }

  return "Saldado";
};

const formatearFecha = (fecha) => {
  if (!fecha) {
    return "Sin fecha";
  }

  return new Date(`${fecha}T00:00:00`).toLocaleDateString("es-EC");
};

const formatearFechaHora = (fecha) => {
  if (!fecha) {
    return "Sin fecha";
  }

  return new Date(fecha).toLocaleString("es-EC");
};

const convertirFechaISOAInput = (fecha) => {
  if (!fecha) {
    return "";
  }

  const fechaConvertida = new Date(fecha);

  if (Number.isNaN(fechaConvertida.getTime())) {
    return "";
  }

  const diferenciaZonaHoraria =
    fechaConvertida.getTimezoneOffset() * 60000;

  return new Date(
    fechaConvertida.getTime() - diferenciaZonaHoraria
  )
    .toISOString()
    .slice(0, 16);
};

const convertirFechaLocalAISO = (fecha) => {
  if (!fecha) {
    return null;
  }

  const fechaConvertida = new Date(fecha);

  if (Number.isNaN(fechaConvertida.getTime())) {
    return null;
  }

  return fechaConvertida.toISOString();
};

const obtenerConfiguracionEstadoActividad = (estado) => {
  if (estado === "programada") {
    return {
      texto: "Programada",
      clase: "bg-info text-dark",
      descripcion: "La actividad todavía no ha comenzado.",
    };
  }

  if (estado === "activa") {
    return {
      texto: "Activa",
      clase: "bg-success",
      descripcion: "La actividad se encuentra dentro de su vigencia.",
    };
  }

  if (estado === "cerrada") {
    return {
      texto: "Cerrada",
      clase: "bg-secondary",
      descripcion: "La fecha de finalización ya terminó.",
    };
  }

  return {
    texto: "Sin configurar",
    clase: "bg-warning text-dark",
    descripcion: "La actividad todavía no tiene una vigencia definida.",
  };
};

function GroupDetail() {
  const navigate = useNavigate();
  const { id } = useParams();

  const [grupo, setGrupo] = useState(null);
  const [usuarios, setUsuarios] = useState([]);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState("");

  const [gastoData, setGastoData] = useState({
    descripcion: "",
    monto: "",
    fecha_gasto: obtenerFechaActual(),
  });

  const [registrandoGasto, setRegistrandoGasto] = useState(false);

  const [pagoData, setPagoData] = useState({
    monto: "",
    fecha_pago: obtenerFechaActual(),
  });
  const [registrandoPago, setRegistrandoPago] = useState(false);
  const [mensajePago, setMensajePago] = useState("");
  const [errorPago, setErrorPago] = useState("");

  const [pagos, setPagos] = useState([]);
  const [cargandoPagos, setCargandoPagos] = useState(true);
  const [errorPagos, setErrorPagos] = useState("");
  const [mensajeListadoPagos, setMensajeListadoPagos] =
    useState("");

  const [detallePagoAbierto, setDetallePagoAbierto] = useState(false);
  const [pagoSeleccionado, setPagoSeleccionado] = useState(null);
  const [cargandoDetallePago, setCargandoDetallePago] =
    useState(false);
  const [errorDetallePago, setErrorDetallePago] = useState("");

  const [gastos, setGastos] = useState([]);
  const [totalGastos, setTotalGastos] = useState("0.00");
  const [cargandoGastos, setCargandoGastos] = useState(true);
  const [errorGastos, setErrorGastos] = useState("");

  const [balances, setBalances] = useState([]);
  const [resumenBalances, setResumenBalances] = useState(null);
  const [cargandoBalances, setCargandoBalances] = useState(true);
  const [errorBalances, setErrorBalances] = useState("");

  const [resumenEconomico, setResumenEconomico] = useState(null);
  const [cuotasEconomicas, setCuotasEconomicas] = useState([]);
  const [
    cargandoResumenEconomico,
    setCargandoResumenEconomico,
  ] = useState(true);
  const [
    errorResumenEconomico,
    setErrorResumenEconomico,
  ] = useState("");

  const [detalleGastoAbierto, setDetalleGastoAbierto] = useState(false);
  const [gastoSeleccionado, setGastoSeleccionado] = useState(null);
  const [cargandoDetalleGasto, setCargandoDetalleGasto] = useState(false);
  const [errorDetalleGasto, setErrorDetalleGasto] = useState("");

  const [edicionGastoAbierta, setEdicionGastoAbierta] = useState(false);
  const [gastoEditandoId, setGastoEditandoId] = useState(null);
  const [edicionGastoData, setEdicionGastoData] = useState({
    descripcion: "",
    monto: "",
    fecha_gasto: obtenerFechaActual(),
  });
  const [guardandoEdicionGasto, setGuardandoEdicionGasto] = useState(false);
  const [errorEdicionGasto, setErrorEdicionGasto] = useState("");
  const [eliminandoGastoId, setEliminandoGastoId] = useState(null);

  const [participanteEditando, setParticipanteEditando] = useState(null);
  const [notaTemporal, setNotaTemporal] = useState("");
  const [notasParticipantes, setNotasParticipantes] = useState({});

  const [formData, setFormData] = useState({
    nombre: "",
    descripcion: "",
    fecha_inicio: "",
    fecha_fin: "",
  });

  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [modoEdicion, setModoEdicion] = useState(false);
  const [agregandoParticipante, setAgregandoParticipante] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  const [membresias, setMembresias] = useState([]);
  const [resumenMembresias, setResumenMembresias] = useState({
    total_membresias: 0,
    total_activas: 0,
    total_retiradas: 0,
  });
  const [cargandoMembresias, setCargandoMembresias] =
    useState(true);
  const [errorMembresias, setErrorMembresias] = useState("");

  const username = localStorage.getItem("username") || "usuario";
  const displayName =
    username.charAt(0).toUpperCase() + username.slice(1);
  const avatarLetter = username.charAt(0).toUpperCase();
  const esCreador = grupo?.creador_username === username;
  const actividadProgramada = grupo?.estado === "programada";
  const actividadActiva = grupo?.estado === "activa";
  const actividadCerrada = grupo?.estado === "cerrada";
  const usuarioActual = grupo?.participantes?.find(
    (participante) => participante.username === username
  );
  const cuotaUsuarioActual = cuotasEconomicas.find(
    (cuota) =>
      cuota.participante?.username === username
  );
  const saldoPendienteUsuario = Number(
    cuotaUsuarioActual?.saldo_pendiente || 0
  );
  const cuotaUsuarioSaldada =
    cuotaUsuarioActual?.estado === "saldado" ||
    saldoPendienteUsuario <= 0;
  const puedeRegistrarPagos =
    Boolean(grupo) &&
    actividadActiva &&
    Boolean(usuarioActual);
  const puedeRegistrarAporte =
    puedeRegistrarPagos &&
    Boolean(cuotaUsuarioActual) &&
    saldoPendienteUsuario > 0;
  const puedeRegistrarGastos =
    Boolean(grupo) && actividadActiva;

  const obtenerMembresias = useCallback(async () => {
    const token = localStorage.getItem("access");

    if (!token) {
      setErrorMembresias(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      setCargandoMembresias(false);
      return;
    }

    try {
      setCargandoMembresias(true);
      setErrorMembresias("");

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/membresias/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
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
          data.error ||
            "No se pudo cargar el historial de membresías."
        );
      }

      setMembresias(
        Array.isArray(data.membresias)
          ? data.membresias
          : []
      );

      setResumenMembresias({
        total_membresias:
          Number(data.total_membresias) || 0,
        total_activas:
          Number(data.total_activas) || 0,
        total_retiradas:
          Number(data.total_retiradas) || 0,
      });
    } catch (errorHistorial) {
      setMembresias([]);
      setResumenMembresias({
        total_membresias: 0,
        total_activas: 0,
        total_retiradas: 0,
      });
      setErrorMembresias(
        errorHistorial.message ||
          "No se pudo cargar el historial de membresías."
      );
    } finally {
      setCargandoMembresias(false);
    }
  }, [id]);

  const obtenerResumenEconomico = useCallback(async () => {
    const token = localStorage.getItem("access");

    if (!token) {
      setErrorResumenEconomico(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      setCargandoResumenEconomico(false);
      return;
    }

    try {
      setCargandoResumenEconomico(true);
      setErrorResumenEconomico("");

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/resumen-economico/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
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
          data.error ||
            "No se pudo cargar el resumen económico."
        );
      }

      setResumenEconomico(data.resumen || null);
      setCuotasEconomicas(
        Array.isArray(data.cuotas) ? data.cuotas : []
      );
    } catch (errorResumen) {
      setResumenEconomico(null);
      setCuotasEconomicas([]);
      setErrorResumenEconomico(
        errorResumen.message ||
          "No se pudo cargar el resumen económico."
      );
    } finally {
      setCargandoResumenEconomico(false);
    }
  }, [id]);

  const obtenerPagos = useCallback(async () => {
    const token = localStorage.getItem("access");

    if (!token) {
      setErrorPagos(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      setCargandoPagos(false);
      return;
    }

    try {
      setCargandoPagos(true);
      setErrorPagos("");

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/pagos/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
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
          data.error ||
            "No se pudo cargar el historial de pagos."
        );
      }

      setPagos(
        Array.isArray(data.pagos) ? data.pagos : []
      );
      setMensajeListadoPagos(data.mensaje || "");
    } catch (errorListadoPagos) {
      setPagos([]);
      setMensajeListadoPagos("");
      setErrorPagos(
        errorListadoPagos.message ||
          "No se pudo cargar el historial de pagos."
      );
    } finally {
      setCargandoPagos(false);
    }
  }, [id]);

  const obtenerBalances = async () => {
    const token = localStorage.getItem("access");

    if (!token) {
      setErrorBalances(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      setCargandoBalances(false);
      return;
    }

    try {
      setCargandoBalances(true);
      setErrorBalances("");

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/balances/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
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
          data.error || "No se pudieron cargar los balances."
        );
      }

      setBalances(
        Array.isArray(data.balances) ? data.balances : []
      );
      setResumenBalances(data.resumen || null);
    } catch (errorBalance) {
      setBalances([]);
      setResumenBalances(null);
      setErrorBalances(
        errorBalance.message ||
          "No se pudieron cargar los balances del grupo."
      );
    } finally {
      setCargandoBalances(false);
    }
  };

  useEffect(() => {
    const obtenerDetalleGrupo = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        setError("Tu sesión ha expirado. Inicia sesión nuevamente.");
        setCargando(false);
        return;
      }

      try {
        const response = await fetch(
          `http://127.0.0.1:8000/api/grupos/${id}/`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error("No se pudo cargar el detalle del grupo.");
        }

        const data = await response.json();

        setGrupo(data);
        setTotalGastos(data.total_gastos || "0.00");

        setFormData({
          nombre: data.nombre || "",
          descripcion: data.descripcion || "",
          fecha_inicio: convertirFechaISOAInput(
            data.fecha_inicio
          ),
          fecha_fin: convertirFechaISOAInput(
            data.fecha_fin
          ),
        });
      } catch {
        setError("No se pudo cargar la información del grupo.");
      } finally {
        setCargando(false);
      }
    };

    obtenerDetalleGrupo();
  }, [id]);

  useEffect(() => {
  const temporizador = setTimeout(() => {
    obtenerMembresias();
  }, 0);

  return () => {
    clearTimeout(temporizador);
  };
}, [obtenerMembresias]);

  useEffect(() => {
    const obtenerUsuarios = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        return;
      }

      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/usuarios/",
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error("No se pudieron cargar los usuarios.");
        }

        const data = await response.json();
        setUsuarios(data);
      } catch (errorUsuarios) {
        console.error("Error al cargar usuarios:", errorUsuarios);
      }
    };

    obtenerUsuarios();
  }, []);

  useEffect(() => {
    const obtenerGastos = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        setErrorGastos(
          "Tu sesión ha expirado. Inicia sesión nuevamente."
        );
        setCargandoGastos(false);
        return;
      }

      try {
        setErrorGastos("");

        const response = await fetch(
          `http://127.0.0.1:8000/api/grupos/${id}/gastos/`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error || "No se pudieron cargar los gastos."
          );
        }

        setGastos(Array.isArray(data.gastos) ? data.gastos : []);
        setTotalGastos(data.total_gastos || "0.00");
      } catch (errorListado) {
        setErrorGastos(
          errorListado.message ||
            "No se pudieron cargar los gastos del grupo."
        );
      } finally {
        setCargandoGastos(false);
      }
    };

    obtenerGastos();
  }, [id]);

  useEffect(() => {
    const temporizador = setTimeout(() => {
      obtenerResumenEconomico();
    }, 0);

    return () => {
      clearTimeout(temporizador);
    };
  }, [obtenerResumenEconomico]);

  useEffect(() => {
    const temporizador = setTimeout(() => {
      obtenerPagos();
    }, 0);

    return () => {
      clearTimeout(temporizador);
    };
  }, [obtenerPagos]);

  useEffect(() => {
    const cargarBalancesIniciales = async () => {
      const token = localStorage.getItem("access");

      if (!token) {
        setErrorBalances(
          "Tu sesión ha expirado. Inicia sesión nuevamente."
        );
        setCargandoBalances(false);
        return;
      }

      try {
        setCargandoBalances(true);
        setErrorBalances("");

        const response = await fetch(
          `http://127.0.0.1:8000/api/grupos/${id}/balances/`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
            },
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
            data.error || "No se pudieron cargar los balances."
          );
        }

        setBalances(
          Array.isArray(data.balances) ? data.balances : []
        );
        setResumenBalances(data.resumen || null);
      } catch (errorBalance) {
        setBalances([]);
        setResumenBalances(null);
        setErrorBalances(
          errorBalance.message ||
            "No se pudieron cargar los balances del grupo."
        );
      } finally {
        setCargandoBalances(false);
      }
    };

    cargarBalancesIniciales();
  }, [id]);

  const verDetallePago = async (pagoId) => {
    const token = localStorage.getItem("access");

    setDetallePagoAbierto(true);
    setPagoSeleccionado(null);
    setErrorDetallePago("");

    if (!token) {
      setErrorDetallePago(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      return;
    }

    try {
      setCargandoDetallePago(true);

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/pagos/${pagoId}/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
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
          data.error ||
            "No se pudo cargar el detalle del pago."
        );
      }

      setPagoSeleccionado(data.pago || null);
    } catch (errorDetalle) {
      setErrorDetallePago(
        errorDetalle.message ||
          "No se pudo cargar el detalle del pago."
      );
    } finally {
      setCargandoDetallePago(false);
    }
  };

  const cerrarDetallePago = () => {
    setDetallePagoAbierto(false);
    setPagoSeleccionado(null);
    setErrorDetallePago("");
    setCargandoDetallePago(false);
  };

  const verDetalleGasto = async (gastoId) => {
    const token = localStorage.getItem("access");

    setDetalleGastoAbierto(true);
    setGastoSeleccionado(null);
    setErrorDetalleGasto("");

    if (!token) {
      setErrorDetalleGasto(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      return;
    }

    try {
      setCargandoDetalleGasto(true);

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/gastos/${gastoId}/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "No se pudo cargar el detalle del gasto."
        );
      }

      setGastoSeleccionado(data.gasto || null);
    } catch (errorDetalle) {
      setErrorDetalleGasto(
        errorDetalle.message ||
          "No se pudo cargar el detalle del gasto."
      );
    } finally {
      setCargandoDetalleGasto(false);
    }
  };

  const cerrarDetalleGasto = () => {
    setDetalleGastoAbierto(false);
    setGastoSeleccionado(null);
    setErrorDetalleGasto("");
    setCargandoDetalleGasto(false);
  };

  const abrirEdicionGasto = (gasto) => {
    setGastoEditandoId(gasto.id);
    setEdicionGastoData({
      descripcion: gasto.descripcion || "",
      monto: gasto.monto || "",
      fecha_gasto: gasto.fecha_gasto || obtenerFechaActual(),
    });
    setErrorEdicionGasto("");
    setMensaje("");
    setError("");
    setEdicionGastoAbierta(true);
  };

  const cerrarEdicionGasto = () => {
    if (guardandoEdicionGasto) {
      return;
    }

    setEdicionGastoAbierta(false);
    setGastoEditandoId(null);
    setEdicionGastoData({
      descripcion: "",
      monto: "",
      fecha_gasto: obtenerFechaActual(),
    });
    setErrorEdicionGasto("");
  };

  const handleEdicionGastoChange = (e) => {
    setEdicionGastoData({
      ...edicionGastoData,
      [e.target.name]: e.target.value,
    });
  };
  const guardarEdicionGasto = async (e) => {
    e.preventDefault();
    setErrorEdicionGasto("");

    if (!edicionGastoData.descripcion.trim()) {
      setErrorEdicionGasto(
        "Escribe una descripción para el gasto."
      );
      return;
    }

    if (
      !edicionGastoData.monto ||
      Number(edicionGastoData.monto) <= 0
    ) {
      setErrorEdicionGasto(
        "El monto debe ser mayor que cero."
      );
      return;
    }

    if (!edicionGastoData.fecha_gasto) {
      setErrorEdicionGasto(
        "Selecciona la fecha del gasto."
      );
      return;
    }

    const token = localStorage.getItem("access");

    if (!token) {
      setErrorEdicionGasto(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      return;
    }

    try {
      setGuardandoEdicionGasto(true);

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/gastos/${gastoEditandoId}/`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            descripcion: edicionGastoData.descripcion.trim(),
            monto: edicionGastoData.monto,
            fecha_gasto: edicionGastoData.fecha_gasto,
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
            "No se pudo actualizar el gasto."
          )
        );
      }

      if (data.gasto) {
        const gastosActualizados = gastos.map((gasto) =>
          gasto.id === data.gasto.id
            ? data.gasto
            : gasto
        );

        setGastos(gastosActualizados);
        setTotalGastos(
          gastosActualizados
            .reduce(
              (total, gasto) =>
                total + Number(gasto.monto || 0),
              0
            )
            .toFixed(2)
        );

        setGastoSeleccionado((detalleActual) =>
          detalleActual?.id === data.gasto.id
            ? data.gasto
            : detalleActual
        );
      }

      setEdicionGastoAbierta(false);
      setGastoEditandoId(null);
      setErrorEdicionGasto("");
      setMensaje(
        data.mensaje || "Gasto actualizado correctamente."
      );

      await Promise.all([
        obtenerBalances(),
        obtenerResumenEconomico(),
      ]);
    } catch (errorEdicion) {
      setErrorEdicionGasto(
        errorEdicion.message ||
          "No se pudo actualizar el gasto."
      );
    } finally {
      setGuardandoEdicionGasto(false);
    }
  };

  const eliminarGasto = async (gasto) => {
    const confirmar = window.confirm(
      `¿Deseas eliminar el gasto "${gasto.descripcion}" por ${formatearMonto(
        gasto.monto
      )}? Esta acción no se puede deshacer.`
    );

    if (!confirmar) {
      return;
    }

    setMensaje("");
    setError("");
    setErrorGastos("");

    const token = localStorage.getItem("access");

    if (!token) {
      setError("Tu sesión ha expirado. Inicia sesión nuevamente.");
      return;
    }

    try {
      setEliminandoGastoId(gasto.id);

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/gastos/${gasto.id}/`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
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
            "No se pudo eliminar el gasto."
          )
        );
      }

      const gastosActualizados = gastos.filter(
        (gastoActual) => gastoActual.id !== gasto.id
      );

      setGastos(gastosActualizados);
      setTotalGastos(
        gastosActualizados
          .reduce(
            (total, gastoActual) =>
              total + Number(gastoActual.monto || 0),
            0
          )
          .toFixed(2)
      );

      if (gastoSeleccionado?.id === gasto.id) {
        cerrarDetalleGasto();
      }

      if (gastoEditandoId === gasto.id) {
        setEdicionGastoAbierta(false);
        setGastoEditandoId(null);
        setErrorEdicionGasto("");
      }

      setMensaje(
        data.mensaje || "Gasto eliminado correctamente."
      );

      await Promise.all([
        obtenerBalances(),
        obtenerResumenEconomico(),
      ]);
    } catch (errorEliminacion) {
      setError(
        errorEliminacion.message ||
          "No se pudo eliminar el gasto."
      );
    } finally {
      setEliminandoGastoId(null);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleGastoChange = (e) => {
    setGastoData({
      ...gastoData,
      [e.target.name]: e.target.value,
    });
  };

  const handlePagoChange = (e) => {
    setPagoData((datosActuales) => ({
      ...datosActuales,
      [e.target.name]: e.target.value,
    }));

    setMensajePago("");
    setErrorPago("");
  };

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

  const registrarPago = async (e) => {
    e.preventDefault();

    setMensajePago("");
    setErrorPago("");
    setMensaje("");
    setError("");

    if (!cuotaUsuarioActual || cuotaUsuarioSaldada) {
      setErrorPago("Tu cuota ya se encuentra saldada.");
      return;
    }

    if (!pagoData.monto || Number(pagoData.monto) <= 0) {
      setErrorPago("El monto del pago debe ser mayor que cero.");
      return;
    }

    if (
      Number(pagoData.monto) >
      saldoPendienteUsuario
    ) {
      setErrorPago(
        `El monto del pago no puede superar tu saldo pendiente de ${formatearMonto(
          saldoPendienteUsuario
        )}.`
      );
      return;
    }

    if (!pagoData.fecha_pago) {
      setErrorPago("Selecciona la fecha del pago.");
      return;
    }

    const token = localStorage.getItem("access");

    if (!token) {
      setErrorPago(
        "Tu sesión ha expirado. Inicia sesión nuevamente."
      );
      return;
    }

    try {
      setRegistrandoPago(true);

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/pagos/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            monto: pagoData.monto,
            fecha_pago: pagoData.fecha_pago,
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
            "No se pudo registrar el pago."
          )
        );
      }

      setPagoData({
        monto: "",
        fecha_pago: obtenerFechaActual(),
      });

      setMensajePago(
        data.mensaje || "Pago propio registrado correctamente."
      );

      await Promise.all([
        obtenerBalances(),
        obtenerResumenEconomico(),
        obtenerPagos(),
      ]);
    } catch (errorRegistroPago) {
      setErrorPago(
        errorRegistroPago.message ||
          "No se pudo registrar el pago."
      );
    } finally {
      setRegistrandoPago(false);
    }
  };

  const guardarCambios = async (e) => {
    e.preventDefault();

    setMensaje("");
    setError("");

    if (!formData.nombre.trim()) {
      setError("Escribe un nombre para la actividad.");
      return;
    }

    if (!formData.fecha_inicio) {
      setError("Selecciona la fecha y hora de inicio.");
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
      setError("Las fechas ingresadas no son válidas.");
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
      setError("Tu sesión ha expirado. Inicia sesión nuevamente.");
      return;
    }

    try {
      setGuardando(true);

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/`,
        {
          method: "PATCH",
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
            "No se pudo actualizar la actividad."
          )
        );
      }

      setGrupo(data);
      setTotalGastos(data.total_gastos || totalGastos);

      setFormData({
        nombre: data.nombre || "",
        descripcion: data.descripcion || "",
        fecha_inicio: convertirFechaISOAInput(
          data.fecha_inicio
        ),
        fecha_fin: convertirFechaISOAInput(
          data.fecha_fin
        ),
      });

      setModoEdicion(false);
      setMensaje("Actividad actualizada correctamente.");
    } catch (errorActualizacion) {
      setError(
        errorActualizacion.message ||
          "No se pudo actualizar la actividad."
      );
    } finally {
      setGuardando(false);
    }
  };

  const cancelarEdicion = () => {
    setFormData({
      nombre: grupo?.nombre || "",
      descripcion: grupo?.descripcion || "",
      fecha_inicio: convertirFechaISOAInput(
        grupo?.fecha_inicio
      ),
      fecha_fin: convertirFechaISOAInput(
        grupo?.fecha_fin
      ),
    });

    setModoEdicion(false);
    setMensaje("");
    setError("");
  };

  const eliminarGrupo = async () => {
    const confirmar = window.confirm(
      "¿Estás seguro de que deseas eliminar este grupo? Esta acción no se puede deshacer."
    );

    if (!confirmar) {
      return;
    }

    setMensaje("");
    setError("");

    const token = localStorage.getItem("access");

    if (!token) {
      setError("Tu sesión ha expirado. Inicia sesión nuevamente.");
      return;
    }

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("No se pudo eliminar el grupo.");
      }

      navigate("/dashboard");
    } catch {
      setError("No se pudo eliminar el grupo. Intenta nuevamente.");
    }
  };
  const registrarGasto = async (e) => {
    e.preventDefault();

    setMensaje("");
    setError("");

    if (!gastoData.descripcion.trim()) {
      setError("Escribe una descripción para el gasto.");
      return;
    }

    if (!gastoData.monto || Number(gastoData.monto) <= 0) {
      setError("El monto debe ser mayor que cero.");
      return;
    }

    if (!gastoData.fecha_gasto) {
      setError("Selecciona la fecha del gasto.");
      return;
    }

    const token = localStorage.getItem("access");

    if (!token) {
      setError("Tu sesión ha expirado. Inicia sesión nuevamente.");
      return;
    }

    try {
      setRegistrandoGasto(true);

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/gastos/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            descripcion: gastoData.descripcion.trim(),
            monto: gastoData.monto,
            fecha_gasto: gastoData.fecha_gasto,
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
            "No se pudo registrar el gasto."
          )
        );
      }

      setGastoData({
        descripcion: "",
        monto: "",
        fecha_gasto: obtenerFechaActual(),
      });

      if (data.gasto) {
        setGastos((gastosActuales) => [
          data.gasto,
          ...gastosActuales,
        ]);
      }

      setTotalGastos(
        data.total_gastos ||
          (
            Number(totalGastos) +
            Number(data.gasto?.monto || 0)
          ).toFixed(2)
      );

      setErrorGastos("");
      setMensaje(
        data.mensaje || "Gasto común registrado correctamente."
      );

      await Promise.all([
        obtenerBalances(),
        obtenerResumenEconomico(),
      ]);
    } catch (errorGasto) {
      setError(
        errorGasto.message || "No se pudo registrar el gasto."
      );
    } finally {
      setRegistrandoGasto(false);
    }
  };

  const iniciarEdicionParticipante = (participante) => {
    setParticipanteEditando(participante.id);
    setNotaTemporal(
      notasParticipantes[participante.id] || ""
    );
    setMensaje("");
    setError("");
  };

  const cancelarEdicionParticipante = () => {
    setParticipanteEditando(null);
    setNotaTemporal("");
    setMensaje("");
    setError("");
  };

  const guardarEdicionParticipante = (participanteId) => {
    setNotasParticipantes({
      ...notasParticipantes,
      [participanteId]: notaTemporal.trim(),
    });

    setParticipanteEditando(null);
    setNotaTemporal("");

    setMensaje(
      "Información del participante actualizada correctamente."
    );
  };

  const agregarParticipante = async () => {
    setMensaje("");
    setError("");

    if (!usuarioSeleccionado) {
      setError("Selecciona un usuario para agregarlo al grupo.");
      return;
    }

    const token = localStorage.getItem("access");

    if (!token) {
      setError("Tu sesión ha expirado. Inicia sesión nuevamente.");
      return;
    }

    try {
      setAgregandoParticipante(true);

      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/participantes/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            usuario_id: usuarioSeleccionado,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "No se pudo agregar el participante."
        );
      }

      setGrupo(data.grupo);
      setTotalGastos(
        data.grupo?.total_gastos || totalGastos
      );
      setUsuarioSeleccionado("");
      setMensaje(
        data.mensaje || "Participante agregado correctamente."
      );

      await obtenerMembresias();
      await Promise.all([
        obtenerBalances(),
        obtenerResumenEconomico(),
      ]);
    } catch (errorParticipante) {
      setError(
        errorParticipante.message ||
          "No se pudo agregar el participante."
      );
    } finally {
      setAgregandoParticipante(false);
    }
  };

  const eliminarParticipante = async (participanteId) => {
    const confirmar = window.confirm(
      "¿Deseas retirar este participante de la actividad? Su historial se conservará."
    );

    if (!confirmar) {
      return;
    }

    setMensaje("");
    setError("");

    const token = localStorage.getItem("access");

    if (!token) {
      setError("Tu sesión ha expirado. Inicia sesión nuevamente.");
      return;
    }

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/grupos/${id}/participantes/${participanteId}/`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "No se pudo eliminar el participante."
        );
      }

      setGrupo(data.grupo);
      setTotalGastos(
        data.grupo?.total_gastos || totalGastos
      );

      setNotasParticipantes((notasActuales) => {
        const nuevasNotas = { ...notasActuales };
        delete nuevasNotas[participanteId];
        return nuevasNotas;
      });

      setParticipanteEditando(null);
      setNotaTemporal("");
      setMensaje(
        data.mensaje || "Participante retirado correctamente."
      );

      await obtenerMembresias();
      await Promise.all([
        obtenerBalances(),
        obtenerResumenEconomico(),
      ]);
    } catch (errorParticipante) {
      setError(
        errorParticipante.message ||
          "No se pudo eliminar el participante."
      );
    }
  };

  const irARegistrarPago = () => {
    document
      .getElementById("registrar-pago")
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
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
          {puedeRegistrarAporte && (
            <button
              type="button"
              className="btn btn-primary w-100 mb-3"
              onClick={irARegistrarPago}
            >
              Registrar pago
            </button>
          )}

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

          <strong>Detalle de la actividad</strong>
        </div>

        {cargando ? (
          <div className="create-group-card">
            <h4>Cargando detalle...</h4>
            <p>Estamos consultando la información del grupo.</p>
          </div>
        ) : error && !grupo ? (
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
              <div className="d-flex align-items-center flex-wrap gap-3">
                <h1 className="mb-0">{grupo.nombre}</h1>

                <span
                  className={`badge ${
                    obtenerConfiguracionEstadoActividad(
                      grupo.estado
                    ).clase
                  }`}
                >
                  {
                    obtenerConfiguracionEstadoActividad(
                      grupo.estado
                    ).texto
                  }
                </span>

                <span
                  className={`badge ${
                    esCreador
                      ? "bg-primary"
                      : "bg-dark"
                  }`}
                >
                  {esCreador
                    ? "Creador"
                    : "Participante"}
                </span>
              </div>

              <p className="mt-2">
                {esCreador
                  ? "Revisa y administra la información general de la actividad."
                  : actividadCerrada
                    ? "Consulta la información histórica de esta actividad."
                    : actividadProgramada
                      ? "Consulta la actividad; los gastos se habilitarán cuando inicie."
                      : "Consulta la actividad y registra gastos comunes o pagos propios."}
              </p>
            </header>

            <section
              className="create-group-grid"
              style={{
                gridTemplateColumns: "minmax(0, 1fr)",
                width: "100%",
              }}
            >
              <div className="create-group-card">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h4 className="mb-0">
                    Información de la actividad
                  </h4>

                  {!modoEdicion && esCreador && (
                    <div className="d-flex gap-2">
                      <button
                        type="button"
                        className="btn btn-outline-primary"
                        onClick={() => {
                          setModoEdicion(true);
                          setMensaje("");
                          setError("");
                        }}
                      >
                        Editar grupo
                      </button>

                      <button
                        type="button"
                        className="btn btn-outline-danger"
                        onClick={eliminarGrupo}
                      >
                        Eliminar grupo
                      </button>
                    </div>
                  )}
                </div>

                {mensaje && (
                  <div
                    className="alert alert-success"
                    role="alert"
                  >
                    {mensaje}
                  </div>
                )}

                {error && (
                  <div
                    className="alert alert-danger"
                    role="alert"
                  >
                    {error}
                  </div>
                )}

                {actividadCerrada && (
                  <div
                    className="alert alert-warning"
                    role="alert"
                  >
                    Esta actividad está cerrada. Puedes consultar
                    su información, pero no registrar gastos,
                    pagos ni modificar participantes.
                  </div>
                )}

                {actividadProgramada && (
                  <div
                    className="alert alert-info"
                    role="alert"
                  >
                    Esta actividad todavía no ha comenzado.
                    El registro de gastos comunes se habilitará
                    automáticamente cuando llegue la fecha de inicio.
                  </div>
                )}

                {!esCreador && !actividadCerrada && (
                  <div
                    className="alert alert-info"
                    role="alert"
                  >
                    Participas activamente en esta actividad.
                    Puedes consultar la información, registrar
                    gastos comunes cuando esté activa y registrar
                    únicamente tus propios pagos.
                  </div>
                )}

                {modoEdicion ? (
                  <form onSubmit={guardarCambios}>
                    <div className="mt-4">
                      <label className="form-label">
                        Nombre de la actividad
                      </label>

                      <input
                        type="text"
                        name="nombre"
                        className="form-control"
                        value={formData.nombre}
                        onChange={handleChange}
                        required
                      />
                    </div>

                    <div className="mt-3">
                      <label className="form-label">
                        Descripción
                      </label>

                      <textarea
                        name="descripcion"
                        className="form-control"
                        rows="5"
                        value={formData.descripcion}
                        onChange={handleChange}
                      />
                    </div>

                    <div className="row mt-1">
                      <div className="col-md-6 mt-3">
                        <label className="form-label">
                          Fecha y hora de inicio
                        </label>

                        <input
                          type="datetime-local"
                          name="fecha_inicio"
                          className="form-control"
                          value={formData.fecha_inicio}
                          onChange={handleChange}
                          disabled={guardando}
                          required
                        />
                      </div>

                      <div className="col-md-6 mt-3">
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
                          disabled={guardando}
                          required
                        />
                      </div>
                    </div>

                    <div
                      className="alert alert-light border mt-3 mb-0"
                      role="alert"
                    >
                      El estado se actualizará automáticamente
                      según estas fechas.
                    </div>

                    <div className="create-group-footer mt-4">
                      <small>
                        ⓘ Los cambios se guardarán en la base de
                        datos.
                      </small>

                      <div className="d-flex gap-2">
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          onClick={cancelarEdicion}
                          disabled={guardando}
                        >
                          Cancelar
                        </button>

                        <button
                          type="submit"
                          className="btn btn-primary"
                          disabled={guardando}
                        >
                          {guardando
                            ? "Guardando..."
                            : "Guardar cambios"}
                        </button>
                      </div>
                    </div>
                  </form>
                ) : (
                  <>
                    <div className="mt-4">
                      <label className="form-label">
                        Nombre de la actividad
                      </label>

                      <div className="form-control bg-light">
                        {grupo.nombre}
                      </div>
                    </div>

                    <div className="mt-3">
                      <label className="form-label">
                        Descripción
                      </label>

                      <div
                        className="form-control bg-light"
                        style={{ minHeight: "110px" }}
                      >
                        {grupo.descripcion || "Sin descripción"}
                      </div>
                    </div>

                    <div className="row mt-1">
                      <div className="col-md-6 mt-3">
                        <label className="form-label">
                          Inicio de la actividad
                        </label>

                        <div className="form-control bg-light">
                          {formatearFechaHora(
                            grupo.fecha_inicio
                          )}
                        </div>
                      </div>

                      <div className="col-md-6 mt-3">
                        <label className="form-label">
                          Finalización de la actividad
                        </label>

                        <div className="form-control bg-light">
                          {formatearFechaHora(
                            grupo.fecha_fin
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3">
                      <label className="form-label">
                        Estado de la actividad
                      </label>

                      <div className="border rounded p-3 bg-light">
                        <div className="d-flex justify-content-between align-items-center gap-3">
                          <span>
                            {
                              obtenerConfiguracionEstadoActividad(
                                grupo.estado
                              ).descripcion
                            }
                          </span>

                          <span
                            className={`badge ${
                              obtenerConfiguracionEstadoActividad(
                                grupo.estado
                              ).clase
                            }`}
                          >
                            {
                              obtenerConfiguracionEstadoActividad(
                                grupo.estado
                              ).texto
                            }
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3">
                      <label className="form-label">
                        Creado por
                      </label>

                      <div className="form-control bg-light">
                        {grupo.creador_username || username}
                      </div>
                    </div>

                    <div className="mt-3">
                      <label className="form-label">
                        Fecha de creación
                      </label>

                      <div className="form-control bg-light">
                        {grupo.fecha_creacion
                          ? new Date(
                              grupo.fecha_creacion
                            ).toLocaleDateString()
                          : "Sin fecha"}
                      </div>
                    </div>

                    <div className="mt-4">
                      <div className="d-flex justify-content-between align-items-center">
                        <div>
                          <h5 className="mb-1">
                            Participantes del grupo
                          </h5>

                          <small className="text-muted">
                            Total de participantes:{" "}
                            {grupo.participantes?.length || 0}
                          </small>
                        </div>
                      </div>

                      {grupo.participantes &&
                      grupo.participantes.length > 0 ? (
                        <div className="mt-3">
                          {grupo.participantes.map(
                            (participante) => (
                              <div
                                key={participante.id}
                                className="border rounded p-3 mb-2"
                              >
                                <div className="d-flex justify-content-between align-items-start">
                                  <div>
                                    <strong>
                                      {
                                        participante.nombre_completo
                                      }
                                    </strong>

                                    <br />

                                    <small className="text-muted">
                                      Usuario: @
                                      {participante.username}
                                    </small>

                                    <br />

                                    <small className="text-muted">
                                      Correo:{" "}
                                      {participante.email ||
                                        "No registrado"}
                                    </small>

                                    {notasParticipantes[
                                      participante.id
                                    ] && (
                                      <>
                                        <br />

                                        <small className="text-muted">
                                          Nota/Rol:{" "}
                                          {
                                            notasParticipantes[
                                              participante.id
                                            ]
                                          }
                                        </small>
                                      </>
                                    )}
                                  </div>

                                  <div className="d-flex gap-2 align-items-center">
                                    <span className="badge bg-light text-dark">
                                      {participante.username ===
                                      grupo.creador_username
                                        ? "Creador"
                                        : "Participante"}
                                    </span>

                                    {esCreador &&
                                      !actividadCerrada && (
                                        <>
                                          <button
                                            type="button"
                                            className="btn btn-outline-primary btn-sm"
                                            onClick={() =>
                                              iniciarEdicionParticipante(
                                                participante
                                              )
                                            }
                                          >
                                            Editar
                                          </button>

                                          {participante.username !==
                                            grupo.creador_username && (
                                            <button
                                              type="button"
                                              className="btn btn-outline-danger btn-sm"
                                              onClick={() =>
                                                eliminarParticipante(
                                                  participante.id
                                                )
                                              }
                                            >
                                              Retirar
                                            </button>
                                          )}
                                        </>
                                      )}
                                  </div>
                                </div>

                                {esCreador &&
                                  !actividadCerrada &&
                                  participanteEditando ===
                                    participante.id && (
                                  <div className="mt-3">
                                    <label className="form-label">
                                      Nota o rol del participante
                                    </label>

                                    <input
                                      type="text"
                                      className="form-control"
                                      placeholder="Ej: Responsable de pagos, amigo, compañero..."
                                      value={notaTemporal}
                                      onChange={(e) =>
                                        setNotaTemporal(
                                          e.target.value
                                        )
                                      }
                                    />

                                    <div className="d-flex gap-2 mt-3">
                                      <button
                                        type="button"
                                        className="btn btn-outline-secondary btn-sm"
                                        onClick={
                                          cancelarEdicionParticipante
                                        }
                                      >
                                        Cancelar
                                      </button>

                                      <button
                                        type="button"
                                        className="btn btn-primary btn-sm"
                                        onClick={() =>
                                          guardarEdicionParticipante(
                                            participante.id
                                          )
                                        }
                                      >
                                        Guardar
                                      </button>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )
                          )}
                        </div>
                      ) : (
                        <div className="empty-groups-card mt-3">
                          <h5>
                            No hay participantes todavía
                          </h5>

                          <p>
                            Agrega usuarios registrados para que
                            formen parte de este grupo.
                          </p>
                        </div>
                      )}

                      {esCreador && !actividadCerrada && (
                        <div className="mt-4">
                          <label className="form-label">
                            Agregar participante
                          </label>

                          <div className="d-flex gap-2">
                            <select
                              className="form-control"
                              value={usuarioSeleccionado}
                              onChange={(e) =>
                                setUsuarioSeleccionado(
                                  e.target.value
                                )
                              }
                            >
                              <option value="">
                                Selecciona un usuario registrado
                              </option>

                              {usuarios
                                .filter(
                                  (usuario) =>
                                    !grupo.participantes?.some(
                                      (participante) =>
                                        participante.id ===
                                        usuario.id
                                    )
                                )
                                .map((usuario) => (
                                  <option
                                    key={usuario.id}
                                    value={usuario.id}
                                  >
                                    {usuario.nombre_completo} (@
                                    {usuario.username})
                                  </option>
                                ))}
                            </select>

                            <button
                              type="button"
                              className="btn btn-primary"
                              onClick={agregarParticipante}
                              disabled={agregandoParticipante}
                            >
                              {agregandoParticipante
                                ? "Agregando..."
                                : "Agregar"}
                            </button>
                          </div>
                        </div>
                      )}

                      <div className="mt-5 pt-4 border-top">
                        <div className="d-flex justify-content-between align-items-center gap-3">
                          <div>
                            <h5 className="mb-1">
                              Historial de membresías
                            </h5>

                            <small className="text-muted">
                              Consulta los ingresos, retiros y
                              reingresos de los participantes.
                            </small>
                          </div>

                          <button
                            type="button"
                            className="btn btn-outline-primary btn-sm"
                            onClick={obtenerMembresias}
                            disabled={cargandoMembresias}
                          >
                            {cargandoMembresias
                              ? "Actualizando..."
                              : "Actualizar"}
                          </button>
                        </div>

                        <div className="row g-3 mt-1">
                          <div className="col-md-4">
                            <div className="border rounded p-3 h-100 bg-light">
                              <small className="text-muted d-block">
                                Registros históricos
                              </small>

                              <strong className="fs-5">
                                {
                                  resumenMembresias.total_membresias
                                }
                              </strong>
                            </div>
                          </div>

                          <div className="col-md-4">
                            <div className="border rounded p-3 h-100 bg-light">
                              <small className="text-muted d-block">
                                Membresías activas
                              </small>

                              <strong className="fs-5">
                                {resumenMembresias.total_activas}
                              </strong>
                            </div>
                          </div>

                          <div className="col-md-4">
                            <div className="border rounded p-3 h-100 bg-light">
                              <small className="text-muted d-block">
                                Membresías retiradas
                              </small>

                              <strong className="fs-5">
                                {
                                  resumenMembresias.total_retiradas
                                }
                              </strong>
                            </div>
                          </div>
                        </div>

                        {cargandoMembresias ? (
                          <div
                            className="alert alert-light border mt-3"
                            role="alert"
                          >
                            Cargando historial de membresías...
                          </div>
                        ) : errorMembresias ? (
                          <div
                            className="alert alert-danger mt-3"
                            role="alert"
                          >
                            {errorMembresias}
                          </div>
                        ) : membresias.length === 0 ? (
                          <div className="alert alert-light border mt-3 mb-0">
                            No hay membresías registradas para
                            esta actividad.
                          </div>
                        ) : (
                          <div className="d-flex flex-column gap-3 mt-3">
                            {membresias.map((membresia) => (
                              <div
                                key={membresia.id}
                                className="border rounded p-3"
                              >
                                <div className="d-flex justify-content-between align-items-start gap-3">
                                  <div>
                                    <strong>
                                      {membresia.usuario
                                        ?.nombre_completo ||
                                        membresia.usuario
                                          ?.username ||
                                        "Usuario"}
                                    </strong>

                                    {membresia.usuario?.username && (
                                      <small className="text-muted d-block">
                                        @
                                        {
                                          membresia.usuario
                                            .username
                                        }
                                      </small>
                                    )}
                                  </div>

                                  <span
                                    className={`badge ${
                                      membresia.activo
                                        ? "bg-success"
                                        : "bg-secondary"
                                    }`}
                                  >
                                    {membresia.activo
                                      ? "Activo"
                                      : "Retirado"}
                                  </span>
                                </div>

                                <div className="row g-2 mt-2">
                                  <div className="col-md-6">
                                    <div className="bg-light border rounded p-2 h-100">
                                      <small className="text-muted d-block">
                                        Fecha de ingreso
                                      </small>

                                      <strong>
                                        {formatearFechaHora(
                                          membresia.fecha_ingreso
                                        )}
                                      </strong>
                                    </div>
                                  </div>

                                  <div className="col-md-6">
                                    <div className="bg-light border rounded p-2 h-100">
                                      <small className="text-muted d-block">
                                        Fecha de salida
                                      </small>

                                      <strong>
                                        {membresia.fecha_salida
                                          ? formatearFechaHora(
                                              membresia.fecha_salida
                                            )
                                          : "Continúa en la actividad"}
                                      </strong>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="mt-5 pt-4 border-top">
                        <div className="d-flex justify-content-between align-items-center gap-3">
                          <div>
                            <h5 className="mb-1">
                              Resumen económico
                            </h5>

                            <small className="text-muted">
                              Consulta el total común, los aportes y
                              la cuota acumulada de cada integrante.
                            </small>
                          </div>

                          <button
                            type="button"
                            className="btn btn-outline-primary btn-sm"
                            onClick={obtenerResumenEconomico}
                            disabled={cargandoResumenEconomico}
                          >
                            {cargandoResumenEconomico
                              ? "Actualizando..."
                              : "Actualizar"}
                          </button>
                        </div>

                        {cargandoResumenEconomico ? (
                          <div
                            className="alert alert-light border mt-3"
                            role="alert"
                          >
                            Cargando resumen económico...
                          </div>
                        ) : errorResumenEconomico ? (
                          <div
                            className="alert alert-danger mt-3"
                            role="alert"
                          >
                            {errorResumenEconomico}
                          </div>
                        ) : resumenEconomico ? (
                          <>
                            <div className="row g-3 mt-1">
                              <div className="col-md-3">
                                <div className="border rounded p-3 h-100 bg-light">
                                  <small className="text-muted d-block">
                                    Total de gastos
                                  </small>

                                  <strong className="fs-5">
                                    {formatearMonto(
                                      resumenEconomico.total_gastos
                                    )}
                                  </strong>
                                </div>
                              </div>

                              <div className="col-md-3">
                                <div className="border rounded p-3 h-100 bg-light">
                                  <small className="text-muted d-block">
                                    Gastos registrados
                                  </small>

                                  <strong className="fs-5">
                                    {resumenEconomico.cantidad_gastos ||
                                      0}
                                  </strong>
                                </div>
                              </div>

                              <div className="col-md-3">
                                <div className="border rounded p-3 h-100 bg-light">
                                  <small className="text-muted d-block">
                                    Total aportado
                                  </small>

                                  <strong className="fs-5">
                                    {formatearMonto(
                                      resumenEconomico.total_aportado
                                    )}
                                  </strong>
                                </div>
                              </div>

                              <div className="col-md-3">
                                <div className="border rounded p-3 h-100 bg-light">
                                  <small className="text-muted d-block">
                                    Total pendiente
                                  </small>

                                  <strong className="fs-5">
                                    {formatearMonto(
                                      resumenEconomico.total_pendiente
                                    )}
                                  </strong>
                                </div>
                              </div>
                            </div>

                            <div className="d-flex justify-content-between align-items-center mt-4">
                              <div>
                                <h6 className="mb-1">
                                  Cuotas individuales
                                </h6>

                                <small className="text-muted">
                                  Las cuotas se calculan desde las
                                  divisiones históricas guardadas.
                                </small>
                              </div>

                              <span className="badge bg-light text-dark border">
                                {cuotasEconomicas.length}
                              </span>
                            </div>

                            {cuotasEconomicas.length > 0 ? (
                              <div className="d-flex flex-column gap-3 mt-3">
                                {cuotasEconomicas.map((cuota) => {
                                  const estaSaldado =
                                    cuota.estado === "saldado";

                                  return (
                                    <div
                                      key={cuota.participante.id}
                                      className="border rounded p-3"
                                    >
                                      <div className="d-flex justify-content-between align-items-start gap-3">
                                        <div>
                                          <strong>
                                            {cuota.participante
                                              .nombre_completo ||
                                              cuota.participante
                                                .username}
                                          </strong>

                                          <small className="text-muted d-block">
                                            @{cuota.participante.username}
                                          </small>

                                          <span
                                            className={`badge mt-2 ${
                                              cuota.activo
                                                ? "bg-success"
                                                : "bg-secondary"
                                            }`}
                                          >
                                            {cuota.activo
                                              ? "Miembro activo"
                                              : "Participante histórico"}
                                          </span>
                                        </div>

                                        <div className="text-end">
                                          <span
                                            className={`badge ${
                                              estaSaldado
                                                ? "bg-success"
                                                : "bg-warning text-dark"
                                            }`}
                                          >
                                            {estaSaldado
                                              ? "Saldado"
                                              : "Pendiente"}
                                          </span>

                                          <strong className="fs-5 d-block mt-2">
                                            {formatearMonto(
                                              cuota.saldo_pendiente
                                            )}
                                          </strong>

                                          <small className="text-muted">
                                            Saldo pendiente
                                          </small>
                                        </div>
                                      </div>

                                      <div className="row g-2 mt-2">
                                        <div className="col-md-6">
                                          <div className="bg-light border rounded p-2 h-100">
                                            <small className="text-muted d-block">
                                              Cuota acumulada
                                            </small>

                                            <strong>
                                              {formatearMonto(
                                                cuota.cuota_total
                                              )}
                                            </strong>
                                          </div>
                                        </div>

                                        <div className="col-md-6">
                                          <div className="bg-light border rounded p-2 h-100">
                                            <small className="text-muted d-block">
                                              Total aportado
                                            </small>

                                            <strong>
                                              {formatearMonto(
                                                cuota.total_aportado
                                              )}
                                            </strong>
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <div className="alert alert-light border mt-3 mb-0">
                                Todavía no existen cuotas económicas
                                para esta actividad.
                              </div>
                            )}

                            <div
                              className="alert alert-light border mt-3 mb-0"
                              role="alert"
                            >
                              La suma de las cuotas corresponde a{" "}
                              <strong>
                                {formatearMonto(
                                  resumenEconomico.total_cuotas
                                )}
                              </strong>
                              .
                            </div>
                          </>
                        ) : (
                          <div className="alert alert-light border mt-3 mb-0">
                            No hay información económica disponible.
                          </div>
                        )}
                      </div>

                      <div className="mt-5 pt-4 border-top">
                        <div className="d-flex justify-content-between align-items-center gap-3">
                          <div>
                            <h5 className="mb-1">
                              Balances individuales
                            </h5>

                            <small className="text-muted">
                              Revisa cuánto pagó, cuánto le correspondía
                              y el saldo actual de cada participante.
                            </small>
                          </div>

                          <button
                            type="button"
                            className="btn btn-outline-primary btn-sm"
                            onClick={obtenerBalances}
                            disabled={cargandoBalances}
                          >
                            {cargandoBalances
                              ? "Actualizando..."
                              : "Actualizar"}
                          </button>
                        </div>

                        {cargandoBalances ? (
                          <div
                            className="alert alert-light border mt-3"
                            role="alert"
                          >
                            Cargando balances del grupo...
                          </div>
                        ) : errorBalances ? (
                          <div
                            className="alert alert-danger mt-3"
                            role="alert"
                          >
                            {errorBalances}
                          </div>
                        ) : (
                          <>
                            {resumenBalances && (
                              <div className="row g-3 mt-1">
                                <div className="col-md-4">
                                  <div className="border rounded p-3 h-100 bg-light">
                                    <small className="text-muted d-block">
                                      Total común
                                    </small>

                                    <strong className="fs-5">
                                      {formatearMonto(
                                        totalGastos
                                      )}
                                    </strong>
                                  </div>
                                </div>

                                <div className="col-md-4">
                                  <div className="border rounded p-3 h-100 bg-light">
                                    <small className="text-muted d-block">
                                      Total repartido
                                    </small>

                                    <strong className="fs-5">
                                      {formatearMonto(
                                        resumenBalances.total_correspondiente
                                      )}
                                    </strong>
                                  </div>
                                </div>

                                <div className="col-md-4">
                                  <div className="border rounded p-3 h-100 bg-light">
                                    <small className="text-muted d-block">
                                      Balance general
                                    </small>

                                    <strong className="fs-5">
                                      {formatearBalance(
                                        resumenBalances.balance_general
                                      )}
                                    </strong>
                                  </div>
                                </div>
                              </div>
                            )}

                            {balances.length > 0 ? (
                              <div className="d-flex flex-column gap-3 mt-3">
                                {balances.map((balance) => {
                                  const estadoClase =
                                    balance.estado === "a_favor"
                                      ? "bg-success"
                                      : balance.estado === "debe"
                                        ? "bg-danger"
                                        : "bg-secondary";

                                  return (
                                    <div
                                      key={balance.participante.id}
                                      className="border rounded p-3"
                                    >
                                      <div className="d-flex justify-content-between align-items-start gap-3">
                                        <div>
                                          <strong>
                                            {balance.participante
                                              .nombre_completo ||
                                              balance.participante
                                                .username}
                                          </strong>

                                          <small className="text-muted d-block">
                                            @{balance.participante.username}
                                          </small>
                                        </div>

                                        <div className="text-end">
                                          <span
                                            className={`badge ${estadoClase}`}
                                          >
                                            {obtenerTextoEstadoBalance(
                                              balance.estado
                                            )}
                                          </span>

                                          <strong className="fs-5 d-block mt-2">
                                            {formatearBalance(
                                              balance.balance
                                            )}
                                          </strong>
                                        </div>
                                      </div>

                                      <div className="row g-2 mt-2">
                                        <div className="col-md-6">
                                          <div className="bg-light border rounded p-2">
                                            <small className="text-muted d-block">
                                              Pagos realizados
                                            </small>

                                            <strong>
                                              {formatearMonto(
                                                balance.pagos_realizados
                                              )}
                                            </strong>
                                          </div>
                                        </div>

                                        <div className="col-md-6">
                                          <div className="bg-light border rounded p-2">
                                            <small className="text-muted d-block">
                                              Le correspondía
                                            </small>

                                            <strong>
                                              {formatearMonto(
                                                balance.total_correspondiente
                                              )}
                                            </strong>
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <div className="alert alert-light border mt-3 mb-0">
                                No hay balances disponibles para este grupo.
                              </div>
                            )}
                          </>
                        )}
                      </div>

                      {puedeRegistrarPagos && (
                        <div
                          id="registrar-pago"
                          className="mt-5 pt-4 border-top"
                        >
                          <div>
                            <h5 className="mb-1">
                              Registrar aporte propio
                            </h5>

                            <small className="text-muted">
                              Registra un aporte realizado por ti
                              para cubrir tu cuota de la actividad.
                            </small>
                          </div>

                          {cargandoResumenEconomico ? (
                            <div
                              className="alert alert-light border mt-3"
                              role="alert"
                            >
                              Consultando tu saldo pendiente...
                            </div>
                          ) : errorResumenEconomico ? (
                            <div
                              className="alert alert-danger mt-3"
                              role="alert"
                            >
                              No fue posible consultar tu saldo
                              pendiente. Actualiza el resumen
                              económico e inténtalo nuevamente.
                            </div>
                          ) : cuotaUsuarioActual ? (
                            <div className="row g-3 mt-1">
                              <div className="col-md-4">
                                <div className="border rounded p-3 h-100 bg-light">
                                  <small className="text-muted d-block">
                                    Tu cuota acumulada
                                  </small>

                                  <strong className="fs-5">
                                    {formatearMonto(
                                      cuotaUsuarioActual.cuota_total
                                    )}
                                  </strong>
                                </div>
                              </div>

                              <div className="col-md-4">
                                <div className="border rounded p-3 h-100 bg-light">
                                  <small className="text-muted d-block">
                                    Total que aportaste
                                  </small>

                                  <strong className="fs-5">
                                    {formatearMonto(
                                      cuotaUsuarioActual.total_aportado
                                    )}
                                  </strong>
                                </div>
                              </div>

                              <div className="col-md-4">
                                <div className="border rounded p-3 h-100 bg-light">
                                  <small className="text-muted d-block">
                                    Saldo disponible para pagar
                                  </small>

                                  <strong className="fs-5">
                                    {formatearMonto(
                                      cuotaUsuarioActual.saldo_pendiente
                                    )}
                                  </strong>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div
                              className="alert alert-warning mt-3"
                              role="alert"
                            >
                              Todavía no tienes una cuota asignada
                              en esta actividad.
                            </div>
                          )}

                          {!cargandoResumenEconomico &&
                            cuotaUsuarioActual &&
                            cuotaUsuarioSaldada && (
                              <div
                                className="alert alert-success mt-3"
                                role="alert"
                              >
                                Tu cuota ya se encuentra saldada.
                                No necesitas registrar más aportes.
                              </div>
                            )}

                          {!cargandoResumenEconomico &&
                            puedeRegistrarAporte && (
                              <div
                                className="alert alert-info mt-3"
                                role="alert"
                              >
                                Puedes registrar como máximo{" "}
                                <strong>
                                  {formatearMonto(
                                    saldoPendienteUsuario
                                  )}
                                </strong>
                                .
                              </div>
                            )}

                          {mensajePago && (
                            <div
                              className="alert alert-success mt-3"
                              role="alert"
                            >
                              {mensajePago}
                            </div>
                          )}

                          {errorPago && (
                            <div
                              className="alert alert-danger mt-3"
                              role="alert"
                            >
                              {errorPago}
                            </div>
                          )}

                          <form
                            onSubmit={registrarPago}
                            className="mt-3"
                          >
                            <div className="row">
                              <div className="col-md-6 mb-3">
                                <label className="form-label">
                                  Aporte registrado por
                                </label>

                                <div className="form-control bg-light">
                                  {usuarioActual?.nombre_completo ||
                                    username}{" "}
                                  (@{username})
                                </div>

                                <small className="text-muted">
                                  El aporte se registrará
                                  automáticamente a tu nombre.
                                </small>
                              </div>

                              <div className="col-md-6 mb-3">
                                <label className="form-label">
                                  Monto del aporte
                                </label>

                                <input
                                  type="number"
                                  name="monto"
                                  className="form-control"
                                  placeholder="0.00"
                                  min="0.01"
                                  max={
                                    puedeRegistrarAporte
                                      ? cuotaUsuarioActual.saldo_pendiente
                                      : undefined
                                  }
                                  step="0.01"
                                  value={pagoData.monto}
                                  onChange={handlePagoChange}
                                  disabled={
                                    registrandoPago ||
                                    !puedeRegistrarAporte
                                  }
                                  required
                                />
                              </div>

                              <div className="col-md-6 mb-3">
                                <label className="form-label">
                                  Fecha del pago
                                </label>

                                <input
                                  type="date"
                                  name="fecha_pago"
                                  className="form-control"
                                  value={pagoData.fecha_pago}
                                  onChange={handlePagoChange}
                                  disabled={
                                    registrandoPago ||
                                    !puedeRegistrarAporte
                                  }
                                  required
                                />
                              </div>
                            </div>

                            <div className="d-flex justify-content-between align-items-center gap-3 mt-2">
                              <small className="text-muted">
                                Cada participante registra únicamente
                                sus propios aportes.
                              </small>

                              <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={
                                  registrandoPago ||
                                  !puedeRegistrarAporte
                                }
                              >
                                {registrandoPago
                                  ? "Registrando aporte..."
                                  : "Registrar mi aporte"}
                              </button>
                            </div>
                          </form>
                        </div>
                      )}

                      <div className="mt-5 pt-4 border-top">
                        <div className="d-flex justify-content-between align-items-center gap-3">
                          <div>
                            <h5 className="mb-1">
                              Historial de pagos
                            </h5>

                            <small className="text-muted">
                              Consulta los aportes registrados en
                              esta actividad, del más reciente al
                              más antiguo.
                            </small>
                          </div>

                          <button
                            type="button"
                            className="btn btn-outline-primary btn-sm"
                            onClick={obtenerPagos}
                            disabled={cargandoPagos}
                          >
                            {cargandoPagos
                              ? "Actualizando..."
                              : "Actualizar"}
                          </button>
                        </div>

                        {cargandoPagos ? (
                          <div
                            className="alert alert-light border mt-3"
                            role="alert"
                          >
                            Cargando historial de pagos...
                          </div>
                        ) : errorPagos ? (
                          <div
                            className="alert alert-danger mt-3"
                            role="alert"
                          >
                            {errorPagos}
                          </div>
                        ) : pagos.length === 0 ? (
                          <div
                            className="alert alert-light border mt-3 mb-0"
                            role="alert"
                          >
                            {mensajeListadoPagos ||
                              "Todavía no existen pagos registrados."}
                          </div>
                        ) : (
                          <>
                            <div className="d-flex justify-content-between align-items-center mt-3">
                              <small className="text-muted">
                                Registros encontrados
                              </small>

                              <span className="badge bg-light text-dark border">
                                {pagos.length}
                              </span>
                            </div>

                            <div className="d-flex flex-column gap-3 mt-3">
                              {pagos.map((pago) => (
                                <div
                                  key={pago.id}
                                  className="border rounded p-3"
                                >
                                  <div className="d-flex justify-content-between align-items-start gap-3">
                                    <div>
                                      <strong>
                                        {pago.pagador
                                          ?.nombre_completo ||
                                          pago.pagador
                                            ?.username ||
                                          "Participante"}
                                      </strong>

                                      {pago.pagador?.username && (
                                        <small className="text-muted d-block">
                                          @{pago.pagador.username}
                                        </small>
                                      )}

                                      <small className="text-muted d-block mt-2">
                                        Fecha del pago:{" "}
                                        {formatearFecha(
                                          pago.fecha_pago
                                        )}
                                      </small>

                                      <small className="text-muted d-block">
                                        Registrado:{" "}
                                        {formatearFechaHora(
                                          pago.fecha_registro
                                        )}
                                      </small>
                                    </div>

                                    <div className="text-end">
                                      <strong className="fs-5 d-block">
                                        {formatearMonto(pago.monto)}
                                      </strong>

                                      <button
                                        type="button"
                                        className="btn btn-outline-primary btn-sm mt-2"
                                        onClick={() =>
                                          verDetallePago(pago.id)
                                        }
                                      >
                                        Ver detalle
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </>
                        )}
                      </div>

                      {!actividadActiva &&
                        !actividadCerrada && (
                          <div
                            className="alert alert-light border mt-5"
                            role="alert"
                          >
                            {actividadProgramada
                              ? "El registro de gastos comunes estará disponible cuando la actividad comience."
                              : "Configura correctamente la vigencia de la actividad para habilitar el registro de gastos."}
                          </div>
                        )}

                      {puedeRegistrarGastos && (
                        <div className="mt-5 pt-4 border-top">
                          <div className="d-flex justify-content-between align-items-center gap-3">
                            <div>
                              <h5 className="mb-1">
                                Registrar gasto común
                              </h5>

                              <small className="text-muted">
                                Ingresa la descripción, el monto y
                                la fecha del gasto de la actividad.
                              </small>
                            </div>

                            <span className="badge bg-success">
                              Actividad activa
                            </span>
                          </div>

                          <div
                            className="alert alert-light border mt-3"
                            role="alert"
                          >
                            El sistema guardará automáticamente
                            quién registra el gasto y lo asociará
                            a los {grupo.participantes?.length || 0}{" "}
                            integrantes activos.
                          </div>

                          <form
                            onSubmit={registrarGasto}
                            className="mt-3"
                          >
                            <div className="row">
                              <div className="col-md-6 mb-3">
                                <label className="form-label">
                                  Descripción del gasto
                                </label>

                                <input
                                  type="text"
                                  name="descripcion"
                                  className="form-control"
                                  placeholder="Ej: Alquiler del transporte"
                                  value={gastoData.descripcion}
                                  onChange={handleGastoChange}
                                  maxLength="150"
                                  disabled={registrandoGasto}
                                  required
                                />
                              </div>

                              <div className="col-md-3 mb-3">
                                <label className="form-label">
                                  Monto
                                </label>

                                <input
                                  type="number"
                                  name="monto"
                                  className="form-control"
                                  placeholder="0.00"
                                  min="0.01"
                                  step="0.01"
                                  value={gastoData.monto}
                                  onChange={handleGastoChange}
                                  disabled={registrandoGasto}
                                  required
                                />
                              </div>

                              <div className="col-md-3 mb-3">
                                <label className="form-label">
                                  Fecha
                                </label>

                                <input
                                  type="date"
                                  name="fecha_gasto"
                                  className="form-control"
                                  value={gastoData.fecha_gasto}
                                  onChange={handleGastoChange}
                                  disabled={registrandoGasto}
                                  required
                                />
                              </div>
                            </div>

                            <div className="d-flex justify-content-between align-items-center gap-3 mt-2">
                              <small className="text-muted">
                                No se selecciona quién pagó ni los
                                participantes incluidos.
                              </small>

                              <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={
                                  registrandoGasto ||
                                  !grupo.participantes ||
                                  grupo.participantes.length === 0
                                }
                              >
                                {registrandoGasto
                                  ? "Registrando gasto..."
                                  : "Registrar gasto común"}
                              </button>
                            </div>
                          </form>
                        </div>
                      )}

                      <div className="mt-5 pt-4 border-top">
                        <div className="d-flex justify-content-between align-items-center gap-3">
                          <div>
                            <h5 className="mb-1">
                              Gastos comunes del grupo
                            </h5>

                            <small className="text-muted">
                              Registros realizados: {gastos.length}
                            </small>
                          </div>

                          <div className="text-end">
                            <small className="text-muted d-block">
                              Total común
                            </small>

                            <strong className="fs-4">
                              {formatearMonto(totalGastos)}
                            </strong>
                          </div>
                        </div>

                        {cargandoGastos ? (
                          <div
                            className="alert alert-light border mt-3"
                            role="alert"
                          >
                            Cargando gastos del grupo...
                          </div>
                        ) : errorGastos ? (
                          <div
                            className="alert alert-danger mt-3"
                            role="alert"
                          >
                            {errorGastos}
                          </div>
                        ) : gastos.length === 0 ? (
                          <div className="empty-groups-card mt-3">
                            <h5>No hay gastos registrados</h5>

                            <p>
                              Cuando registres un gasto aparecerá
                              automáticamente en esta sección.
                            </p>
                          </div>
                        ) : (
                          <div className="mt-3">
                            {gastos.map((gasto) => (
                              <div
                                key={gasto.id}
                                className="border rounded p-3 mb-3"
                              >
                                <div className="d-flex justify-content-between align-items-start gap-3">
                                  <div>
                                    <h6 className="mb-1">
                                      {gasto.descripcion}
                                    </h6>

                                    <small className="text-muted">
                                      Fecha:{" "}
                                      {formatearFecha(
                                        gasto.fecha_gasto
                                      )}
                                    </small>
                                  </div>

                                  <div className="text-end">
                                    <strong className="fs-5 d-block">
                                      {formatearMonto(gasto.monto)}
                                    </strong>

                                    <div className="d-flex gap-2 justify-content-end mt-2">
                                      {esCreador &&
                                        !actividadCerrada && (
                                          <>
                                          <button
                                            type="button"
                                            className="btn btn-outline-secondary btn-sm"
                                            onClick={() =>
                                              abrirEdicionGasto(gasto)
                                            }
                                          >
                                            Editar
                                          </button>

                                          <button
                                            type="button"
                                            className="btn btn-outline-danger btn-sm"
                                            onClick={() =>
                                              eliminarGasto(gasto)
                                            }
                                            disabled={
                                              eliminandoGastoId ===
                                              gasto.id
                                            }
                                          >
                                            {eliminandoGastoId ===
                                            gasto.id
                                              ? "Eliminando..."
                                              : "Eliminar"}
                                          </button>
                                        </>
                                      )}

                                      <button
                                        type="button"
                                        className="btn btn-outline-primary btn-sm"
                                        onClick={() =>
                                          verDetalleGasto(gasto.id)
                                        }
                                      >
                                        Ver detalle
                                      </button>
                                    </div>
                                  </div>
                                </div>

                                <div className="mt-3">
                                  <small className="text-muted">
                                    Registrado por
                                  </small>

                                  <div>
                                    <strong>
                                      {gasto.registrado_por
                                        ?.nombre_completo ||
                                        gasto.registrado_por
                                          ?.username ||
                                        "Sin información"}
                                    </strong>

                                    {gasto.registrado_por?.username && (
                                      <span className="text-muted">
                                        {" "}
                                        (@
                                        {
                                          gasto.registrado_por
                                            .username
                                        }
                                        )
                                      </span>
                                    )}
                                  </div>
                                </div>

                                <div className="mt-3">
                                  <small className="text-muted">
                                    Integrantes asociados:{" "}
                                    {gasto.participantes?.length ||
                                      0}
                                  </small>

                                  <div className="d-flex flex-wrap gap-2 mt-2">
                                    {gasto.participantes?.map(
                                      (participante) => (
                                        <span
                                          key={participante.id}
                                          className="badge bg-light text-dark border"
                                        >
                                          {participante.nombre_completo ||
                                            participante.username}
                                        </span>
                                      )
                                    )}
                                  </div>
                                </div>

                                <div className="mt-3 p-3 border rounded bg-light">
                                  <div className="d-flex justify-content-between align-items-center">
                                    <small className="fw-semibold">
                                      División individual
                                    </small>

                                    <span className="badge bg-white text-dark border">
                                      {gasto.divisiones?.length || 0}
                                    </span>
                                  </div>

                                  {Array.isArray(gasto.divisiones) &&
                                  gasto.divisiones.length > 0 ? (
                                    <div className="d-flex flex-column gap-2 mt-3">
                                      {gasto.divisiones.map(
                                        (division) => (
                                          <div
                                            key={
                                              division.id ||
                                              `${gasto.id}-${division.participante?.id}`
                                            }
                                            className="d-flex justify-content-between align-items-center bg-white border rounded px-3 py-2"
                                          >
                                            <span>
                                              {division.participante
                                                ?.nombre_completo ||
                                                division.participante
                                                  ?.username ||
                                                "Participante"}
                                            </span>

                                            <strong>
                                              {formatearMonto(
                                                division.monto_asignado
                                              )}
                                            </strong>
                                          </div>
                                        )
                                      )}
                                    </div>
                                  ) : (
                                    <small className="text-muted d-block mt-2">
                                      No hay una división calculada para este
                                      gasto.
                                    </small>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="create-group-footer mt-4">
                      <small>
                        {actividadCerrada
                          ? "ⓘ La actividad está cerrada y permanece disponible únicamente para consulta."
                          : actividadProgramada
                            ? "ⓘ Los gastos comunes se habilitarán al iniciar la actividad; los participantes se asociarán automáticamente."
                            : "ⓘ Cada gasto común se asocia automáticamente a los integrantes activos y aumenta el total del grupo."}
                      </small>

                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => navigate("/dashboard")}
                      >
                        Volver
                      </button>
                    </div>
                  </>
                )}
              </div>


            </section>
          </>
        )}
      </main>

      {esCreador &&
        !actividadCerrada &&
        edicionGastoAbierta && (
          <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.55)",
            zIndex: 1060,
          }}
          role="dialog"
          aria-modal="true"
          aria-label="Editar gasto"
          onClick={cerrarEdicionGasto}
        >
          <div
            className="bg-white rounded shadow-lg w-100"
            style={{
              maxWidth: "760px",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="d-flex justify-content-between align-items-center border-bottom p-4">
              <div>
                <h4 className="mb-1">Editar gasto</h4>
                <small className="text-muted">
                  Modifica la información del gasto seleccionado.
                </small>
              </div>

              <button
                type="button"
                className="btn-close"
                aria-label="Cerrar"
                onClick={cerrarEdicionGasto}
                disabled={guardandoEdicionGasto}
              />
            </div>

            <form onSubmit={guardarEdicionGasto}>
              <div className="p-4">
                {errorEdicionGasto && (
                  <div
                    className="alert alert-danger"
                    role="alert"
                  >
                    {errorEdicionGasto}
                  </div>
                )}

                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label">
                      Descripción del gasto
                    </label>

                    <input
                      type="text"
                      name="descripcion"
                      className="form-control"
                      value={edicionGastoData.descripcion}
                      onChange={handleEdicionGastoChange}
                      maxLength="150"
                      disabled={guardandoEdicionGasto}
                      required
                    />
                  </div>

                  <div className="col-md-3 mb-3">
                    <label className="form-label">
                      Monto
                    </label>

                    <input
                      type="number"
                      name="monto"
                      className="form-control"
                      min="0.01"
                      step="0.01"
                      value={edicionGastoData.monto}
                      onChange={handleEdicionGastoChange}
                      disabled={guardandoEdicionGasto}
                      required
                    />
                  </div>

                  <div className="col-md-3 mb-3">
                    <label className="form-label">
                      Fecha
                    </label>

                    <input
                      type="date"
                      name="fecha_gasto"
                      className="form-control"
                      value={edicionGastoData.fecha_gasto}
                      onChange={handleEdicionGastoChange}
                      disabled={guardandoEdicionGasto}
                      required
                    />
                  </div>
                </div>

                <div
                  className="alert alert-light border mb-0"
                  role="alert"
                >
                  Este gasto es común. Los integrantes asociados
                  se conservarán y no se modifican manualmente.
                </div>
              </div>

              <div className="d-flex justify-content-end gap-2 border-top p-4">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={cerrarEdicionGasto}
                  disabled={guardandoEdicionGasto}
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={guardandoEdicionGasto}
                >
                  {guardandoEdicionGasto
                    ? "Guardando cambios..."
                    : "Guardar cambios"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {detallePagoAbierto && (
        <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.55)",
            zIndex: 1070,
          }}
          role="dialog"
          aria-modal="true"
          aria-label="Detalle del pago"
          onClick={cerrarDetallePago}
        >
          <div
            className="bg-white rounded shadow-lg w-100"
            style={{
              maxWidth: "680px",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="d-flex justify-content-between align-items-center border-bottom p-4">
              <div>
                <h4 className="mb-1">Detalle del pago</h4>

                <small className="text-muted">
                  Información completa del aporte seleccionado.
                </small>
              </div>

              <button
                type="button"
                className="btn-close"
                aria-label="Cerrar"
                onClick={cerrarDetallePago}
              />
            </div>

            <div className="p-4">
              {cargandoDetallePago ? (
                <div
                  className="alert alert-light border mb-0"
                  role="alert"
                >
                  Cargando detalle del pago...
                </div>
              ) : errorDetallePago ? (
                <div
                  className="alert alert-danger mb-0"
                  role="alert"
                >
                  {errorDetallePago}
                </div>
              ) : pagoSeleccionado ? (
                <>
                  <div className="d-flex justify-content-between align-items-start gap-3 mb-4">
                    <div>
                      <small className="text-muted">
                        Actividad
                      </small>

                      <h5 className="mb-0">
                        {grupo?.nombre || "Actividad"}
                      </h5>
                    </div>

                    <strong className="fs-4">
                      {formatearMonto(
                        pagoSeleccionado.monto
                      )}
                    </strong>
                  </div>

                  <div className="row g-3">
                    <div className="col-md-6">
                      <div className="border rounded p-3 h-100 bg-light">
                        <small className="text-muted d-block">
                          Participante que pagó
                        </small>

                        <strong>
                          {pagoSeleccionado.pagador
                            ?.nombre_completo ||
                            pagoSeleccionado.pagador
                              ?.username ||
                            "Sin información"}
                        </strong>

                        {pagoSeleccionado.pagador
                          ?.username && (
                          <small className="text-muted d-block">
                            @
                            {
                              pagoSeleccionado.pagador
                                .username
                            }
                          </small>
                        )}
                      </div>
                    </div>

                    <div className="col-md-6">
                      <div className="border rounded p-3 h-100 bg-light">
                        <small className="text-muted d-block">
                          Fecha del pago
                        </small>

                        <strong>
                          {formatearFecha(
                            pagoSeleccionado.fecha_pago
                          )}
                        </strong>
                      </div>
                    </div>

                    <div className="col-md-6">
                      <div className="border rounded p-3 h-100 bg-light">
                        <small className="text-muted d-block">
                          Registrado por
                        </small>

                        <strong>
                          {pagoSeleccionado.registrado_por
                            ?.nombre_completo ||
                            pagoSeleccionado.registrado_por
                              ?.username ||
                            "Sin información"}
                        </strong>

                        {pagoSeleccionado.registrado_por
                          ?.username && (
                          <small className="text-muted d-block">
                            @
                            {
                              pagoSeleccionado
                                .registrado_por.username
                            }
                          </small>
                        )}
                      </div>
                    </div>

                    <div className="col-md-6">
                      <div className="border rounded p-3 h-100 bg-light">
                        <small className="text-muted d-block">
                          Fecha de registro
                        </small>

                        <strong>
                          {formatearFechaHora(
                            pagoSeleccionado.fecha_registro
                          )}
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div
                    className="alert alert-light border mt-4 mb-0"
                    role="alert"
                  >
                    Este registro corresponde a un aporte propio
                    realizado por el participante.
                  </div>
                </>
              ) : (
                <div
                  className="alert alert-warning mb-0"
                  role="alert"
                >
                  No se encontró información del pago.
                </div>
              )}
            </div>

            <div className="d-flex justify-content-end border-top p-4">
              <button
                type="button"
                className="btn btn-primary"
                onClick={cerrarDetallePago}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {detalleGastoAbierto && (
        <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.55)",
            zIndex: 1050,
          }}
          role="dialog"
          aria-modal="true"
          aria-label="Detalle del gasto"
          onClick={cerrarDetalleGasto}
        >
          <div
            className="bg-white rounded shadow-lg w-100"
            style={{
              maxWidth: "680px",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="d-flex justify-content-between align-items-center border-bottom p-4">
              <div>
                <h4 className="mb-1">Detalle del gasto</h4>
                <small className="text-muted">
                  Información completa del gasto seleccionado.
                </small>
              </div>

              <button
                type="button"
                className="btn-close"
                aria-label="Cerrar"
                onClick={cerrarDetalleGasto}
              />
            </div>

            <div className="p-4">
              {cargandoDetalleGasto ? (
                <div className="alert alert-light border mb-0" role="alert">
                  Cargando detalle del gasto...
                </div>
              ) : errorDetalleGasto ? (
                <div className="alert alert-danger mb-0" role="alert">
                  {errorDetalleGasto}
                </div>
              ) : gastoSeleccionado ? (
                <>
                  <div className="d-flex justify-content-between align-items-start gap-3 mb-4">
                    <div>
                      <small className="text-muted">Descripción</small>
                      <h5 className="mb-0">
                        {gastoSeleccionado.descripcion}
                      </h5>
                    </div>

                    <strong className="fs-4">
                      {formatearMonto(gastoSeleccionado.monto)}
                    </strong>
                  </div>

                  <div className="row g-3">
                    <div className="col-md-6">
                      <small className="text-muted">Fecha del gasto</small>
                      <div className="fw-semibold">
                        {formatearFecha(gastoSeleccionado.fecha_gasto)}
                      </div>
                    </div>

                    <div className="col-md-6">
                      <small className="text-muted">Fecha de registro</small>
                      <div className="fw-semibold">
                        {formatearFechaHora(
                          gastoSeleccionado.fecha_registro
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 p-3 border rounded bg-light">
                    <small className="text-muted">
                      Tipo de registro
                    </small>

                    <div className="fw-semibold">
                      Gasto común de la actividad
                    </div>

                    <small className="text-muted d-block">
                      Asociado automáticamente a los integrantes
                      que estaban activos al registrarlo.
                    </small>
                  </div>

                  <div className="mt-4">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <h6 className="mb-0">Integrantes asociados</h6>
                      <span className="badge bg-light text-dark border">
                        {gastoSeleccionado.participantes?.length || 0}
                      </span>
                    </div>

                    {gastoSeleccionado.participantes?.length > 0 ? (
                      <div className="d-flex flex-column gap-2">
                        {gastoSeleccionado.participantes.map(
                          (participante) => (
                            <div
                              key={participante.id}
                              className="border rounded p-3"
                            >
                              <strong>
                                {participante.nombre_completo ||
                                  participante.username}
                              </strong>

                              <small className="text-muted d-block">
                                @{participante.username}
                              </small>

                              {participante.email && (
                                <small className="text-muted d-block">
                                  {participante.email}
                                </small>
                              )}
                            </div>
                          )
                        )}
                      </div>
                    ) : (
                      <div className="alert alert-light border mb-0">
                        No hay participantes asociados a este gasto.
                      </div>
                    )}
                  </div>

                  <div className="mt-4">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <div>
                        <h6 className="mb-1">División individual</h6>
                        <small className="text-muted">
                          Valor que corresponde pagar a cada participante.
                        </small>
                      </div>

                      <span className="badge bg-light text-dark border">
                        {gastoSeleccionado.divisiones?.length || 0}
                      </span>
                    </div>

                    {Array.isArray(gastoSeleccionado.divisiones) &&
                    gastoSeleccionado.divisiones.length > 0 ? (
                      <div className="d-flex flex-column gap-2">
                        {gastoSeleccionado.divisiones.map(
                          (division) => (
                            <div
                              key={
                                division.id ||
                                `${gastoSeleccionado.id}-${division.participante?.id}`
                              }
                              className="d-flex justify-content-between align-items-center border rounded p-3"
                            >
                              <div>
                                <strong>
                                  {division.participante
                                    ?.nombre_completo ||
                                    division.participante
                                      ?.username ||
                                    "Participante"}
                                </strong>

                                {division.participante?.username && (
                                  <small className="text-muted d-block">
                                    @{division.participante.username}
                                  </small>
                                )}
                              </div>

                              <div className="text-end">
                                <small className="text-muted d-block">
                                  Le corresponde
                                </small>

                                <strong className="fs-5">
                                  {formatearMonto(
                                    division.monto_asignado
                                  )}
                                </strong>
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    ) : (
                      <div className="alert alert-light border mb-0">
                        No hay una división calculada para este gasto.
                      </div>
                    )}
                  </div>

                  <div className="mt-4 p-3 border rounded">
                    <small className="text-muted">Registrado por</small>
                    <div className="fw-semibold">
                      {gastoSeleccionado.registrado_por?.nombre_completo ||
                        gastoSeleccionado.registrado_por?.username ||
                        "Sin información"}
                    </div>

                    {gastoSeleccionado.registrado_por?.username && (
                      <small className="text-muted d-block">
                        @{gastoSeleccionado.registrado_por.username}
                      </small>
                    )}
                  </div>
                </>
              ) : (
                <div className="alert alert-warning mb-0" role="alert">
                  No se encontró información del gasto.
                </div>
              )}
            </div>

            <div className="d-flex justify-content-end border-top p-4">
              <button
                type="button"
                className="btn btn-primary"
                onClick={cerrarDetalleGasto}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default GroupDetail;