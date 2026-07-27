from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MinValueValidator,
)
from django.db import models, transaction
from django.utils import timezone



def ruta_evidencia_resolucion(
    instancia,
    nombre_archivo,
):
    extension = Path(
        nombre_archivo
    ).suffix.lower()

    nombre_seguro = (
        f"{uuid4().hex}{extension}"
    )

    return (
        "evidencias_resolucion/"
        f"grupo_{instancia.grupo_id}/"
        f"deuda_{instancia.deuda_id}/"
        f"{nombre_seguro}"
    )


class Group(models.Model):
    ESTADO_SIN_CONFIGURAR = "sin_configurar"
    ESTADO_PROGRAMADA = "programada"
    ESTADO_ACTIVA = "activa"
    ESTADO_CERRADA = "cerrada"

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    creador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="grupos_creados",
    )

    participantes = models.ManyToManyField(
        User,
        related_name="grupos_participante",
        blank=True,
    )

    fecha_inicio = models.DateTimeField(
        null=True,
        blank=True,
    )

    fecha_fin = models.DateTimeField(
        null=True,
        blank=True,
    )

    fecha_cierre_automatico = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    fecha_generacion_saldos = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    caso_excepcional_todos_deben = models.BooleanField(
        default=False,
        editable=False,
    )

    fecha_deteccion_todos_deben = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()

        if self.fecha_inicio and not self.fecha_fin:
            raise ValidationError({
                "fecha_fin": (
                    "Debes establecer la fecha y hora de finalización."
                )
            })

        if self.fecha_fin and not self.fecha_inicio:
            raise ValidationError({
                "fecha_inicio": (
                    "Debes establecer la fecha y hora de inicio."
                )
            })

        if (
            self.fecha_inicio
            and self.fecha_fin
            and self.fecha_fin <= self.fecha_inicio
        ):
            raise ValidationError({
                "fecha_fin": (
                    "La fecha y hora de finalización debe ser "
                    "posterior a la fecha y hora de inicio."
                )
            })

    @property
    def estado(self):
        if not self.fecha_inicio or not self.fecha_fin:
            return self.ESTADO_SIN_CONFIGURAR

        if self.fecha_cierre_automatico:
            return self.ESTADO_CERRADA

        fecha_actual = timezone.now()

        if fecha_actual < self.fecha_inicio:
            return self.ESTADO_PROGRAMADA

        if fecha_actual >= self.fecha_fin:
            return self.ESTADO_CERRADA

        return self.ESTADO_ACTIVA

    def debe_cerrarse_automaticamente(
        self,
        momento=None,
    ):
        momento = momento or timezone.now()

        return bool(
            self.pk
            and self.fecha_fin
            and not self.fecha_cierre_automatico
            and momento >= self.fecha_fin
        )

    @transaction.atomic
    def cerrar_automaticamente(
        self,
        momento=None,
    ):
        momento = momento or timezone.now()

        if not self.pk:
            return False

        grupo_bloqueado = (
            Group.objects
            .select_for_update()
            .get(pk=self.pk)
        )

        if not grupo_bloqueado.debe_cerrarse_automaticamente(
            momento
        ):
            self.fecha_cierre_automatico = (
                grupo_bloqueado.fecha_cierre_automatico
            )
            self.fecha_generacion_saldos = (
                grupo_bloqueado.fecha_generacion_saldos
            )
            self.caso_excepcional_todos_deben = (
                grupo_bloqueado
                .caso_excepcional_todos_deben
            )
            self.fecha_deteccion_todos_deben = (
                grupo_bloqueado
                .fecha_deteccion_todos_deben
            )
            return False

        fecha_cierre_efectiva = (
            grupo_bloqueado.fecha_fin
        )

        grupo_bloqueado.fecha_cierre_automatico = (
            fecha_cierre_efectiva
        )

        grupo_bloqueado.save(
            update_fields=[
                "fecha_cierre_automatico",
            ]
        )

        resumen_saldos = (
            grupo_bloqueado.generar_saldos_cierre(
                momento=momento
            )
        )

        ActivityHistory.registrar(
            grupo=grupo_bloqueado,
            usuario=None,
            tipo_accion=(
                ActivityHistory
                .TIPO_ACTIVIDAD_CERRADA_AUTOMATICAMENTE
            ),
            descripcion=(
                f'El sistema cerró automáticamente la '
                f'actividad "{grupo_bloqueado.nombre}".'
            ),
            datos={
                "grupo_id": grupo_bloqueado.id,
                "grupo_nombre": (
                    grupo_bloqueado.nombre
                ),
                "fecha_fin_programada": (
                    grupo_bloqueado.fecha_fin.isoformat()
                ),
                "fecha_cierre_efectiva": (
                    fecha_cierre_efectiva.isoformat()
                ),
                "procesado_en": momento.isoformat(),
                "estado": self.ESTADO_CERRADA,
                "origen": "sistema",
                "saldos_cierre": resumen_saldos,
            },
        )

        self.fecha_cierre_automatico = (
            grupo_bloqueado.fecha_cierre_automatico
        )

        self.fecha_generacion_saldos = (
            grupo_bloqueado.fecha_generacion_saldos
        )

        self.caso_excepcional_todos_deben = (
            grupo_bloqueado
            .caso_excepcional_todos_deben
        )

        self.fecha_deteccion_todos_deben = (
            grupo_bloqueado
            .fecha_deteccion_todos_deben
        )

        return True

    @transaction.atomic
    def generar_saldos_cierre(
        self,
        momento=None,
    ):
        momento = momento or timezone.now()

        if not self.pk:
            raise ValidationError(
                "La actividad debe existir antes de generar saldos."
            )

        grupo_bloqueado = (
            Group.objects
            .select_for_update()
            .get(pk=self.pk)
        )

        if not grupo_bloqueado.fecha_cierre_automatico:
            raise ValidationError(
                (
                    "Los saldos solo pueden generarse "
                    "cuando la actividad está cerrada."
                )
            )

        if grupo_bloqueado.fecha_generacion_saldos:
            self.fecha_generacion_saldos = (
                grupo_bloqueado.fecha_generacion_saldos
            )
            self.caso_excepcional_todos_deben = (
                grupo_bloqueado
                .caso_excepcional_todos_deben
            )
            self.fecha_deteccion_todos_deben = (
                grupo_bloqueado
                .fecha_deteccion_todos_deben
            )

            return (
                grupo_bloqueado
                .obtener_resumen_saldos_cierre(
                    generados=False
                )
            )

        cuotas_por_usuario = {
            fila["participante_id"]: (
                fila["cuota_total"]
                or Decimal("0.00")
            )
            for fila in (
                ExpenseDivision.objects
                .filter(
                    gasto__grupo=grupo_bloqueado
                )
                .values("participante_id")
                .annotate(
                    cuota_total=models.Sum(
                        "monto_asignado"
                    )
                )
            )
        }

        pagos_por_usuario = {
            fila["pagador_id"]: (
                fila["total_pagado"]
                or Decimal("0.00")
            )
            for fila in (
                Payment.objects
                .filter(
                    grupo=grupo_bloqueado
                )
                .values("pagador_id")
                .annotate(
                    total_pagado=models.Sum(
                        "monto"
                    )
                )
            )
        }

        usuarios_ids = sorted(
            set(cuotas_por_usuario)
            | set(pagos_por_usuario)
        )

        usuarios = {
            usuario.id: usuario
            for usuario in User.objects.filter(
                id__in=usuarios_ids
            )
        }

        saldos_creados = []
        deudas_creadas = []
        saldos_con_obligacion = []

        total_cuotas = Decimal("0.00")
        total_pagado = Decimal("0.00")
        total_pendiente = Decimal("0.00")

        for usuario_id in usuarios_ids:
            usuario = usuarios.get(
                usuario_id
            )

            if not usuario:
                continue

            cuota_total = (
                cuotas_por_usuario.get(
                    usuario_id,
                    Decimal("0.00"),
                )
            ).quantize(
                Decimal("0.01")
            )

            pagado_total = (
                pagos_por_usuario.get(
                    usuario_id,
                    Decimal("0.00"),
                )
            ).quantize(
                Decimal("0.01")
            )

            saldo_pendiente = (
                cuota_total
                - pagado_total
            ).quantize(
                Decimal("0.01")
            )

            if saldo_pendiente < Decimal("0.00"):
                saldo_pendiente = Decimal("0.00")

            estado = (
                ClosingBalance.ESTADO_SALDADO
                if saldo_pendiente == Decimal("0.00")
                else ClosingBalance.ESTADO_PENDIENTE
            )

            saldo = ClosingBalance.objects.create(
                grupo=grupo_bloqueado,
                grupo_nombre=grupo_bloqueado.nombre,
                participante=usuario,
                participante_username=usuario.username,
                cuota_total=cuota_total,
                total_pagado=pagado_total,
                saldo_pendiente=saldo_pendiente,
                estado=estado,
            )

            saldos_creados.append(
                saldo
            )

            if cuota_total > Decimal("0.00"):
                saldos_con_obligacion.append(
                    saldo
                )

            if saldo_pendiente > Decimal("0.00"):
                deuda = Debt.objects.create(
                    grupo=grupo_bloqueado,
                    grupo_nombre=grupo_bloqueado.nombre,
                    saldo_cierre=saldo,
                    participante=usuario,
                    participante_username=usuario.username,
                    monto_original=saldo_pendiente,
                    saldo_pendiente=saldo_pendiente,
                    estado=Debt.ESTADO_PENDIENTE,
                )

                deudas_creadas.append(
                    deuda
                )

            total_cuotas += cuota_total
            total_pagado += pagado_total
            total_pendiente += saldo_pendiente

        total_participantes_con_obligacion = len(
            saldos_con_obligacion
        )

        caso_todos_deben = bool(
            total_participantes_con_obligacion
            and all(
                saldo.saldo_pendiente
                > Decimal("0.00")
                for saldo in saldos_con_obligacion
            )
        )

        total_deudas_registradas = sum(
            (
                deuda.saldo_pendiente
                for deuda in deudas_creadas
            ),
            Decimal("0.00"),
        ).quantize(
            Decimal("0.01")
        )

        total_pendiente = total_pendiente.quantize(
            Decimal("0.01")
        )

        if total_deudas_registradas != total_pendiente:
            raise ValidationError(
                (
                    "La suma de las deudas no coincide "
                    "con el total pendiente de la actividad."
                )
            )

        grupo_bloqueado.fecha_generacion_saldos = (
            momento
        )

        grupo_bloqueado.caso_excepcional_todos_deben = (
            caso_todos_deben
        )

        grupo_bloqueado.fecha_deteccion_todos_deben = (
            momento
            if caso_todos_deben
            else None
        )

        grupo_bloqueado.save(
            update_fields=[
                "fecha_generacion_saldos",
                "caso_excepcional_todos_deben",
                "fecha_deteccion_todos_deben",
            ]
        )

        self.fecha_generacion_saldos = (
            grupo_bloqueado.fecha_generacion_saldos
        )

        self.caso_excepcional_todos_deben = (
            grupo_bloqueado
            .caso_excepcional_todos_deben
        )

        self.fecha_deteccion_todos_deben = (
            grupo_bloqueado
            .fecha_deteccion_todos_deben
        )

        if caso_todos_deben:
            responsable = (
                grupo_bloqueado.responsable_deudas
            )

            ActivityHistory.registrar(
                grupo=grupo_bloqueado,
                usuario=None,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_CASO_TODOS_DEBEN_DETECTADO
                ),
                descripcion=(
                    "El sistema detectó que todos los "
                    "participantes con obligaciones "
                    f'de la actividad '
                    f'"{grupo_bloqueado.nombre}" '
                    "mantienen saldos pendientes."
                ),
                datos={
                    "grupo_id": grupo_bloqueado.id,
                    "grupo_nombre": (
                        grupo_bloqueado.nombre
                    ),
                    "caso_todos_deben": True,
                    "total_participantes_con_obligacion": (
                        total_participantes_con_obligacion
                    ),
                    "total_deudores": len(
                        deudas_creadas
                    ),
                    "total_pendiente": (
                        f"{total_pendiente:.2f}"
                    ),
                    "deudas_ids": [
                        deuda.id
                        for deuda in deudas_creadas
                    ],
                    "responsable_deudas": {
                        "usuario_id": (
                            responsable.id
                            if responsable
                            else None
                        ),
                        "username": (
                            responsable.username
                            if responsable
                            else None
                        ),
                        "es_acreedor_automatico": False,
                    },
                    "detectado_en": momento.isoformat(),
                },
            )

        if not saldos_creados:
            mensaje = (
                "La actividad cerró sin gastos, pagos "
                "ni saldos pendientes."
            )
        elif caso_todos_deben:
            mensaje = (
                "Todos los participantes con obligaciones "
                "mantienen saldos pendientes."
            )
        elif not deudas_creadas:
            mensaje = (
                "Todos los participantes quedaron saldados."
            )
        else:
            mensaje = (
                "Saldos pendientes generados correctamente."
            )

        return {
            "generados": True,
            "mensaje": mensaje,
            "caso_todos_deben": caso_todos_deben,
            "total_participantes_con_obligacion": (
                total_participantes_con_obligacion
            ),
            "total_saldos": len(saldos_creados),
            "total_deudas": len(deudas_creadas),
            "total_cuotas": f"{total_cuotas:.2f}",
            "total_pagado": f"{total_pagado:.2f}",
            "total_pendiente": f"{total_pendiente:.2f}",
        }

    def obtener_resumen_saldos_cierre(
        self,
        generados=None,
    ):
        saldos = self.saldos_cierre.all()

        total_cuotas = (
            saldos.aggregate(
                total=models.Sum("cuota_total")
            )["total"]
            or Decimal("0.00")
        )

        total_pagado = (
            saldos.aggregate(
                total=models.Sum("total_pagado")
            )["total"]
            or Decimal("0.00")
        )

        total_pendiente = (
            saldos.aggregate(
                total=models.Sum("saldo_pendiente")
            )["total"]
            or Decimal("0.00")
        )

        total_saldos = saldos.count()
        total_deudas = self.deudas_generadas.count()

        saldos_con_obligacion = saldos.filter(
            cuota_total__gt=Decimal("0.00")
        )

        total_participantes_con_obligacion = (
            saldos_con_obligacion.count()
        )

        caso_todos_deben_calculado = bool(
            total_participantes_con_obligacion
            and not saldos_con_obligacion.filter(
                saldo_pendiente__lte=Decimal("0.00")
            ).exists()
        )

        caso_todos_deben = bool(
            self.caso_excepcional_todos_deben
            or caso_todos_deben_calculado
        )

        if total_saldos == 0:
            mensaje = (
                "La actividad cerró sin gastos, pagos "
                "ni saldos pendientes."
            )
        elif caso_todos_deben:
            mensaje = (
                "Todos los participantes con obligaciones "
                "mantienen saldos pendientes."
            )
        elif total_deudas == 0:
            mensaje = (
                "Todos los participantes quedaron saldados."
            )
        else:
            mensaje = (
                "Saldos pendientes consultados correctamente."
            )

        respuesta = {
            "mensaje": mensaje,
            "caso_todos_deben": caso_todos_deben,
            "fecha_deteccion_todos_deben": (
                self.fecha_deteccion_todos_deben
            ),
            "total_participantes_con_obligacion": (
                total_participantes_con_obligacion
            ),
            "total_saldos": total_saldos,
            "total_deudas": total_deudas,
            "total_cuotas": f"{total_cuotas:.2f}",
            "total_pagado": f"{total_pagado:.2f}",
            "total_pendiente": f"{total_pendiente:.2f}",
        }

        if generados is not None:
            respuesta["generados"] = generados

        return respuesta

    @classmethod
    def cerrar_actividades_vencidas(
        cls,
        momento=None,
    ):
        momento = momento or timezone.now()

        grupos_ids = list(
            cls.objects
            .filter(
                fecha_fin__isnull=False,
                fecha_fin__lte=momento,
                fecha_cierre_automatico__isnull=True,
            )
            .order_by("fecha_fin", "id")
            .values_list(
                "id",
                flat=True,
            )
        )

        cantidad_cerrada = 0

        for grupo_id in grupos_ids:
            grupo = cls.objects.get(
                id=grupo_id
            )

            if grupo.cerrar_automaticamente(
                momento=momento
            ):
                cantidad_cerrada += 1

        return cantidad_cerrada

    def obtener_integrantes_activos(self):
        return (
            User.objects
            .filter(
                membresias_grupos__grupo=self,
                membresias_grupos__activo=True,
            )
            .distinct()
            .order_by("id")
        )

    @property
    def asignacion_responsable_deudas_vigente(self):
        if not self.pk:
            return None

        return (
            self.asignaciones_responsable_deudas
            .filter(vigente=True)
            .select_related(
                "responsable",
                "asignado_por",
            )
            .first()
        )

    @property
    def responsable_deudas(self):
        asignacion = (
            self.asignacion_responsable_deudas_vigente
        )

        return (
            asignacion.responsable
            if asignacion
            else None
        )

    @property
    def mensaje_responsable_deudas(self):
        responsable = self.responsable_deudas

        if not responsable:
            return (
                "No existe un responsable asignado "
                "para revisar las deudas."
            )

        return (
            f"{responsable.username} es el responsable "
            "vigente de revisar las deudas."
        )

    def puede_revisar_solicitudes_deuda(
        self,
        usuario,
    ):
        if (
            not usuario
            or not getattr(
                usuario,
                "is_authenticated",
                False,
            )
        ):
            return False

        asignacion = (
            self.asignacion_responsable_deudas_vigente
        )

        if (
            not asignacion
            or asignacion.responsable_id != usuario.id
        ):
            return False

        return GroupMembership.objects.filter(
            grupo=self,
            usuario=usuario,
            activo=True,
        ).exists()

    @transaction.atomic
    def asignar_responsable_deudas(
        self,
        responsable,
        asignado_por,
        momento=None,
    ):
        momento = momento or timezone.now()

        if not self.pk:
            raise ValidationError(
                (
                    "La actividad debe existir antes de "
                    "asignar un responsable."
                )
            )

        if not responsable or not responsable.pk:
            raise ValidationError({
                "responsable_id": (
                    "Debes seleccionar un usuario válido."
                )
            })

        if not asignado_por or not asignado_por.pk:
            raise ValidationError(
                (
                    "No se pudo identificar al usuario "
                    "que realiza la asignación."
                )
            )

        grupo_bloqueado = (
            Group.objects
            .select_for_update()
            .select_related("creador")
            .get(pk=self.pk)
        )

        if grupo_bloqueado.creador_id != asignado_por.id:
            raise ValidationError({
                "responsable_id": (
                    "Solo el creador de la actividad puede "
                    "asignar al responsable de las deudas."
                )
            })

        membresia_activa = (
            GroupMembership.objects
            .filter(
                grupo=grupo_bloqueado,
                usuario=responsable,
                activo=True,
            )
            .exists()
        )

        if not membresia_activa:
            raise ValidationError({
                "responsable_id": (
                    "El responsable debe tener una "
                    "membresía activa en la actividad."
                )
            })

        asignacion_anterior = (
            DebtReviewAssignment.objects
            .select_for_update()
            .filter(
                grupo=grupo_bloqueado,
                vigente=True,
            )
            .select_related("responsable")
            .first()
        )

        if (
            asignacion_anterior
            and asignacion_anterior.responsable_id
            == responsable.id
        ):
            return asignacion_anterior, False

        datos_anterior = None

        if asignacion_anterior:
            datos_anterior = {
                "asignacion_id": (
                    asignacion_anterior.id
                ),
                "responsable_id": (
                    asignacion_anterior.responsable_id
                ),
                "responsable_username": (
                    asignacion_anterior
                    .responsable_username
                ),
                "fecha_asignacion": (
                    asignacion_anterior
                    .fecha_asignacion
                    .isoformat()
                ),
            }

            asignacion_anterior.finalizar(
                momento=momento
            )

        nueva_asignacion = (
            DebtReviewAssignment.objects.create(
                grupo=grupo_bloqueado,
                responsable=responsable,
                responsable_username=(
                    responsable.username
                ),
                asignado_por=asignado_por,
                asignado_por_username=(
                    asignado_por.username
                ),
                fecha_asignacion=momento,
                vigente=True,
            )
        )

        tipo_accion = (
            ActivityHistory
            .TIPO_RESPONSABLE_DEUDAS_CAMBIADO
            if asignacion_anterior
            else ActivityHistory
            .TIPO_RESPONSABLE_DEUDAS_ASIGNADO
        )

        descripcion = (
            f'{asignado_por.username} cambió al '
            f'responsable de las deudas de '
            f'"{grupo_bloqueado.nombre}" a '
            f'{responsable.username}.'
            if asignacion_anterior
            else (
                f'{asignado_por.username} asignó a '
                f'{responsable.username} como responsable '
                f'de las deudas de '
                f'"{grupo_bloqueado.nombre}".'
            )
        )

        ActivityHistory.registrar(
            grupo=grupo_bloqueado,
            usuario=asignado_por,
            tipo_accion=tipo_accion,
            descripcion=descripcion,
            datos={
                "asignacion_id": nueva_asignacion.id,
                "responsable_anterior": datos_anterior,
                "responsable_nuevo": {
                    "usuario_id": responsable.id,
                    "username": responsable.username,
                },
                "asignado_por": {
                    "usuario_id": asignado_por.id,
                    "username": asignado_por.username,
                },
                "fecha_asignacion": (
                    momento.isoformat()
                ),
                "vigente": True,
            },
        )

        return nueva_asignacion, True

    def obtener_deuda_propia(
        self,
        usuario,
    ):
        if (
            not usuario
            or not getattr(
                usuario,
                "is_authenticated",
                False,
            )
        ):
            return None

        return (
            self.deudas_generadas
            .filter(
                participante=usuario,
            )
            .select_related(
                "participante",
                "saldo_cierre",
            )
            .first()
        )

    def obtener_deudas_para_revision(
        self,
        usuario,
    ):
        if not self.puede_revisar_solicitudes_deuda(
            usuario
        ):
            raise ValidationError(
                (
                    "Solo el responsable vigente puede "
                    "revisar las solicitudes de resolución "
                    "de deuda."
                )
            )

        return (
            self.deudas_generadas
            .select_related(
                "participante",
                "saldo_cierre",
            )
            .order_by(
                "-fecha_generacion",
                "-id",
            )
        )

    def obtener_solicitudes_resolucion_para_revision(
        self,
        usuario,
        solo_pendientes=True,
    ):
        if not self.puede_revisar_solicitudes_deuda(
            usuario
        ):
            raise ValidationError(
                (
                    "Solo el responsable vigente puede "
                    "consultar y revisar las solicitudes "
                    "de resolución de deuda."
                )
            )

        solicitudes = (
            self.solicitudes_resolucion_deudas
            .select_related(
                "grupo",
                "deuda",
                "deuda__participante",
                "deuda__saldo_cierre",
                "solicitante",
                "revisado_por",
            )
            .order_by(
                "-fecha_envio",
                "-id",
            )
        )

        if solo_pendientes:
            solicitudes = solicitudes.filter(
                estado=(
                    DebtResolutionRequest
                    .ESTADO_PENDIENTE_REVISION
                )
            )

        return solicitudes

    @property
    def mensaje_caso_todos_deben(self):
        if not self.caso_excepcional_todos_deben:
            return None

        return (
            "Todos los participantes con obligaciones "
            "mantienen saldos pendientes."
        )

    def obtener_advertencia_deudas_usuario(
        self,
        usuario,
    ):
        resumen = (
            Debt.resumen_deudas_activas_usuario(
                usuario
            )
        )

        cantidad = resumen[
            "cantidad_deudas_pendientes"
        ]

        monto_total = resumen[
            "monto_total_pendiente"
        ]

        tiene_deudas = cantidad > 0

        if tiene_deudas:
            mensaje = (
                f"{usuario.username} mantiene "
                f"{cantidad} obligación(es) pendiente(s) "
                f"por un total de ${monto_total:.2f}. "
                "Debes confirmar si deseas continuar "
                "con la incorporación."
            )
        else:
            mensaje = (
                f"{usuario.username} no mantiene "
                "deudas pendientes."
            )

        return {
            "usuario": {
                "id": usuario.id,
                "username": usuario.username,
            },
            "tiene_deudas_pendientes": tiene_deudas,
            "requiere_confirmacion": tiene_deudas,
            "cantidad_deudas_pendientes": cantidad,
            "monto_total_pendiente": (
                f"{monto_total:.2f}"
            ),
            "mensaje": mensaje,
        }

    @transaction.atomic
    def incorporar_participante(
        self,
        usuario,
        agregado_por,
        confirmar_deudas=False,
        momento=None,
    ):
        momento = momento or timezone.now()

        if not self.pk:
            raise ValidationError(
                (
                    "La actividad debe existir antes "
                    "de agregar participantes."
                )
            )

        if not usuario or not usuario.pk:
            raise ValidationError({
                "usuario_id": (
                    "Debes seleccionar un usuario válido."
                )
            })

        if not agregado_por or not agregado_por.pk:
            raise ValidationError(
                (
                    "No se pudo identificar al usuario "
                    "que realiza la incorporación."
                )
            )

        grupo_bloqueado = (
            Group.objects
            .select_for_update()
            .select_related("creador")
            .get(pk=self.pk)
        )

        if grupo_bloqueado.creador_id != agregado_por.id:
            raise ValidationError({
                "usuario_id": (
                    "Solo el creador de la actividad puede "
                    "agregar participantes."
                )
            })

        if (
            grupo_bloqueado.estado
            == Group.ESTADO_CERRADA
        ):
            raise ValidationError({
                "usuario_id": (
                    "No se pueden modificar participantes "
                    "porque la actividad está cerrada."
                )
            })

        if GroupMembership.objects.filter(
            grupo=grupo_bloqueado,
            usuario=usuario,
            activo=True,
        ).exists():
            raise ValidationError({
                "usuario_id": (
                    "El usuario ya es participante activo "
                    "del grupo."
                )
            })

        advertencia = (
            grupo_bloqueado
            .obtener_advertencia_deudas_usuario(
                usuario
            )
        )

        if (
            advertencia["requiere_confirmacion"]
            and not confirmar_deudas
        ):
            return None, advertencia, False

        tenia_membresia_previa = (
            GroupMembership.objects
            .filter(
                grupo=grupo_bloqueado,
                usuario=usuario,
                activo=False,
            )
            .exists()
        )

        membresia = GroupMembership.objects.create(
            grupo=grupo_bloqueado,
            usuario=usuario,
            fecha_ingreso=momento,
        )

        grupo_bloqueado.participantes.add(
            usuario
        )

        tipo_accion = (
            ActivityHistory
            .TIPO_PARTICIPANTE_REINGRESO
            if tenia_membresia_previa
            else ActivityHistory
            .TIPO_PARTICIPANTE_INGRESO
        )

        accion = (
            "reingresó a"
            if tenia_membresia_previa
            else "ingresó a"
        )

        ActivityHistory.registrar(
            grupo=grupo_bloqueado,
            usuario=agregado_por,
            tipo_accion=tipo_accion,
            descripcion=(
                f"{agregado_por.username} agregó a "
                f"{usuario.username}, quien {accion} "
                f'la actividad '
                f'"{grupo_bloqueado.nombre}".'
            ),
            datos={
                "participante_id": usuario.id,
                "participante_username": (
                    usuario.username
                ),
                "membresia_id": membresia.id,
                "es_reingreso": (
                    tenia_membresia_previa
                ),
                "tenia_deudas_pendientes": (
                    advertencia[
                        "tiene_deudas_pendientes"
                    ]
                ),
                "cantidad_deudas_pendientes": (
                    advertencia[
                        "cantidad_deudas_pendientes"
                    ]
                ),
                "monto_total_pendiente": (
                    advertencia[
                        "monto_total_pendiente"
                    ]
                ),
                "confirmacion_del_creador": bool(
                    advertencia[
                        "tiene_deudas_pendientes"
                    ]
                    and confirmar_deudas
                ),
                "fecha_incorporacion": (
                    momento.isoformat()
                ),
            },
        )

        self.participantes.add(
            usuario
        )

        return membresia, advertencia, True

    @property
    def total_gastos(self):
        total = self.gastos.aggregate(
            total=models.Sum("monto")
        )["total"]

        return total or Decimal("0.00")


