from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from .models import (
    ActivityHistory,
    Expense,
    ExpenseDivision,
    Group,
    GroupMembership,
    Notification,
    Payment,
)


CERO = Decimal("0.00")
DOS_DECIMALES = Decimal("0.01")


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
        nombre = (
            f"{obj.first_name} {obj.last_name}"
        ).strip()

        return nombre if nombre else obj.username


class GroupMembershipSerializer(
    serializers.ModelSerializer
):
    grupo_id = serializers.IntegerField(
        source="grupo.id",
        read_only=True,
    )

    grupo_nombre = serializers.CharField(
        source="grupo.nombre",
        read_only=True,
    )

    usuario = UserSimpleSerializer(
        read_only=True,
    )

    estado = serializers.SerializerMethodField()

    class Meta:
        model = GroupMembership
        fields = [
            "id",
            "grupo_id",
            "grupo_nombre",
            "usuario",
            "fecha_ingreso",
            "fecha_salida",
            "activo",
            "estado",
        ]

        read_only_fields = fields

    def get_estado(self, obj):
        return (
            "activo"
            if obj.activo
            else "retirado"
        )


class GroupSerializer(serializers.ModelSerializer):
    creador_username = serializers.CharField(
        source="creador.username",
        read_only=True,
    )

    participantes = UserSimpleSerializer(
        many=True,
        read_only=True,
    )

    estado = serializers.CharField(
        read_only=True,
    )

    total_gastos = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    fecha_inicio = serializers.DateTimeField(
        required=False,
        allow_null=False,
    )

    fecha_fin = serializers.DateTimeField(
        required=False,
        allow_null=False,
    )

    class Meta:
        model = Group
        fields = [
            "id",
            "nombre",
            "descripcion",
            "creador_username",
            "participantes",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "total_gastos",
            "fecha_creacion",
        ]

        read_only_fields = [
            "id",
            "creador_username",
            "participantes",
            "estado",
            "total_gastos",
            "fecha_creacion",
        ]

    def validate_nombre(self, value):
        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError(
                "El nombre de la actividad es obligatorio."
            )

        return nombre

    def validate(self, attrs):
        fecha_inicio = attrs.get(
            "fecha_inicio",
            getattr(
                self.instance,
                "fecha_inicio",
                None,
            ),
        )

        fecha_fin = attrs.get(
            "fecha_fin",
            getattr(
                self.instance,
                "fecha_fin",
                None,
            ),
        )

        if self.instance is None:
            errores = {}

            if not fecha_inicio:
                errores["fecha_inicio"] = (
                    "Debes establecer la fecha y hora "
                    "de inicio."
                )

            if not fecha_fin:
                errores["fecha_fin"] = (
                    "Debes establecer la fecha y hora "
                    "de finalización."
                )

            if errores:
                raise serializers.ValidationError(
                    errores
                )

        if fecha_inicio and not fecha_fin:
            raise serializers.ValidationError({
                "fecha_fin": (
                    "Debes establecer la fecha y hora "
                    "de finalización."
                )
            })

        if fecha_fin and not fecha_inicio:
            raise serializers.ValidationError({
                "fecha_inicio": (
                    "Debes establecer la fecha y hora "
                    "de inicio."
                )
            })

        if (
            fecha_inicio
            and fecha_fin
            and fecha_fin <= fecha_inicio
        ):
            raise serializers.ValidationError({
                "fecha_fin": (
                    "La fecha y hora de finalización "
                    "debe ser posterior a la fecha "
                    "y hora de inicio."
                )
            })

        return attrs


