from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from .models import (
    ActivityHistory,
    ClosingBalance,
    Debt,
    DebtResolutionRequest,
    DebtReviewAssignment,
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


class DebtReviewAssignmentSerializer(
    serializers.ModelSerializer
):
    grupo_id = serializers.IntegerField(
        source="grupo.id",
        read_only=True,
    )

    responsable = UserSimpleSerializer(
        read_only=True,
    )

    responsable_id = serializers.IntegerField(
        source="responsable.id",
        read_only=True,
    )

    asignado_por = UserSimpleSerializer(
        read_only=True,
    )

    asignado_por_id = serializers.IntegerField(
        source="asignado_por.id",
        read_only=True,
    )

    estado = serializers.SerializerMethodField()

    class Meta:
        model = DebtReviewAssignment
        fields = [
            "id",
            "grupo_id",
            "responsable",
            "responsable_id",
            "responsable_username",
            "asignado_por",
            "asignado_por_id",
            "asignado_por_username",
            "fecha_asignacion",
            "fecha_fin",
            "vigente",
            "estado",
        ]

        read_only_fields = fields

    def get_estado(self, obj):
        return (
            "vigente"
            if obj.vigente
            else "anterior"
        )


class DebtReviewAssignmentRequestSerializer(
    serializers.Serializer
):
    responsable_id = serializers.IntegerField(
        required=True,
        min_value=1,
    )

    def validate_responsable_id(self, value):
        if not User.objects.filter(
            id=value
        ).exists():
            raise serializers.ValidationError(
                "El usuario seleccionado no existe."
            )

        return value



class ParticipantDebtWarningRequestSerializer(
    serializers.Serializer
):
    usuario_id = serializers.IntegerField(
        required=True,
        min_value=1,
    )

    def validate_usuario_id(self, value):
        if not User.objects.filter(
            id=value
        ).exists():
            raise serializers.ValidationError(
                "El usuario seleccionado no existe."
            )

        return value


class ParticipantIncorporationSerializer(
    serializers.Serializer
):
    usuario_id = serializers.IntegerField(
        required=True,
        min_value=1,
    )

    confirmar_deudas = serializers.BooleanField(
        required=False,
        default=False,
    )

    def validate_usuario_id(self, value):
        if not User.objects.filter(
            id=value
        ).exists():
            raise serializers.ValidationError(
                "El usuario seleccionado no existe."
            )

        return value


class ParticipantDebtWarningSerializer(
    serializers.Serializer
):
    usuario = serializers.DictField(
        read_only=True,
    )

    tiene_deudas_pendientes = serializers.BooleanField(
        read_only=True,
    )

    requiere_confirmacion = serializers.BooleanField(
        read_only=True,
    )

    cantidad_deudas_pendientes = serializers.IntegerField(
        read_only=True,
    )

    monto_total_pendiente = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    mensaje = serializers.CharField(
        read_only=True,
    )


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

    responsable_deudas = serializers.SerializerMethodField()

    asignacion_responsable_deudas = (
        serializers.SerializerMethodField()
    )

    mensaje_responsable_deudas = serializers.CharField(
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
            "responsable_deudas",
            "asignacion_responsable_deudas",
            "mensaje_responsable_deudas",
            "fecha_inicio",
            "fecha_fin",
            "fecha_cierre_automatico",
            "fecha_generacion_saldos",
            "caso_excepcional_todos_deben",
            "fecha_deteccion_todos_deben",
            "mensaje_caso_todos_deben",
            "estado",
            "total_gastos",
            "fecha_creacion",
        ]

        read_only_fields = [
            "id",
            "creador_username",
            "participantes",
            "responsable_deudas",
            "asignacion_responsable_deudas",
            "mensaje_responsable_deudas",
            "fecha_cierre_automatico",
            "fecha_generacion_saldos",
            "caso_excepcional_todos_deben",
            "fecha_deteccion_todos_deben",
            "mensaje_caso_todos_deben",
            "estado",
            "total_gastos",
            "fecha_creacion",
        ]

    def get_responsable_deudas(self, obj):
        responsable = obj.responsable_deudas

        if not responsable:
            return None

        return UserSimpleSerializer(
            responsable,
            context=self.context,
        ).data

    def get_asignacion_responsable_deudas(
        self,
        obj,
    ):
        asignacion = (
            obj.asignacion_responsable_deudas_vigente
        )

        if not asignacion:
            return None

        return DebtReviewAssignmentSerializer(
            asignacion,
            context=self.context,
        ).data

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


class ClosingBalanceSerializer(
    serializers.ModelSerializer
):
    grupo_id = serializers.IntegerField(
        source="grupo.id",
        read_only=True,
    )

    participante = UserSimpleSerializer(
        read_only=True,
    )

    participante_id = serializers.IntegerField(
        source="participante.id",
        read_only=True,
    )

    estado_display = serializers.CharField(
        source="get_estado_display",
        read_only=True,
    )

    cuota_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    total_pagado = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    saldo_pendiente = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    tiene_deuda = serializers.SerializerMethodField()

    es_saldo_propio = serializers.SerializerMethodField()

    class Meta:
        model = ClosingBalance
        fields = [
            "id",
            "grupo_id",
            "grupo_nombre",
            "participante",
            "participante_id",
            "participante_username",
            "cuota_total",
            "total_pagado",
            "saldo_pendiente",
            "estado",
            "estado_display",
            "tiene_deuda",
            "es_saldo_propio",
            "fecha_generacion",
        ]

        read_only_fields = fields

    def get_tiene_deuda(self, obj):
        return hasattr(
            obj,
            "deuda",
        )

    def get_es_saldo_propio(self, obj):
        request = self.context.get("request")

        return bool(
            request
            and request.user.is_authenticated
            and request.user.id == obj.participante_id
        )



class DebtResolutionRequestSerializer(
    serializers.ModelSerializer
):
    deuda_id = serializers.IntegerField(
        source="deuda.id",
        read_only=True,
    )

    grupo_id = serializers.IntegerField(
        source="grupo.id",
        read_only=True,
    )

    actividad = serializers.SerializerMethodField()

    deuda = serializers.SerializerMethodField()

    solicitante = UserSimpleSerializer(
        read_only=True,
    )

    solicitante_id = serializers.IntegerField(
        source="solicitante.id",
        read_only=True,
    )

    revisado_por = UserSimpleSerializer(
        read_only=True,
    )

    estado_display = serializers.CharField(
        source="get_estado_display",
        read_only=True,
    )

    decision_display = serializers.CharField(
        source="get_decision_display",
        read_only=True,
    )

    evidencia = serializers.FileField(
        read_only=True,
    )

    pendiente_revision = serializers.BooleanField(
        read_only=True,
    )

    puede_editarse = serializers.BooleanField(
        read_only=True,
    )

    puede_revisar = serializers.SerializerMethodField()

    resultado_deuda = serializers.SerializerMethodField()

    class Meta:
        model = DebtResolutionRequest
        fields = [
            "id",
            "deuda_id",
            "grupo_id",
            "grupo_nombre",
            "actividad",
            "deuda",
            "solicitante",
            "solicitante_id",
            "solicitante_username",
            "descripcion",
            "evidencia",
            "evidencia_nombre_original",
            "estado",
            "estado_display",
            "decision",
            "decision_display",
            "observacion_revision",
            "revisado_por",
            "revisado_por_username",
            "fecha_envio",
            "fecha_revision",
            "fecha_actualizacion",
            "pendiente_revision",
            "puede_editarse",
            "puede_revisar",
            "resultado_deuda",
        ]

        read_only_fields = fields

    def get_actividad(self, obj):
        return {
            "id": obj.grupo_id,
            "nombre": obj.grupo_nombre,
            "estado": obj.grupo.estado,
            "fecha_cierre": (
                obj.grupo.fecha_cierre_automatico
            ),
        }

    def get_deuda(self, obj):
        return {
            "id": obj.deuda_id,
            "participante": (
                UserSimpleSerializer(
                    obj.deuda.participante,
                    context=self.context,
                ).data
            ),
            "participante_username": (
                obj.deuda.participante_username
            ),
            "monto_original": (
                f"{obj.deuda.monto_original:.2f}"
            ),
            "saldo_pendiente": (
                f"{obj.deuda.saldo_pendiente:.2f}"
            ),
            "estado": obj.deuda.estado,
            "estado_display": (
                obj.deuda.get_estado_display()
            ),
            "fecha_generacion": (
                obj.deuda.fecha_generacion
            ),
            "fecha_resolucion": (
                obj.deuda.fecha_resolucion
            ),
        }

    def get_puede_revisar(self, obj):
        request = self.context.get("request")

        return bool(
            request
            and request.user.is_authenticated
            and obj.pendiente_revision
            and obj.grupo
            .puede_revisar_solicitudes_deuda(
                request.user
            )
        )

    def get_resultado_deuda(self, obj):
        if (
            obj.estado
            == DebtResolutionRequest.ESTADO_APROBADA
        ):
            return (
                "La deuda fue resuelta."
            )

        if (
            obj.estado
            == DebtResolutionRequest.ESTADO_RECHAZADA
        ):
            return (
                "La deuda permanece pendiente."
            )

        return (
            "La solicitud está pendiente de revisión."
        )


class DebtResolutionRequestCreateSerializer(
    serializers.Serializer
):
    descripcion = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=2000,
    )

    evidencia = serializers.FileField(
        required=True,
        allow_empty_file=False,
    )

    FORMATOS_ADMITIDOS = {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
    }

    def validate_descripcion(self, value):
        descripcion = value.strip()

        if not descripcion:
            raise serializers.ValidationError(
                "La descripción o explicación es obligatoria."
            )

        return descripcion

    def validate_evidencia(self, value):
        extension = Path(
            value.name
        ).suffix.lower()

        if extension not in self.FORMATOS_ADMITIDOS:
            raise serializers.ValidationError(
                (
                    "La evidencia debe estar en formato "
                    "PDF, JPG, JPEG o PNG."
                )
            )

        return value

    def validate(self, attrs):
        deuda = self.context.get("deuda")
        request = self.context.get("request")

        usuario = (
            request.user
            if request
            and request.user.is_authenticated
            else None
        )

        if not deuda:
            raise serializers.ValidationError({
                "deuda": (
                    "No se pudo identificar la deuda."
                )
            })

        if not usuario:
            raise serializers.ValidationError({
                "usuario": (
                    "No se pudo identificar al usuario "
                    "que envía la solicitud."
                )
            })

        if deuda.participante_id != usuario.id:
            raise serializers.ValidationError({
                "deuda": (
                    "Solo puedes enviar solicitudes "
                    "sobre tus propias deudas."
                )
            })

        if (
            deuda.estado != Debt.ESTADO_PENDIENTE
            or deuda.saldo_pendiente <= CERO
        ):
            raise serializers.ValidationError({
                "deuda": (
                    "La deuda debe encontrarse pendiente "
                    "y mantener saldo para enviar "
                    "una solicitud."
                )
            })

        if DebtResolutionRequest.objects.filter(
            deuda=deuda,
            estado=(
                DebtResolutionRequest
                .ESTADO_PENDIENTE_REVISION
            ),
        ).exists():
            raise serializers.ValidationError({
                "deuda": (
                    "Ya existe una solicitud pendiente "
                    "de revisión para esta deuda."
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        deuda = self.context["deuda"]
        request = self.context["request"]

        try:
            return (
                DebtResolutionRequest
                .crear_para_deuda(
                    deuda=deuda,
                    solicitante=request.user,
                    descripcion=validated_data[
                        "descripcion"
                    ],
                    evidencia=validated_data[
                        "evidencia"
                    ],
                )
            )
        except DjangoValidationError as error:
            if hasattr(
                error,
                "message_dict",
            ):
                raise serializers.ValidationError(
                    error.message_dict
                )

            raise serializers.ValidationError({
                "error": error.messages
            })


class DebtResolutionReviewDecisionSerializer(
    serializers.Serializer
):
    decision = serializers.ChoiceField(
        choices=[
            (
                DebtResolutionRequest
                .DECISION_APROBADA
            ),
            (
                DebtResolutionRequest
                .DECISION_RECHAZADA
            ),
        ],
        required=True,
    )

    observacion = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=2000,
    )

    def validate_observacion(self, value):
        observacion = value.strip()

        if not observacion:
            raise serializers.ValidationError(
                (
                    "La observación o justificación "
                    "de la decisión es obligatoria."
                )
            )

        return observacion

    def validate(self, attrs):
        solicitud = self.context.get(
            "solicitud"
        )

        request = self.context.get(
            "request"
        )

        responsable = (
            request.user
            if request
            and request.user.is_authenticated
            else None
        )

        if not solicitud:
            raise serializers.ValidationError({
                "solicitud": (
                    "No se pudo identificar "
                    "la solicitud."
                )
            })

        if not responsable:
            raise serializers.ValidationError({
                "responsable": (
                    "No se pudo identificar "
                    "al responsable."
                )
            })

        if not solicitud.grupo.puede_revisar_solicitudes_deuda(
            responsable
        ):
            raise serializers.ValidationError({
                "responsable": (
                    "Solo el responsable vigente "
                    "de la actividad puede tomar "
                    "esta decisión."
                )
            })

        if (
            solicitud.estado
            != (
                DebtResolutionRequest
                .ESTADO_PENDIENTE_REVISION
            )
        ):
            raise serializers.ValidationError({
                "solicitud": (
                    "La solicitud ya fue revisada "
                    "y no puede decidirse nuevamente."
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        solicitud = self.context[
            "solicitud"
        ]

        request = self.context[
            "request"
        ]

        try:
            return solicitud.revisar(
                responsable=request.user,
                decision=validated_data[
                    "decision"
                ],
                observacion=validated_data[
                    "observacion"
                ],
            )
        except DjangoValidationError as error:
            if hasattr(
                error,
                "message_dict",
            ):
                raise serializers.ValidationError(
                    error.message_dict
                )

            raise serializers.ValidationError({
                "error": error.messages
            })


class DebtResolutionReviewListResponseSerializer(
    serializers.Serializer
):
    grupo_id = serializers.IntegerField(
        read_only=True,
    )

    grupo_nombre = serializers.CharField(
        read_only=True,
    )

    estado_actividad = serializers.CharField(
        read_only=True,
    )

    responsable = UserSimpleSerializer(
        read_only=True,
    )

    total_solicitudes = serializers.IntegerField(
        read_only=True,
    )

    total_pendientes = serializers.IntegerField(
        read_only=True,
    )

    mensaje = serializers.CharField(
        read_only=True,
    )

    solicitudes = DebtResolutionRequestSerializer(
        many=True,
        read_only=True,
    )


class DebtSerializer(
    serializers.ModelSerializer
):
    grupo_id = serializers.IntegerField(
        source="grupo.id",
        read_only=True,
    )

    saldo_cierre_id = serializers.IntegerField(
        source="saldo_cierre.id",
        read_only=True,
    )

    participante = UserSimpleSerializer(
        read_only=True,
    )

    participante_id = serializers.IntegerField(
        source="participante.id",
        read_only=True,
    )

    estado_display = serializers.CharField(
        source="get_estado_display",
        read_only=True,
    )

    monto_original = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    saldo_pendiente = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    es_deuda_propia = serializers.SerializerMethodField()

    puede_revisar_solicitudes = (
        serializers.SerializerMethodField()
    )

    asociada_a_actividad = serializers.SerializerMethodField()

    acreedor = serializers.SerializerMethodField()

    caso_todos_deben = serializers.BooleanField(
        source="grupo.caso_excepcional_todos_deben",
        read_only=True,
    )

    actividad = serializers.SerializerMethodField()

    solicitudes = serializers.SerializerMethodField()

    cantidad_solicitudes = serializers.SerializerMethodField()

    tiene_solicitud_pendiente = (
        serializers.BooleanField(
            read_only=True,
        )
    )

    mensaje_solicitudes = serializers.SerializerMethodField()

    class Meta:
        model = Debt
        fields = [
            "id",
            "grupo_id",
            "grupo_nombre",
            "saldo_cierre_id",
            "participante",
            "participante_id",
            "participante_username",
            "monto_original",
            "saldo_pendiente",
            "estado",
            "estado_display",
            "es_deuda_propia",
            "puede_revisar_solicitudes",
            "asociada_a_actividad",
            "acreedor",
            "caso_todos_deben",
            "actividad",
            "solicitudes",
            "cantidad_solicitudes",
            "tiene_solicitud_pendiente",
            "mensaje_solicitudes",
            "fecha_generacion",
            "fecha_actualizacion",
            "fecha_resolucion",
        ]

        read_only_fields = fields

    def get_es_deuda_propia(self, obj):
        request = self.context.get("request")

        return bool(
            request
            and request.user.is_authenticated
            and request.user.id == obj.participante_id
        )

    def get_puede_revisar_solicitudes(
        self,
        obj,
    ):
        request = self.context.get("request")

        if (
            not request
            or not request.user.is_authenticated
        ):
            return False

        return obj.grupo.puede_revisar_solicitudes_deuda(
            request.user
        )

    def get_asociada_a_actividad(self, obj):
        return True

    def get_acreedor(self, obj):
        return None

    def get_actividad(self, obj):
        return {
            "id": obj.grupo_id,
            "nombre": obj.grupo_nombre,
            "estado": obj.grupo.estado,
            "fecha_cierre": (
                obj.grupo.fecha_cierre_automatico
            ),
        }

    def get_solicitudes(self, obj):
        solicitudes = (
            obj.obtener_solicitudes_ordenadas()
        )

        return DebtResolutionRequestSerializer(
            solicitudes,
            many=True,
            context=self.context,
        ).data

    def get_cantidad_solicitudes(self, obj):
        return (
            obj.solicitudes_resolucion
            .count()
        )

    def get_mensaje_solicitudes(self, obj):
        if obj.solicitudes_resolucion.exists():
            return (
                "Solicitudes de resolución "
                "consultadas correctamente."
            )

        return (
            "Esta deuda todavía no tiene "
            "solicitudes de resolución."
        )



class OwnDebtsResponseSerializer(
    serializers.Serializer
):
    mensaje = serializers.CharField(
        read_only=True,
    )

    total_deudas = serializers.IntegerField(
        read_only=True,
    )

    monto_total_pendiente = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    deudas = DebtSerializer(
        many=True,
        read_only=True,
    )


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