class GroupMembership(models.Model):
    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="membresias",
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="membresias_grupos",
    )

    fecha_ingreso = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )

    fecha_salida = models.DateTimeField(
        null=True,
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            "-fecha_ingreso",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "grupo",
                    "usuario",
                ],
                condition=models.Q(activo=True),
                name=(
                    "membresia_activa_unica_"
                    "por_grupo_usuario"
                ),
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        activo=True,
                        fecha_salida__isnull=True,
                    )
                    | models.Q(
                        activo=False,
                        fecha_salida__isnull=False,
                    )
                ),
                name=(
                    "membresia_estado_fecha_"
                    "salida_consistentes"
                ),
            ),
        ]

    def __str__(self):
        estado = (
            "Activo"
            if self.activo
            else "Retirado"
        )

        return (
            f"{self.usuario.username} - "
            f"{self.grupo.nombre} - "
            f"{estado}"
        )

    def retirar(self):
        if not self.activo:
            return

        self.activo = False
        self.fecha_salida = timezone.now()

        self.save(
            update_fields=[
                "activo",
                "fecha_salida",
            ]
        )


class DebtReviewAssignment(models.Model):
    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="asignaciones_responsable_deudas",
    )

    responsable = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="asignaciones_revision_deudas",
    )

    responsable_username = models.CharField(
        max_length=150,
    )

    asignado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="responsables_deudas_asignados",
    )

    asignado_por_username = models.CharField(
        max_length=150,
    )

    fecha_asignacion = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )

    fecha_fin = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    vigente = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            "-fecha_asignacion",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["grupo"],
                condition=models.Q(vigente=True),
                name=(
                    "responsable_deudas_vigente_"
                    "unico_por_grupo"
                ),
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        vigente=True,
                        fecha_fin__isnull=True,
                    )
                    | models.Q(
                        vigente=False,
                        fecha_fin__isnull=False,
                    )
                ),
                name=(
                    "responsable_deudas_vigencia_"
                    "fecha_consistentes"
                ),
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "grupo",
                    "vigente",
                ],
                name="resp_deuda_grupo_vig_idx",
            ),
            models.Index(
                fields=[
                    "responsable",
                    "vigente",
                ],
                name="resp_deuda_user_vig_idx",
            ),
        ]

    def __str__(self):
        estado = (
            "Vigente"
            if self.vigente
            else "Anterior"
        )

        return (
            f"{self.responsable_username} - "
            f"{self.grupo.nombre} - "
            f"{estado}"
        )

    def finalizar(
        self,
        momento=None,
    ):
        if not self.vigente:
            return False

        momento = momento or timezone.now()

        self.vigente = False
        self.fecha_fin = momento

        self.save(
            update_fields=[
                "vigente",
                "fecha_fin",
            ]
        )

        return True


