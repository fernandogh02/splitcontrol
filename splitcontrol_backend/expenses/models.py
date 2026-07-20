from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Group(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    creador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="grupos_creados"
    )

    participantes = models.ManyToManyField(
        User,
        related_name="grupos_participante",
        blank=True
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
        related_name="gastos"
    )

    descripcion = models.CharField(
        max_length=150
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.01"),
                message="El monto debe ser mayor que cero."
            )
        ]
    )

    pagado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="gastos_pagados"
    )

    participantes = models.ManyToManyField(
        User,
        related_name="gastos_compartidos"
    )

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="gastos_registrados"
    )

    fecha_gasto = models.DateField(
        default=timezone.localdate
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-fecha_gasto", "-fecha_registro"]

    def __str__(self):
        return f"{self.descripcion} - ${self.monto}"