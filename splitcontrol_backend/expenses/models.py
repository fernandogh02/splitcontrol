from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


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
            },
        )

        self.fecha_cierre_automatico = (
            grupo_bloqueado.fecha_cierre_automatico
        )

        return True

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