class Expense(models.Model):
    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="gastos",
    )

    descripcion = models.CharField(
        max_length=150,
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01"),
                message="El monto debe ser mayor que cero.",
            )
        ],
    )

    participantes = models.ManyToManyField(
        User,
        related_name="gastos_compartidos",
    )

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="gastos_registrados",
    )

    fecha_gasto = models.DateField(
        default=timezone.localdate,
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-fecha_gasto",
            "-fecha_registro",
        ]

    def __str__(self):
        return (
            f"{self.descripcion} - "
            f"${self.monto}"
        )

    @transaction.atomic
    def sincronizar_integrantes_activos(self):
        integrantes_activos = (
            self.grupo.obtener_integrantes_activos()
        )

        self.participantes.set(
            integrantes_activos
        )

        return self.calcular_division_equitativa()

    @transaction.atomic
    def calcular_division_equitativa(self):
        participantes = list(
            self.participantes.all().order_by("id")
        )

        if not participantes:
            self.divisiones.all().delete()
            return []

        monto_centavos = int(
            (
                self.monto
                * Decimal("100")
            ).quantize(
                Decimal("1")
            )
        )

        cantidad_participantes = len(
            participantes
        )

        (
            monto_base_centavos,
            centavos_restantes,
        ) = divmod(
            monto_centavos,
            cantidad_participantes,
        )

        self.divisiones.all().delete()

        divisiones = []

        for indice, participante in enumerate(
            participantes
        ):
            centavos_asignados = (
                monto_base_centavos
            )

            if indice < centavos_restantes:
                centavos_asignados += 1

            monto_asignado = (
                Decimal(centavos_asignados)
                / Decimal("100")
            )

            divisiones.append(
                ExpenseDivision(
                    gasto=self,
                    participante=participante,
                    monto_asignado=monto_asignado,
                )
            )

        return ExpenseDivision.objects.bulk_create(
            divisiones
        )


