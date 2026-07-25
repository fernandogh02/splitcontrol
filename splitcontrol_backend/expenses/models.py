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

        fecha_actual = timezone.now()

        if fecha_actual < self.fecha_inicio:
            return self.ESTADO_PROGRAMADA

        if fecha_actual <= self.fecha_fin:
            return self.ESTADO_ACTIVA

        return self.ESTADO_CERRADA

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

    receptor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="pagos_recibidos",
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

        constraints = [
            models.CheckConstraint(
                condition=~models.Q(
                    pagador=models.F(
                        "receptor"
                    )
                ),
                name=(
                    "pago_pagador_receptor_"
                    "diferentes"
                ),
            )
        ]

    def __str__(self):
        return (
            f"{self.pagador.username} pagó "
            f"${self.monto} a "
            f"{self.receptor.username}"
        )