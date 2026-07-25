from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from .models import (
    Expense,
    ExpenseDivision,
    Group,
    Payment,
)


class UserSimpleSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "nombre_completo",
        ]

    def get_nombre_completo(self, obj):
        nombre = f"{obj.first_name} {obj.last_name}".strip()

        return nombre if nombre else obj.username


class GroupSerializer(serializers.ModelSerializer):
    creador_username = serializers.CharField(
        source="creador.username",
        read_only=True,
    )

    participantes = UserSimpleSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Group
        fields = [
            "id",
            "nombre",
            "descripcion",
            "creador_username",
            "participantes",
            "fecha_creacion",
        ]

        read_only_fields = [
            "id",
            "creador_username",
            "participantes",
            "fecha_creacion",
        ]


class ExpenseDivisionSerializer(serializers.ModelSerializer):
    participante = UserSimpleSerializer(
        read_only=True,
    )

    class Meta:
        model = ExpenseDivision
        fields = [
            "id",
            "participante",
            "monto_asignado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

        read_only_fields = fields


class ExpenseSerializer(serializers.ModelSerializer):
    pagado_por = UserSimpleSerializer(
        read_only=True,
    )

    pagado_por_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="pagado_por",
        write_only=True,
    )

    participantes = UserSimpleSerializer(
        many=True,
        read_only=True,
    )

    participantes_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="participantes",
        many=True,
        write_only=True,
    )

    divisiones = ExpenseDivisionSerializer(
        many=True,
        read_only=True,
    )

    registrado_por = UserSimpleSerializer(
        read_only=True,
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "grupo",
            "descripcion",
            "monto",
            "fecha_gasto",
            "pagado_por",
            "pagado_por_id",
            "participantes",
            "participantes_ids",
            "divisiones",
            "registrado_por",
            "fecha_registro",
        ]

        read_only_fields = [
            "id",
            "grupo",
            "pagado_por",
            "participantes",
            "divisiones",
            "registrado_por",
            "fecha_registro",
        ]

    def validate_descripcion(self, value):
        descripcion = value.strip()

        if not descripcion:
            raise serializers.ValidationError(
                "La descripción del gasto es obligatoria."
            )

        return descripcion

    def validate_participantes_ids(self, participantes):
        if not participantes:
            raise serializers.ValidationError(
                "Debe seleccionar al menos un participante."
            )

        participantes_sin_repetir = []

        for participante in participantes:
            if participante not in participantes_sin_repetir:
                participantes_sin_repetir.append(participante)

        return participantes_sin_repetir

    def validate(self, attrs):
        grupo = self.context.get("grupo")

        pagado_por = attrs.get(
            "pagado_por",
            getattr(self.instance, "pagado_por", None),
        )

        participantes = attrs.get("participantes")

        if participantes is None:
            if self.instance:
                participantes = list(
                    self.instance.participantes.all()
                )
            else:
                participantes = []

        if not grupo:
            raise serializers.ValidationError(
                "No se pudo identificar el grupo."
            )

        if not pagado_por:
            raise serializers.ValidationError({
                "pagado_por_id": (
                    "Debe seleccionar quién pagó el gasto."
                )
            })

        if not grupo.participantes.filter(
            id=pagado_por.id
        ).exists():
            raise serializers.ValidationError({
                "pagado_por_id": (
                    "La persona que pagó debe pertenecer al grupo."
                )
            })

        if not participantes:
            raise serializers.ValidationError({
                "participantes_ids": (
                    "Debe seleccionar al menos un participante."
                )
            })

        participantes_invalidos = [
            participante.id
            for participante in participantes
            if not grupo.participantes.filter(
                id=participante.id
            ).exists()
        ]

        if participantes_invalidos:
            raise serializers.ValidationError({
                "participantes_ids": (
                    "Todos los participantes seleccionados "
                    "deben pertenecer al grupo."
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        gasto = super().create(validated_data)

        gasto.calcular_division_equitativa()

        return gasto

    @transaction.atomic
    def update(self, instance, validated_data):
        gasto = super().update(
            instance,
            validated_data,
        )

        gasto.calcular_division_equitativa()

        return gasto


class PaymentSerializer(serializers.ModelSerializer):
    pagador = UserSimpleSerializer(
        read_only=True,
    )

    pagador_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="pagador",
        write_only=True,
    )

    receptor = UserSimpleSerializer(
        read_only=True,
    )

    receptor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="receptor",
        write_only=True,
    )

    registrado_por = UserSimpleSerializer(
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "grupo",
            "pagador",
            "pagador_id",
            "receptor",
            "receptor_id",
            "monto",
            "fecha_pago",
            "registrado_por",
            "fecha_registro",
        ]

        read_only_fields = [
            "id",
            "grupo",
            "pagador",
            "receptor",
            "registrado_por",
            "fecha_registro",
        ]

    def validate(self, attrs):
        grupo = self.context.get("grupo")

        pagador = attrs.get(
            "pagador",
            getattr(self.instance, "pagador", None),
        )

        receptor = attrs.get(
            "receptor",
            getattr(self.instance, "receptor", None),
        )

        if not grupo:
            raise serializers.ValidationError(
                "No se pudo identificar el grupo."
            )

        if not pagador:
            raise serializers.ValidationError({
                "pagador_id": (
                    "Debe seleccionar quién realiza el pago."
                )
            })

        if not receptor:
            raise serializers.ValidationError({
                "receptor_id": (
                    "Debe seleccionar quién recibe el pago."
                )
            })

        if pagador.id == receptor.id:
            raise serializers.ValidationError({
                "receptor_id": (
                    "El pagador y el receptor deben ser "
                    "personas diferentes."
                )
            })

        if not grupo.participantes.filter(
            id=pagador.id
        ).exists():
            raise serializers.ValidationError({
                "pagador_id": (
                    "La persona que paga debe pertenecer al grupo."
                )
            })

        if not grupo.participantes.filter(
            id=receptor.id
        ).exists():
            raise serializers.ValidationError({
                "receptor_id": (
                    "La persona que recibe debe pertenecer al grupo."
                )
            })

        return attrs