class ExpenseDivision(models.Model):
    gasto = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="divisiones",
    )

    participante = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="divisiones_gastos",
    )

    monto_asignado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.00"),
            )
        ],
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "participante__username"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "gasto",
                    "participante",
                ],
                name=(
                    "division_unica_por_"
                    "gasto_participante"
                ),
            )
        ]

    def __str__(self):
        return (
            f"{self.participante.username} debe "
            f"${self.monto_asignado} en "
            f"{self.gasto.descripcion}"
        )


class Payment(models.Model):
    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="pagos",
    )

    pagador = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="pagos_realizados",
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01"),
                message=(
                    "El monto del pago debe ser "
                    "mayor que cero."
                ),
            )
        ],
    )

    fecha_pago = models.DateField(
        default=timezone.localdate,
    )

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="pagos_registrados",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-fecha_pago",
            "-fecha_registro",
        ]

    def __str__(self):
        return (
            f"{self.pagador.username} aportó "
            f"${self.monto} en "
            f"{self.grupo.nombre}"
        )


class ClosingBalance(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_SALDADO = "saldado"

    ESTADOS = [
        (
            ESTADO_PENDIENTE,
            "Pendiente",
        ),
        (
            ESTADO_SALDADO,
            "Saldado",
        ),
    ]

    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="saldos_cierre",
    )

    grupo_nombre = models.CharField(
        max_length=100,
    )

    participante = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="saldos_cierre_actividades",
    )

    participante_username = models.CharField(
        max_length=150,
    )

    cuota_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.00"),
            )
        ],
    )

    total_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.00"),
            )
        ],
    )

    saldo_pendiente = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.00"),
            )
        ],
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
    )

    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "participante_username",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "grupo",
                    "participante",
                ],
                name=(
                    "saldo_cierre_unico_por_"
                    "grupo_participante"
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(
                    cuota_total__gte=Decimal("0.00")
                ),
                name="saldo_cierre_cuota_no_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    total_pagado__gte=Decimal("0.00")
                ),
                name="saldo_cierre_pago_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    saldo_pendiente__gte=Decimal("0.00")
                ),
                name="saldo_cierre_pendiente_no_negativo",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "grupo",
                    "estado",
                ],
                name="saldo_grupo_estado_idx",
            ),
            models.Index(
                fields=[
                    "participante",
                    "estado",
                ],
                name="saldo_usuario_estado_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.participante_username} - "
            f"{self.grupo_nombre} - "
            f"${self.saldo_pendiente} - "
            f"{self.get_estado_display()}"
        )


