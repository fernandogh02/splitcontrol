from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


class Group(models.Model):
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

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre


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

    pagado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="gastos_pagados",
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
        ordering = ["-fecha_gasto", "-fecha_registro"]

    def __str__(self):
        return f"{self.descripcion} - ${self.monto}"

    @transaction.atomic
    def calcular_division_equitativa(self):
        participantes = list(
            self.participantes.all().order_by("id")
        )

        if not participantes:
            self.divisiones.all().delete()
            return []

        monto_centavos = int(
            (self.monto * Decimal("100")).quantize(
                Decimal("1")
            )
        )

        cantidad_participantes = len(participantes)

        monto_base_centavos, centavos_restantes = divmod(
            monto_centavos,
            cantidad_participantes,
        )

        self.divisiones.all().delete()

        divisiones = []

        for indice, participante in enumerate(participantes):
            centavos_asignados = monto_base_centavos

            if indice < centavos_restantes:
                centavos_asignados += 1

            monto_asignado = (
                Decimal(centavos_asignados) / Decimal("100")
            )

            divisiones.append(
                ExpenseDivision(
                    gasto=self,
                    participante=participante,
                    monto_asignado=monto_asignado,
                )
            )

        return ExpenseDivision.objects.bulk_create(divisiones)


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
        ordering = ["participante__username"]

        constraints = [
            models.UniqueConstraint(
                fields=["gasto", "participante"],
                name="division_unica_por_gasto_participante",
            )
        ]

    def __str__(self):
        return (
            f"{self.participante.username} debe "
            f"${self.monto_asignado} en {self.gasto.descripcion}"
        )