from rest_framework import serializers
from .models import Group


class GroupSerializer(serializers.ModelSerializer):
    creador_username = serializers.CharField(
        source="creador.username",
        read_only=True
    )

    class Meta:
        model = Group
        fields = [
            "id",
            "nombre",
            "descripcion",
            "creador_username",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id",
            "creador_username",
            "fecha_creacion",
        ]