class Debt(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_EN_REVISION = "en_revision"
    ESTADO_RESUELTA = "resuelta"
    ESTADO_RECHAZADA = "rechazada"

    ESTADOS = [
        (
            ESTADO_PENDIENTE,
            "Pendiente",
        ),
        (
            ESTADO_EN_REVISION,
            "En revisión",
        ),
        (
            ESTADO_RESUELTA,
            "Resuelta",
        ),
        (
            ESTADO_RECHAZADA,
            "Rechazada",
        ),
    ]

    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="deudas_generadas",
    )

    grupo_nombre = models.CharField(
        max_length=100,
    )

    saldo_cierre = models.OneToOneField(
        ClosingBalance,
        on_delete=models.PROTECT,
        related_name="deuda",
    )

    participante = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="deudas_actividades",
    )

    participante_username = models.CharField(
        max_length=150,
    )

    monto_original = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01"),
            )
        ],
    )

    saldo_pendiente = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.00"),
            )
        ],
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_PENDIENTE,
    )

    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
    )

    fecha_resolucion = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-fecha_generacion",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "grupo",
                    "participante",
                ],
                name=(
                    "deuda_unica_por_"
                    "grupo_participante"
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(
                    monto_original__gt=Decimal("0.00")
                ),
                name="deuda_monto_original_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    saldo_pendiente__gte=Decimal("0.00")
                ),
                name="deuda_saldo_no_negativo",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "participante",
                    "estado",
                    "-fecha_generacion",
                ],
                name="deuda_usuario_estado_idx",
            ),
            models.Index(
                fields=[
                    "grupo",
                    "estado",
                ],
                name="deuda_grupo_estado_idx",
            ),
        ]

    @classmethod
    def deudas_activas_usuario(
        cls,
        usuario,
    ):
        if not usuario or not usuario.pk:
            return cls.objects.none()

        return (
            cls.objects
            .filter(
                participante=usuario,
                saldo_pendiente__gt=Decimal("0.00"),
                estado__in=[
                    cls.ESTADO_PENDIENTE,
                    cls.ESTADO_EN_REVISION,
                    cls.ESTADO_RECHAZADA,
                ],
            )
            .select_related(
                "grupo",
                "participante",
                "saldo_cierre",
            )
            .order_by(
                "-fecha_generacion",
                "-id",
            )
        )

    @classmethod
    def resumen_deudas_activas_usuario(
        cls,
        usuario,
    ):
        deudas = cls.deudas_activas_usuario(
            usuario
        )

        monto_total = (
            deudas.aggregate(
                total=models.Sum(
                    "saldo_pendiente"
                )
            )["total"]
            or Decimal("0.00")
        ).quantize(
            Decimal("0.01")
        )

        return {
            "cantidad_deudas_pendientes": (
                deudas.count()
            ),
            "monto_total_pendiente": monto_total,
        }

    @property
    def esta_activa(self):
        return bool(
            self.saldo_pendiente
            > Decimal("0.00")
            and self.estado
            in [
                self.ESTADO_PENDIENTE,
                self.ESTADO_EN_REVISION,
                self.ESTADO_RECHAZADA,
            ]
        )

    @property
    def solicitud_pendiente_revision(self):
        if not self.pk:
            return None

        return (
            self.solicitudes_resolucion
            .filter(
                estado=(
                    DebtResolutionRequest
                    .ESTADO_PENDIENTE_REVISION
                )
            )
            .order_by(
                "-fecha_envio",
                "-id",
            )
            .first()
        )

    @property
    def tiene_solicitud_pendiente(self):
        return bool(
            self.solicitud_pendiente_revision
        )

    def obtener_solicitudes_ordenadas(self):
        if not self.pk:
            return (
                DebtResolutionRequest
                .objects.none()
            )

        return (
            self.solicitudes_resolucion
            .select_related(
                "grupo",
                "deuda",
                "solicitante",
                "revisado_por",
            )
            .order_by(
                "-fecha_envio",
                "-id",
            )
        )

    def __str__(self):
        return (
            f"{self.participante_username} debe "
            f"${self.saldo_pendiente} en "
            f"{self.grupo_nombre}"
        )


