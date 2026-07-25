import { useEffect, useState } from "react";
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

function GroupDetail() {
  const navigate = useNavigate();
  const { id } = useParams();

  const [grupo, setGrupo] = useState(null);
  const [usuarios, setUsuarios] = useState([]);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState("");

  const [participantesGasto, setParticipantesGasto] = useState([]);

  const [gastoData, setGastoData] = useState({
    descripcion: "",
    monto: "",
    fecha_gasto: obtenerFechaActual(),
    pagado_por_id: "",
  });

  const [registrandoGasto, setRegistrandoGasto] = useState(false);

  const [pagoData, setPagoData] = useState({
    pagador_id: "",
    receptor_id: "",
    monto: "",
    fecha_pago: obtenerFechaActual(),
  });
  const [registrandoPago, setRegistrandoPago] = useState(false);
  const [mensajePago, setMensajePago] = useState("");
  const [errorPago, setErrorPago] = useState("");

  const [gastos, setGastos] = useState([]);
  const [cargandoGastos, setCargandoGastos] = useState(true);
  const [errorGastos, setErrorGastos] = useState("");

  const [balances, setBalances] = useState([]);
  const [resumenBalances, setResumenBalances] = useState(null);
  const [cargandoBalances, setCargandoBalances] = useState(true);
  const [errorBalances, setErrorBalances] = useState("");

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
    pagado_por_id: "",
  });
  const [participantesEdicion, setParticipantesEdicion] = useState([]);
  const [guardandoEdicionGasto, setGuardandoEdicionGasto] = useState(false);
  const [errorEdicionGasto, setErrorEdicionGasto] = useState("");
  const [eliminandoGastoId, setEliminandoGastoId] = useState(null);

  const [participanteEditando, setParticipanteEditando] = useState(null);
  const [notaTemporal, setNotaTemporal] = useState("");
  const [notasParticipantes, setNotasParticipantes] = useState({});

  const [formData, setFormData] = useState({
    nombre: "",
    descripcion: "",
  });

  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [modoEdicion, setModoEdicion] = useState(false);
  const [agregandoParticipante, setAgregandoParticipante] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");

  const username = localStorage.getItem("username") || "usuario";
  const displayName =
    username.charAt(0).toUpperCase() + username.slice(1);
  const avatarLetter = username.charAt(0).toUpperCase();

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

        setFormData({
          nombre: data.nombre || "",
          descripcion: data.descripcion || "",
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
      pagado_por_id: gasto.pagado_por?.id
        ? String(gasto.pagado_por.id)
        : "",
    });
    setParticipantesEdicion(
      Array.isArray(gasto.participantes)
        ? gasto.participantes.map((participante) => participante.id)
        : []
    );
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
      pagado_por_id: "",
    });
    setParticipantesEdicion([]);
    setErrorEdicionGasto("");
  };

  const handleEdicionGastoChange = (e) => {
    setEdicionGastoData({
      ...edicionGastoData,
      [e.target.name]: e.target.value,
    });
  };

  const alternarParticipanteEdicion = (participanteId) => {
    setParticipantesEdicion((seleccionados) => {
      if (seleccionados.includes(participanteId)) {
        return seleccionados.filter(
          (item) => item !== participanteId
        );
      }

      return [...seleccionados, participanteId];
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

    if (!edicionGastoData.pagado_por_id) {
      setErrorEdicionGasto(
        "Selecciona quién pagó el gasto."
      );
      return;
    }

    if (participantesEdicion.length === 0) {
      setErrorEdicionGasto(
        "Selecciona al menos un participante para el gasto."
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
            pagado_por_id: Number(
              edicionGastoData.pagado_por_id
            ),
            participantes_ids: participantesEdicion,
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
        setGastos((gastosActuales) =>
          gastosActuales.map((gasto) =>
            gasto.id === data.gasto.id
              ? data.gasto
              : gasto
          )
        );

        setGastoSeleccionado((detalleActual) =>
          detalleActual?.id === data.gasto.id
            ? data.gasto
            : detalleActual
        );
      }

      setEdicionGastoAbierta(false);
      setGastoEditandoId(null);
      setParticipantesEdicion([]);
      setErrorEdicionGasto("");
      setMensaje(
        data.mensaje || "Gasto actualizado correctamente."
      );

      await obtenerBalances();
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

      setGastos((gastosActuales) =>
        gastosActuales.filter(
          (gastoActual) => gastoActual.id !== gasto.id
        )
      );

      if (gastoSeleccionado?.id === gasto.id) {
        cerrarDetalleGasto();
      }

      if (gastoEditandoId === gasto.id) {
        setEdicionGastoAbierta(false);
        setGastoEditandoId(null);
        setParticipantesEdicion([]);
        setErrorEdicionGasto("");
      }

      setMensaje(
        data.mensaje || "Gasto eliminado correctamente."
      );

      await obtenerBalances();
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

    if (!pagoData.pagador_id) {
      setErrorPago("Selecciona quién realiza el pago.");
      return;
    }

    if (!pagoData.receptor_id) {
      setErrorPago("Selecciona quién recibe el pago.");
      return;
    }

    if (pagoData.pagador_id === pagoData.receptor_id) {
      setErrorPago(
        "La persona que paga y la que recibe deben ser diferentes."
      );
      return;
    }

    if (!pagoData.monto || Number(pagoData.monto) <= 0) {
      setErrorPago("El monto del pago debe ser mayor que cero.");
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
            pagador_id: Number(pagoData.pagador_id),
            receptor_id: Number(pagoData.receptor_id),
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
        pagador_id: "",
        receptor_id: "",
        monto: "",
        fecha_pago: obtenerFechaActual(),
      });

      setMensajePago(
        data.mensaje || "Pago registrado correctamente."
      );
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
            nombre: formData.nombre,
            descripcion: formData.descripcion,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("No se pudo actualizar el grupo.");
      }

      const data = await response.json();

      setGrupo(data);

      setFormData({
        nombre: data.nombre || "",
        descripcion: data.descripcion || "",
      });

      setModoEdicion(false);
      setMensaje("Grupo actualizado correctamente.");
    } catch {
      setError("No se pudo actualizar el grupo. Intenta nuevamente.");
    } finally {
      setGuardando(false);
    }
  };

  const cancelarEdicion = () => {
    setFormData({
      nombre: grupo?.nombre || "",
      descripcion: grupo?.descripcion || "",
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

  const alternarParticipanteGasto = (participanteId) => {
    setParticipantesGasto((seleccionados) => {
      if (seleccionados.includes(participanteId)) {
        return seleccionados.filter(
          (item) => item !== participanteId
        );
      }

      return [...seleccionados, participanteId];
    });
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

    if (!gastoData.pagado_por_id) {
      setError("Selecciona quién pagó el gasto.");
      return;
    }

    if (participantesGasto.length === 0) {
      setError(
        "Selecciona al menos un participante para el gasto."
      );
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
            pagado_por_id: Number(gastoData.pagado_por_id),
            participantes_ids: participantesGasto,
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
        pagado_por_id: "",
      });

      setParticipantesGasto([]);

      if (data.gasto) {
        setGastos((gastosActuales) => [
          data.gasto,
          ...gastosActuales,
        ]);
      }

      setErrorGastos("");
      setMensaje(
        data.mensaje || "Gasto registrado correctamente."
      );

      await obtenerBalances();
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
      setUsuarioSeleccionado("");
      setMensaje("Participante agregado correctamente.");

      await obtenerBalances();
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
      "¿Deseas eliminar este participante del grupo?"
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

      setParticipantesGasto((seleccionados) =>
        seleccionados.filter(
          (item) => item !== participanteId
        )
      );

      setGastoData((datosActuales) => {
        if (
          Number(datosActuales.pagado_por_id) === participanteId
        ) {
          return {
            ...datosActuales,
            pagado_por_id: "",
          };
        }

        return datosActuales;
      });

      setPagoData((datosActuales) => ({
        ...datosActuales,
        pagador_id:
          Number(datosActuales.pagador_id) === participanteId
            ? ""
            : datosActuales.pagador_id,
        receptor_id:
          Number(datosActuales.receptor_id) === participanteId
            ? ""
            : datosActuales.receptor_id,
      }));

      setNotasParticipantes((notasActuales) => {
        const nuevasNotas = { ...notasActuales };
        delete nuevasNotas[participanteId];
        return nuevasNotas;
      });

      setParticipanteEditando(null);
      setNotaTemporal("");
      setMensaje("Participante eliminado correctamente.");

      await obtenerBalances();
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
          <button
            type="button"
            className="btn btn-primary w-100 mb-3"
            onClick={irARegistrarPago}
          >
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
              <h1>{grupo.nombre}</h1>

              <p>
                Revisa y administra la información general del
                grupo.
              </p>
            </header>

            <section className="create-group-grid">
              <div className="create-group-card">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h4 className="mb-0">
                    Información del grupo
                  </h4>

                  {!modoEdicion && (
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

                {modoEdicion ? (
                  <form onSubmit={guardarCambios}>
                    <div className="mt-4">
                      <label className="form-label">
                        Nombre del grupo
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
                        required
                      />
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
                        Nombre del grupo
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
                                      Participante
                                    </span>

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

                                    <button
                                      type="button"
                                      className="btn btn-outline-danger btn-sm"
                                      onClick={() =>
                                        eliminarParticipante(
                                          participante.id
                                        )
                                      }
                                    >
                                      Eliminar
                                    </button>
                                  </div>
                                </div>

                                {participanteEditando ===
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
                                      Total pagado
                                    </small>

                                    <strong className="fs-5">
                                      {formatearMonto(
                                        resumenBalances.total_pagado
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
                                              Total pagado
                                            </small>

                                            <strong>
                                              {formatearMonto(
                                                balance.total_pagado
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

                      <div
                        id="registrar-pago"
                        className="mt-5 pt-4 border-top"
                      >
                        <div>
                          <h5 className="mb-1">Registrar pago</h5>

                          <small className="text-muted">
                            Registra un pago realizado entre dos
                            participantes del grupo.
                          </small>
                        </div>

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

                        {grupo.participantes?.length < 2 && (
                          <div
                            className="alert alert-warning mt-3"
                            role="alert"
                          >
                            El grupo necesita al menos dos
                            participantes para registrar un pago.
                          </div>
                        )}

                        <form
                          onSubmit={registrarPago}
                          className="mt-3"
                        >
                          <div className="row">
                            <div className="col-md-6 mb-3">
                              <label className="form-label">
                                ¿Quién realiza el pago?
                              </label>

                              <select
                                name="pagador_id"
                                className="form-control"
                                value={pagoData.pagador_id}
                                onChange={handlePagoChange}
                                disabled={registrandoPago}
                                required
                              >
                                <option value="">
                                  Selecciona al participante que
                                  paga
                                </option>

                                {grupo.participantes?.map(
                                  (participante) => (
                                    <option
                                      key={participante.id}
                                      value={participante.id}
                                      disabled={
                                        String(participante.id) ===
                                        pagoData.receptor_id
                                      }
                                    >
                                      {
                                        participante.nombre_completo
                                      }{" "}
                                      (@{participante.username})
                                    </option>
                                  )
                                )}
                              </select>
                            </div>

                            <div className="col-md-6 mb-3">
                              <label className="form-label">
                                ¿Quién recibe el pago?
                              </label>

                              <select
                                name="receptor_id"
                                className="form-control"
                                value={pagoData.receptor_id}
                                onChange={handlePagoChange}
                                disabled={registrandoPago}
                                required
                              >
                                <option value="">
                                  Selecciona al participante que
                                  recibe
                                </option>

                                {grupo.participantes?.map(
                                  (participante) => (
                                    <option
                                      key={participante.id}
                                      value={participante.id}
                                      disabled={
                                        String(participante.id) ===
                                        pagoData.pagador_id
                                      }
                                    >
                                      {
                                        participante.nombre_completo
                                      }{" "}
                                      (@{participante.username})
                                    </option>
                                  )
                                )}
                              </select>
                            </div>

                            <div className="col-md-6 mb-3">
                              <label className="form-label">
                                Monto del pago
                              </label>

                              <input
                                type="number"
                                name="monto"
                                className="form-control"
                                placeholder="0.00"
                                min="0.01"
                                step="0.01"
                                value={pagoData.monto}
                                onChange={handlePagoChange}
                                disabled={registrandoPago}
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
                                disabled={registrandoPago}
                                required
                              />
                            </div>
                          </div>

                          <div className="d-flex justify-content-between align-items-center gap-3 mt-2">
                            <small className="text-muted">
                              El pago quedará asociado a este
                              grupo y al usuario que lo registra.
                            </small>

                            <button
                              type="submit"
                              className="btn btn-primary"
                              disabled={
                                registrandoPago ||
                                !grupo.participantes ||
                                grupo.participantes.length < 2
                              }
                            >
                              {registrandoPago
                                ? "Registrando pago..."
                                : "Registrar pago"}
                            </button>
                          </div>
                        </form>
                      </div>

                      <div className="mt-5 pt-4 border-top">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <h5 className="mb-1">
                              Registrar gasto
                            </h5>

                            <small className="text-muted">
                              Ingresa la información del gasto
                              realizado en este grupo.
                            </small>
                          </div>
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
                                placeholder="Ej: Compra de alimentos"
                                value={gastoData.descripcion}
                                onChange={handleGastoChange}
                                maxLength="150"
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
                                required
                              />
                            </div>
                          </div>

                          <div className="mb-4">
                            <label className="form-label">
                              ¿Quién pagó?
                            </label>

                            <select
                              name="pagado_por_id"
                              className="form-control"
                              value={
                                gastoData.pagado_por_id
                              }
                              onChange={handleGastoChange}
                              required
                            >
                              <option value="">
                                Selecciona al participante que
                                pagó
                              </option>

                              {grupo.participantes?.map(
                                (participante) => (
                                  <option
                                    key={participante.id}
                                    value={participante.id}
                                  >
                                    {
                                      participante.nombre_completo
                                    }{" "}
                                    (@{participante.username})
                                  </option>
                                )
                              )}
                            </select>
                          </div>

                          <div className="mb-3">
                            <div className="d-flex justify-content-between align-items-center">
                              <label className="form-label mb-0">
                                Participantes incluidos en el
                                gasto
                              </label>

                              <small className="text-muted">
                                Seleccionados:{" "}
                                {participantesGasto.length}
                              </small>
                            </div>

                            {grupo.participantes &&
                            grupo.participantes.length > 0 ? (
                              <div className="mt-3">
                                {grupo.participantes.map(
                                  (participante) => (
                                    <label
                                      key={participante.id}
                                      className="d-flex justify-content-between align-items-center border rounded p-3 mb-2"
                                      style={{
                                        cursor: "pointer",
                                      }}
                                    >
                                      <div className="d-flex align-items-center gap-3">
                                        <input
                                          type="checkbox"
                                          checked={participantesGasto.includes(
                                            participante.id
                                          )}
                                          onChange={() =>
                                            alternarParticipanteGasto(
                                              participante.id
                                            )
                                          }
                                        />

                                        <div>
                                          <strong>
                                            {
                                              participante.nombre_completo
                                            }
                                          </strong>

                                          <br />

                                          <small className="text-muted">
                                            @
                                            {
                                              participante.username
                                            }
                                          </small>
                                        </div>
                                      </div>

                                      <span className="badge bg-light text-dark">
                                        {participantesGasto.includes(
                                          participante.id
                                        )
                                          ? "Incluido"
                                          : "No incluido"}
                                      </span>
                                    </label>
                                  )
                                )}
                              </div>
                            ) : (
                              <div className="empty-groups-card mt-3">
                                <h5>
                                  No hay participantes
                                  disponibles
                                </h5>

                                <p>
                                  Primero agrega participantes
                                  al grupo para registrar un
                                  gasto.
                                </p>
                              </div>
                            )}
                          </div>

                          <div className="d-flex justify-content-end mt-4">
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
                                : "Registrar gasto"}
                            </button>
                          </div>
                        </form>
                      </div>

                      <div className="mt-5 pt-4 border-top">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <h5 className="mb-1">
                              Gastos del grupo
                            </h5>

                            <small className="text-muted">
                              Total de gastos registrados:{" "}
                              {gastos.length}
                            </small>
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
                                        onClick={() => eliminarGasto(gasto)}
                                        disabled={
                                          eliminandoGastoId === gasto.id
                                        }
                                      >
                                        {eliminandoGastoId === gasto.id
                                          ? "Eliminando..."
                                          : "Eliminar"}
                                      </button>

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
                                    Pagado por
                                  </small>

                                  <div>
                                    <strong>
                                      {gasto.pagado_por
                                        ?.nombre_completo ||
                                        gasto.pagado_por
                                          ?.username ||
                                        "Sin información"}
                                    </strong>

                                    {gasto.pagado_por?.username && (
                                      <span className="text-muted">
                                        {" "}
                                        (@
                                        {
                                          gasto.pagado_por
                                            .username
                                        }
                                        )
                                      </span>
                                    )}
                                  </div>
                                </div>

                                <div className="mt-3">
                                  <small className="text-muted">
                                    Participantes incluidos:{" "}
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
                        ⓘ Los gastos registrados se guardan en
                        la base de datos y quedan asociados a
                        este grupo.
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

              <aside className="benefits-column">
                <div className="benefits-card">
                  <h4>Gestión de gastos</h4>

                  <ul>
                    <li>
                      Registra el concepto y el valor total.
                    </li>

                    <li>
                      Selecciona quién realizó el pago.
                    </li>

                    <li>
                      Incluye a los participantes relacionados.
                    </li>
                  </ul>
                </div>
              </aside>
            </section>
          </>
        )}
      </main>

      {edicionGastoAbierta && (
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

                <div className="mb-4">
                  <label className="form-label">
                    ¿Quién pagó?
                  </label>

                  <select
                    name="pagado_por_id"
                    className="form-control"
                    value={edicionGastoData.pagado_por_id}
                    onChange={handleEdicionGastoChange}
                    disabled={guardandoEdicionGasto}
                    required
                  >
                    <option value="">
                      Selecciona al participante que pagó
                    </option>

                    {grupo?.participantes?.map(
                      (participante) => (
                        <option
                          key={participante.id}
                          value={participante.id}
                        >
                          {participante.nombre_completo} (@
                          {participante.username})
                        </option>
                      )
                    )}
                  </select>
                </div>

                <div>
                  <div className="d-flex justify-content-between align-items-center">
                    <label className="form-label mb-0">
                      Participantes incluidos
                    </label>

                    <small className="text-muted">
                      Seleccionados: {participantesEdicion.length}
                    </small>
                  </div>

                  <div className="mt-3">
                    {grupo?.participantes?.map(
                      (participante) => (
                        <label
                          key={participante.id}
                          className="d-flex justify-content-between align-items-center border rounded p-3 mb-2"
                          style={{ cursor: "pointer" }}
                        >
                          <div className="d-flex align-items-center gap-3">
                            <input
                              type="checkbox"
                              checked={participantesEdicion.includes(
                                participante.id
                              )}
                              onChange={() =>
                                alternarParticipanteEdicion(
                                  participante.id
                                )
                              }
                              disabled={guardandoEdicionGasto}
                            />

                            <div>
                              <strong>
                                {participante.nombre_completo}
                              </strong>

                              <small className="text-muted d-block">
                                @{participante.username}
                              </small>
                            </div>
                          </div>

                          <span className="badge bg-light text-dark border">
                            {participantesEdicion.includes(
                              participante.id
                            )
                              ? "Incluido"
                              : "No incluido"}
                          </span>
                        </label>
                      )
                    )}
                  </div>
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
                    <small className="text-muted">Pagado por</small>
                    <div className="fw-semibold">
                      {gastoSeleccionado.pagado_por?.nombre_completo ||
                        gastoSeleccionado.pagado_por?.username ||
                        "Sin información"}
                    </div>

                    {gastoSeleccionado.pagado_por?.username && (
                      <small className="text-muted d-block">
                        @{gastoSeleccionado.pagado_por.username}
                      </small>
                    )}

                    {gastoSeleccionado.pagado_por?.email && (
                      <small className="text-muted d-block">
                        {gastoSeleccionado.pagado_por.email}
                      </small>
                    )}
                  </div>

                  <div className="mt-4">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <h6 className="mb-0">Participantes incluidos</h6>
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