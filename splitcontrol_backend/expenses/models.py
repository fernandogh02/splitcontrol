from django.db import models
from django.contrib.auth.models import User


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