class DebtResolutionRequest(models.Model):
    ESTADO_PENDIENTE_REVISION = (
        "pendiente_revision"
    )
    ESTADO_APROBADA = "aprobada"
    ESTADO_RECHAZADA = "rechazada"

    ESTADOS = [
        (
            ESTADO_PENDIENTE_REVISION,
            "Pendiente de revisión",
        ),
        (
            ESTADO_APROBADA,
            "Aprobada",
        ),
        (
            ESTADO_RECHAZADA,
            "Rechazada",
        ),
    ]

    DECISION_APROBADA = "aprobada"
    DECISION_RECHAZADA = "rechazada"

    DECISIONES = [
        (
            DECISION_APROBADA,
            "Aprobada",
        ),
        (
            DECISION_RECHAZADA,
            "Rechazada",
        ),
    ]

    deuda = models.ForeignKey(
        Debt,
        on_delete=models.PROTECT,
        related_name="solicitudes_resolucion",
    )

    grupo = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name="solicitudes_resolucion_deudas",
    )

    grupo_nombre = models.CharField(
        max_length=100,
    )

    solicitante = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="solicitudes_resolucion_deudas",
    )

    solicitante_username = models.CharField(
        max_length=150,
    )

    descripcion = models.TextField()

    evidencia = models.FileField(
        upload_to=ruta_evidencia_resolucion,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "jpg",
                    "jpeg",
                    "png",
                ],
                message=(
                    "La evidencia debe estar en formato "
                    "PDF, JPG, JPEG o PNG."
                ),
            )
        ],
        blank=True,
    )

    evidencia_nombre_original = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    estado = models.CharField(
        max_length=25,
        choices=ESTADOS,
        default=ESTADO_PENDIENTE_REVISION,
    )

    decision = models.CharField(
        max_length=15,
        choices=DECISIONES,
        null=True,
        blank=True,
    )

    observacion_revision = models.TextField(
        blank=True,
        default="",
    )

    revisado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="solicitudes_deuda_revisadas",
        null=True,
        blank=True,
    )

    revisado_por_username = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    fecha_envio = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )

    fecha_revision = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-fecha_envio",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["deuda"],
                condition=models.Q(
                    estado="pendiente_revision"
                ),
                name=(
                    "solicitud_pendiente_"
                    "unica_por_deuda"
                ),
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        estado="pendiente_revision",
                        decision__isnull=True,
                        revisado_por__isnull=True,
                        fecha_revision__isnull=True,
                    )
                    | models.Q(
                        estado="aprobada",
                        decision="aprobada",
                        revisado_por__isnull=False,
                        fecha_revision__isnull=False,
                    )
                    | models.Q(
                        estado="rechazada",
                        decision="rechazada",
                        revisado_por__isnull=False,
                        fecha_revision__isnull=False,
                    )
                ),
                name=(
                    "solicitud_revision_"
                    "estado_consistente"
                ),
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "deuda",
                    "estado",
                    "-fecha_envio",
                ],
                name="sol_deuda_estado_fecha_idx",
            ),
            models.Index(
                fields=[
                    "solicitante",
                    "-fecha_envio",
                ],
                name="sol_user_fecha_idx",
            ),
            models.Index(
                fields=[
                    "grupo",
                    "estado",
                ],
                name="sol_grupo_estado_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Solicitud de "
            f"{self.solicitante_username} - "
            f"{self.grupo_nombre} - "
            f"{self.get_estado_display()}"
        )

    def clean(self):
        super().clean()

        errores = {}

        if (
            self.deuda_id
            and self.grupo_id
            and self.deuda.grupo_id
            != self.grupo_id
        ):
            errores["grupo"] = (
                "La actividad seleccionada no corresponde "
                "a la deuda."
            )

        if (
            self.deuda_id
            and self.solicitante_id
            and self.deuda.participante_id
            != self.solicitante_id
        ):
            errores["solicitante"] = (
                "Solo el titular de la deuda puede "
                "enviar una solicitud de resolución."
            )

        descripcion = (
            self.descripcion or ""
        ).strip()

        if not descripcion:
            errores["descripcion"] = (
                "La descripción o explicación "
                "es obligatoria."
            )

        if errores:
            raise ValidationError(
                errores
            )

        self.descripcion = descripcion

    @property
    def pendiente_revision(self):
        return (
            self.estado
            == self.ESTADO_PENDIENTE_REVISION
        )

    @property
    def puede_editarse(self):
        return self.pendiente_revision

    @classmethod
    @transaction.atomic
    def crear_para_deuda(
        cls,
        deuda,
        solicitante,
        descripcion,
        evidencia=None,
        momento=None,
    ):
        momento = momento or timezone.now()

        if not deuda or not deuda.pk:
            raise ValidationError({
                "deuda": (
                    "Debes seleccionar una deuda válida."
                )
            })

        if not solicitante or not solicitante.pk:
            raise ValidationError(
                (
                    "No se pudo identificar al usuario "
                    "que envía la solicitud."
                )
            )

        deuda_bloqueada = (
            Debt.objects
            .select_for_update()
            .select_related(
                "grupo",
                "participante",
            )
            .get(pk=deuda.pk)
        )

        if (
            deuda_bloqueada.participante_id
            != solicitante.id
        ):
            raise ValidationError({
                "deuda": (
                    "Solo puedes enviar solicitudes "
                    "sobre tus propias deudas."
                )
            })

        if (
            deuda_bloqueada.estado
            != Debt.ESTADO_PENDIENTE
            or deuda_bloqueada.saldo_pendiente
            <= Decimal("0.00")
        ):
            raise ValidationError({
                "deuda": (
                    "La deuda debe encontrarse pendiente "
                    "y mantener saldo para enviar "
                    "una solicitud."
                )
            })

        if not (descripcion or "").strip():
            raise ValidationError({
                "descripcion": (
                    "La descripción o explicación "
                    "es obligatoria."
                )
            })

        if cls.objects.filter(
            deuda=deuda_bloqueada,
            estado=cls.ESTADO_PENDIENTE_REVISION,
        ).exists():
            raise ValidationError({
                "deuda": (
                    "Ya existe una solicitud pendiente "
                    "de revisión para esta deuda."
                )
            })

        solicitud = cls(
            deuda=deuda_bloqueada,
            grupo=deuda_bloqueada.grupo,
            grupo_nombre=(
                deuda_bloqueada.grupo_nombre
            ),
            solicitante=solicitante,
            solicitante_username=(
                solicitante.username
            ),
            descripcion=descripcion.strip(),
            evidencia=evidencia,
            evidencia_nombre_original=(
                getattr(
                    evidencia,
                    "name",
                    "",
                )
            ),
            estado=cls.ESTADO_PENDIENTE_REVISION,
            fecha_envio=momento,
        )

        solicitud.full_clean()

        try:
            solicitud.save()

            ActivityHistory.registrar(
                grupo=deuda_bloqueada.grupo,
                usuario=solicitante,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_SOLICITUD_RESOLUCION_CREADA
                ),
                descripcion=(
                    f"{solicitante.username} envió una "
                    "solicitud de resolución para su deuda "
                    f'en la actividad '
                    f'"{deuda_bloqueada.grupo_nombre}".'
                ),
                datos={
                    "solicitud_id": solicitud.id,
                    "deuda_id": deuda_bloqueada.id,
                    "grupo_id": (
                        deuda_bloqueada.grupo_id
                    ),
                    "grupo_nombre": (
                        deuda_bloqueada.grupo_nombre
                    ),
                    "solicitante_id": solicitante.id,
                    "solicitante_username": (
                        solicitante.username
                    ),
                    "descripcion": (
                        solicitud.descripcion
                    ),
                    "evidencia_nombre_original": (
                        solicitud
                        .evidencia_nombre_original
                    ),
                    "estado": solicitud.estado,
                    "fecha_envio": (
                        momento.isoformat()
                    ),
                },
            )
        except Exception:
            try:
                if (
                    solicitud.evidencia
                    and solicitud.evidencia.name
                ):
                    (
                        solicitud.evidencia.storage
                        .delete(
                            solicitud.evidencia.name
                        )
                    )
            except Exception:
                pass

            raise

        return solicitud

    @transaction.atomic
    def revisar(
        self,
        responsable,
        decision,
        observacion,
        momento=None,
    ):
        momento = momento or timezone.now()

        if not self.pk:
            raise ValidationError({
                "solicitud": (
                    "La solicitud debe existir antes "
                    "de ser revisada."
                )
            })

        if not responsable or not responsable.pk:
            raise ValidationError({
                "responsable": (
                    "No se pudo identificar al usuario "
                    "responsable de la revisión."
                )
            })

        decision_normalizada = (
            decision or ""
        ).strip().lower()

        if decision_normalizada not in {
            self.DECISION_APROBADA,
            self.DECISION_RECHAZADA,
        }:
            raise ValidationError({
                "decision": (
                    "La decisión debe ser aprobada "
                    "o rechazada."
                )
            })

        observacion_normalizada = (
            observacion or ""
        ).strip()

        if not observacion_normalizada:
            raise ValidationError({
                "observacion": (
                    "La observación o justificación "
                    "de la decisión es obligatoria."
                )
            })

        solicitud_bloqueada = (
            DebtResolutionRequest.objects
            .select_for_update()
            .select_related(
                "grupo",
                "grupo__creador",
                "deuda",
                "deuda__participante",
                "deuda__saldo_cierre",
                "solicitante",
            )
            .get(pk=self.pk)
        )

        grupo = solicitud_bloqueada.grupo

        if not grupo.puede_revisar_solicitudes_deuda(
            responsable
        ):
            raise ValidationError({
                "responsable": (
                    "Solo el responsable vigente de la "
                    "actividad puede tomar esta decisión."
                )
            })

        if (
            solicitud_bloqueada.estado
            != self.ESTADO_PENDIENTE_REVISION
        ):
            raise ValidationError({
                "solicitud": (
                    "La solicitud ya fue revisada y no "
                    "puede decidirse nuevamente."
                )
            })

        deuda_bloqueada = (
            Debt.objects
            .select_for_update()
            .select_related(
                "grupo",
                "participante",
                "saldo_cierre",
            )
            .get(
                pk=solicitud_bloqueada.deuda_id
            )
        )

        if (
            deuda_bloqueada.grupo_id
            != solicitud_bloqueada.grupo_id
            or deuda_bloqueada.participante_id
            != solicitud_bloqueada.solicitante_id
        ):
            raise ValidationError({
                "solicitud": (
                    "La solicitud no coincide con la "
                    "deuda o el usuario solicitante."
                )
            })

        if (
            deuda_bloqueada.estado
            == Debt.ESTADO_RESUELTA
            or deuda_bloqueada.saldo_pendiente
            <= Decimal("0.00")
        ):
            raise ValidationError({
                "deuda": (
                    "La deuda ya se encuentra resuelta "
                    "y no admite otra decisión."
                )
            })

        resumen_antes = (
            Debt.resumen_deudas_activas_usuario(
                solicitud_bloqueada.solicitante
            )
        )

        deuda_antes = {
            "estado": deuda_bloqueada.estado,
            "monto_original": (
                f"{deuda_bloqueada.monto_original:.2f}"
            ),
            "saldo_pendiente": (
                f"{deuda_bloqueada.saldo_pendiente:.2f}"
            ),
            "fecha_resolucion": (
                deuda_bloqueada
                .fecha_resolucion
                .isoformat()
                if deuda_bloqueada.fecha_resolucion
                else None
            ),
        }

        saldo_bloqueado = (
            ClosingBalance.objects
            .select_for_update()
            .get(
                pk=deuda_bloqueada.saldo_cierre_id
            )
        )

        saldo_antes = {
            "estado": saldo_bloqueado.estado,
            "saldo_pendiente": (
                f"{saldo_bloqueado.saldo_pendiente:.2f}"
            ),
            "total_pagado": (
                f"{saldo_bloqueado.total_pagado:.2f}"
            ),
        }

        if (
            decision_normalizada
            == self.DECISION_APROBADA
        ):
            estado_solicitud = self.ESTADO_APROBADA

            deuda_bloqueada.estado = (
                Debt.ESTADO_RESUELTA
            )
            deuda_bloqueada.saldo_pendiente = (
                Decimal("0.00")
            )
            deuda_bloqueada.fecha_resolucion = momento

            deuda_bloqueada.save(
                update_fields=[
                    "estado",
                    "saldo_pendiente",
                    "fecha_resolucion",
                    "fecha_actualizacion",
                ]
            )

            saldo_bloqueado.estado = (
                ClosingBalance.ESTADO_SALDADO
            )
            saldo_bloqueado.saldo_pendiente = (
                Decimal("0.00")
            )

            saldo_bloqueado.save(
                update_fields=[
                    "estado",
                    "saldo_pendiente",
                ]
            )

            resultado_deuda = (
                "La deuda fue resuelta."
            )
        else:
            estado_solicitud = self.ESTADO_RECHAZADA

            deuda_bloqueada.estado = (
                Debt.ESTADO_PENDIENTE
            )
            deuda_bloqueada.fecha_resolucion = None

            deuda_bloqueada.save(
                update_fields=[
                    "estado",
                    "fecha_resolucion",
                    "fecha_actualizacion",
                ]
            )

            resultado_deuda = (
                "La deuda permanece pendiente."
            )

        solicitud_bloqueada.estado = (
            estado_solicitud
        )
        solicitud_bloqueada.decision = (
            decision_normalizada
        )
        solicitud_bloqueada.observacion_revision = (
            observacion_normalizada
        )
        solicitud_bloqueada.revisado_por = responsable
        solicitud_bloqueada.revisado_por_username = (
            responsable.username
        )
        solicitud_bloqueada.fecha_revision = momento

        solicitud_bloqueada.save(
            update_fields=[
                "estado",
                "decision",
                "observacion_revision",
                "revisado_por",
                "revisado_por_username",
                "fecha_revision",
                "fecha_actualizacion",
            ]
        )

        resumen_despues = (
            Debt.resumen_deudas_activas_usuario(
                solicitud_bloqueada.solicitante
            )
        )

        tipo_historial = (
            ActivityHistory
            .TIPO_SOLICITUD_RESOLUCION_APROBADA
            if decision_normalizada
            == self.DECISION_APROBADA
            else (
                ActivityHistory
                .TIPO_SOLICITUD_RESOLUCION_RECHAZADA
            )
        )

        ActivityHistory.registrar(
            grupo=grupo,
            usuario=responsable,
            tipo_accion=tipo_historial,
            descripcion=(
                f"{responsable.username} "
                f"{decision_normalizada} la solicitud "
                f"de resolución de "
                f"{solicitud_bloqueada.solicitante_username} "
                f'en la actividad '
                f'"{solicitud_bloqueada.grupo_nombre}".'
            ),
            datos={
                "solicitud_id": (
                    solicitud_bloqueada.id
                ),
                "deuda_id": deuda_bloqueada.id,
                "grupo_id": grupo.id,
                "grupo_nombre": (
                    solicitud_bloqueada.grupo_nombre
                ),
                "solicitante_id": (
                    solicitud_bloqueada.solicitante_id
                ),
                "solicitante_username": (
                    solicitud_bloqueada
                    .solicitante_username
                ),
                "responsable_id": responsable.id,
                "responsable_username": (
                    responsable.username
                ),
                "decision": decision_normalizada,
                "observacion": (
                    observacion_normalizada
                ),
                "fecha_revision": (
                    momento.isoformat()
                ),
                "deuda_antes": deuda_antes,
                "deuda_despues": {
                    "estado": (
                        deuda_bloqueada.estado
                    ),
                    "monto_original": (
                        f"{deuda_bloqueada.monto_original:.2f}"
                    ),
                    "saldo_pendiente": (
                        f"{deuda_bloqueada.saldo_pendiente:.2f}"
                    ),
                    "fecha_resolucion": (
                        deuda_bloqueada
                        .fecha_resolucion
                        .isoformat()
                        if deuda_bloqueada
                        .fecha_resolucion
                        else None
                    ),
                },
                "saldo_cierre_antes": saldo_antes,
                "saldo_cierre_despues": {
                    "estado": (
                        saldo_bloqueado.estado
                    ),
                    "saldo_pendiente": (
                        f"{saldo_bloqueado.saldo_pendiente:.2f}"
                    ),
                    "total_pagado": (
                        f"{saldo_bloqueado.total_pagado:.2f}"
                    ),
                },
                "advertencia_antes": {
                    "cantidad_deudas_pendientes": (
                        resumen_antes[
                            "cantidad_deudas_pendientes"
                        ]
                    ),
                    "monto_total_pendiente": (
                        f'{resumen_antes[
                            "monto_total_pendiente"
                        ]:.2f}'
                    ),
                },
                "advertencia_despues": {
                    "cantidad_deudas_pendientes": (
                        resumen_despues[
                            "cantidad_deudas_pendientes"
                        ]
                    ),
                    "monto_total_pendiente": (
                        f'{resumen_despues[
                            "monto_total_pendiente"
                        ]:.2f}'
                    ),
                },
            },
        )

        decision_texto = (
            "aprobada"
            if decision_normalizada
            == self.DECISION_APROBADA
            else "rechazada"
        )

        titulo_notificacion = (
            "Solicitud de deuda "
            f"{decision_texto}"
        )

        mensaje_notificacion = (
            f'Solicitud #{solicitud_bloqueada.id} '
            f'de la actividad '
            f'"{solicitud_bloqueada.grupo_nombre}" '
            f'fue {decision_texto}. '
            f'Deuda #{deuda_bloqueada.id}: '
            f'{resultado_deuda} '
            f'Observación: '
            f'{observacion_normalizada}'
        )

        notificacion = Notification.objects.create(
            usuario=(
                solicitud_bloqueada.solicitante
            ),
            titulo=titulo_notificacion,
            mensaje=mensaje_notificacion,
            enlace=(
                f"/mis-deudas/{deuda_bloqueada.id}/"
                f"solicitudes/"
                f"{solicitud_bloqueada.id}"
            ),
        )

        self.estado = solicitud_bloqueada.estado
        self.decision = solicitud_bloqueada.decision
        self.observacion_revision = (
            solicitud_bloqueada
            .observacion_revision
        )
        self.revisado_por = responsable
        self.revisado_por_username = (
            responsable.username
        )
        self.fecha_revision = momento

        return (
            solicitud_bloqueada,
            deuda_bloqueada,
            notificacion,
        )