class ExpenseDivisionSerializer(
    serializers.ModelSerializer
):
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
    fecha_gasto = serializers.DateField(
        required=True,
    )

    participantes = UserSimpleSerializer(
        many=True,
        read_only=True,
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
            "participantes",
            "divisiones",
            "registrado_por",
            "fecha_registro",
        ]

        read_only_fields = [
            "id",
            "grupo",
            "participantes",
            "divisiones",
            "registrado_por",
            "fecha_registro",
        ]

    def validate_descripcion(self, value):
        descripcion = value.strip()

        if not descripcion:
            raise serializers.ValidationError(
                "La descripción del gasto "
                "es obligatoria."
            )

        return descripcion

    def validate(self, attrs):
        grupo = self.context.get("grupo")

        if not grupo:
            raise serializers.ValidationError(
                "No se pudo identificar el grupo."
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        gasto = super().create(
            validated_data
        )

        gasto.sincronizar_integrantes_activos()

        return gasto

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        gasto = super().update(
            instance,
            validated_data,
        )

        gasto.calcular_division_equitativa()

        return gasto


class PaymentSerializer(
    serializers.ModelSerializer
):
    pagador = UserSimpleSerializer(
        read_only=True,
    )

    pagador_id = serializers.IntegerField(
        source="pagador.id",
        read_only=True,
    )

    registrado_por = UserSimpleSerializer(
        read_only=True,
    )

    fecha_pago = serializers.DateField(
        required=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "grupo",
            "pagador",
            "pagador_id",
            "monto",
            "fecha_pago",
            "registrado_por",
            "fecha_registro",
        ]

        read_only_fields = [
            "id",
            "grupo",
            "pagador",
            "pagador_id",
            "registrado_por",
            "fecha_registro",
        ]

    def validate(self, attrs):
        grupo = self.context.get("grupo")
        request = self.context.get("request")

        pagador = (
            request.user
            if request
            and request.user.is_authenticated
            else None
        )

        if not grupo:
            raise serializers.ValidationError(
                "No se pudo identificar el grupo."
            )

        if not pagador:
            raise serializers.ValidationError(
                "No se pudo identificar al usuario "
                "que realiza el pago."
            )

        membresia_activa = (
            GroupMembership.objects
            .filter(
                grupo=grupo,
                usuario=pagador,
                activo=True,
            )
            .exists()
        )

        if not membresia_activa:
            raise serializers.ValidationError({
                "pagador": (
                    "Solo un participante activo puede "
                    "registrar su propio pago."
                )
            })

        cuota_total = (
            ExpenseDivision.objects
            .filter(
                gasto__grupo=grupo,
                participante=pagador,
            )
            .aggregate(
                total=Sum("monto_asignado")
            )["total"]
            or CERO
        ).quantize(DOS_DECIMALES)

        total_aportado = (
            Payment.objects
            .filter(
                grupo=grupo,
                pagador=pagador,
            )
            .aggregate(
                total=Sum("monto")
            )["total"]
            or CERO
        ).quantize(DOS_DECIMALES)

        saldo_pendiente = max(
            cuota_total - total_aportado,
            CERO,
        ).quantize(DOS_DECIMALES)

        if saldo_pendiente == CERO:
            raise serializers.ValidationError({
                "monto": (
                    "Tu cuota ya se encuentra saldada."
                )
            })

        monto = attrs.get(
            "monto",
            CERO,
        ).quantize(DOS_DECIMALES)

        if monto > saldo_pendiente:
            raise serializers.ValidationError({
                "monto": (
                    "El monto del pago no puede superar "
                    f"tu saldo pendiente de "
                    f"${saldo_pendiente:.2f}."
                )
            })

        return attrs


class ActivityHistorySerializer(
    serializers.ModelSerializer
):
    grupo_id = serializers.IntegerField(
        source="grupo.id",
        read_only=True,
    )

    tipo_accion_display = serializers.CharField(
        source="get_tipo_accion_display",
        read_only=True,
    )

    class Meta:
        model = ActivityHistory
        fields = [
            "id",
            "grupo_id",
            "grupo_nombre",
            "usuario",
            "usuario_username",
            "tipo_accion",
            "tipo_accion_display",
            "descripcion",
            "datos",
            "fecha_evento",
        ]

        read_only_fields = fields


class NotificationSerializer(
    serializers.ModelSerializer
):
    usuario = UserSimpleSerializer(
        read_only=True,
    )

    estado = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "usuario",
            "titulo",
            "mensaje",
            "enlace",
            "leida",
            "estado",
            "fecha_creacion",
            "fecha_lectura",
        ]

        read_only_fields = fields

    def get_estado(self, obj):
        return (
            "leida"
            if obj.leida
            else "no_leida"
        )