class Notification(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )

    titulo = models.CharField(
        max_length=150,
    )

    mensaje = models.TextField()

    enlace = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    leida = models.BooleanField(
        default=False,
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
    )

    fecha_lectura = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-fecha_creacion",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "usuario",
                    "leida",
                    "-fecha_creacion",
                ],
                name="notif_usuario_estado_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        leida=False,
                        fecha_lectura__isnull=True,
                    )
                    | models.Q(
                        leida=True,
                        fecha_lectura__isnull=False,
                    )
                ),
                name="notificacion_lectura_fecha_consistente",
            ),
        ]

    def __str__(self):
        estado = (
            "Leída"
            if self.leida
            else "No leída"
        )

        return (
            f"{self.usuario.username} - "
            f"{self.titulo} - "
            f"{estado}"
        )

    def marcar_como_leida(self):
        if self.leida:
            return False

        self.leida = True
        self.fecha_lectura = timezone.now()

        self.save(
            update_fields=[
                "leida",
                "fecha_lectura",
            ]
        )

        return True


class ActivityHistory(models.Model):
    TIPO_ACTIVIDAD_CREADA = "actividad_creada"
    TIPO_ACTIVIDAD_ACTUALIZADA = "actividad_actualizada"
    TIPO_ACTIVIDAD_CERRADA_AUTOMATICAMENTE = (
        "actividad_cerrada_automaticamente"
    )
    TIPO_PARTICIPANTE_INGRESO = "participante_ingreso"
    TIPO_PARTICIPANTE_RETIRO = "participante_retiro"
    TIPO_PARTICIPANTE_REINGRESO = "participante_reingreso"
    TIPO_GASTO_CREADO = "gasto_creado"
    TIPO_GASTO_ACTUALIZADO = "gasto_actualizado"
    TIPO_GASTO_ELIMINADO = "gasto_eliminado"
    TIPO_PAGO_CREADO = "pago_creado"
    TIPO_RESPONSABLE_DEUDAS_ASIGNADO = (
        "responsable_deudas_asignado"
    )
    TIPO_RESPONSABLE_DEUDAS_CAMBIADO = (
        "responsable_deudas_cambiado"
    )
    TIPO_CASO_TODOS_DEBEN_DETECTADO = (
        "caso_todos_deben_detectado"
    )
    TIPO_SOLICITUD_RESOLUCION_CREADA = (
        "solicitud_resolucion_creada"
    )
    TIPO_SOLICITUD_RESOLUCION_APROBADA = (
        "solicitud_resolucion_aprobada"
    )
    TIPO_SOLICITUD_RESOLUCION_RECHAZADA = (
        "solicitud_resolucion_rechazada"
    )

    TIPOS_ACCION = [
        (
            TIPO_ACTIVIDAD_CREADA,
            "Actividad creada",
        ),
        (
            TIPO_ACTIVIDAD_ACTUALIZADA,
            "Actividad actualizada",
        ),
        (
            TIPO_ACTIVIDAD_CERRADA_AUTOMATICAMENTE,
            "Actividad cerrada automáticamente",
        ),
        (
            TIPO_PARTICIPANTE_INGRESO,
            "Participante agregado",
        ),
        (
            TIPO_PARTICIPANTE_RETIRO,
            "Participante retirado",
        ),
        (
            TIPO_PARTICIPANTE_REINGRESO,
            "Participante reingresado",
        ),
        (
            TIPO_GASTO_CREADO,
            "Gasto creado",
        ),
        (
            TIPO_GASTO_ACTUALIZADO,
            "Gasto actualizado",
        ),
        (
            TIPO_GASTO_ELIMINADO,
            "Gasto eliminado",
        ),
        (
            TIPO_PAGO_CREADO,
            "Pago creado",
        ),
        (
            TIPO_RESPONSABLE_DEUDAS_ASIGNADO,
            "Responsable de deudas asignado",
        ),
        (
            TIPO_RESPONSABLE_DEUDAS_CAMBIADO,
            "Responsable de deudas cambiado",
        ),
        (
            TIPO_CASO_TODOS_DEBEN_DETECTADO,
            "Caso excepcional: todos deben",
        ),
        (
            TIPO_SOLICITUD_RESOLUCION_CREADA,
            "Solicitud de resolución creada",
        ),
        (
            TIPO_SOLICITUD_RESOLUCION_APROBADA,
            "Solicitud de resolución aprobada",
        ),
        (
            TIPO_SOLICITUD_RESOLUCION_RECHAZADA,
            "Solicitud de resolución rechazada",
        ),
    ]

    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="historial",
    )

    grupo_nombre = models.CharField(
        max_length=100,
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_historial",
    )

    usuario_username = models.CharField(
        max_length=150,
    )

    tipo_accion = models.CharField(
        max_length=40,
        choices=TIPOS_ACCION,
    )

    descripcion = models.TextField()

    datos = models.JSONField(
        default=dict,
        blank=True,
    )

    fecha_evento = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-fecha_evento",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "grupo",
                    "-fecha_evento",
                ],
                name="hist_grupo_fecha_idx",
            ),
            models.Index(
                fields=[
                    "grupo",
                    "tipo_accion",
                    "-fecha_evento",
                ],
                name="hist_grupo_tipo_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.grupo_nombre} - "
            f"{self.get_tipo_accion_display()} - "
            f"{self.usuario_username}"
        )

    @classmethod
    def registrar(
        cls,
        grupo,
        usuario,
        tipo_accion,
        descripcion,
        datos=None,
    ):
        return cls.objects.create(
            grupo=grupo,
            grupo_nombre=grupo.nombre,
            usuario=usuario,
            usuario_username=(
                usuario.username
                if usuario
                else "sistema"
            ),
            tipo_accion=tipo_accion,
            descripcion=descripcion,
            datos=datos or {},
        )