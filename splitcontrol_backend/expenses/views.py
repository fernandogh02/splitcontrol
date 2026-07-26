from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import (
    generics,
    parsers,
    permissions,
    status,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ActivityHistory,
    ClosingBalance,
    Debt,
    DebtResolutionRequest,
    Expense,
    Group,
    GroupMembership,
    Notification,
    Payment,
)
from .services import (
    calcular_balances_grupo,
    calcular_deudas_grupo,
    calcular_resumen_economico_grupo,
)
from .serializers import (
    ActivityHistorySerializer,
    ClosingBalanceSerializer,
    DebtResolutionRequestCreateSerializer,
    DebtResolutionRequestSerializer,
    DebtResolutionReviewDecisionSerializer,
    DebtResolutionReviewListResponseSerializer,
    DebtReviewAssignmentRequestSerializer,
    DebtReviewAssignmentSerializer,
    DebtSerializer,
    ExpenseSerializer,
    GroupMembershipSerializer,
    GroupSerializer,
    NotificationSerializer,
    ParticipantDebtWarningRequestSerializer,
    ParticipantDebtWarningSerializer,
    ParticipantIncorporationSerializer,
    PaymentSerializer,
    UserSimpleSerializer,
)


def prueba_api(request):
    return JsonResponse({
        "mensaje": "API de SplitControl funcionando correctamente"
    })


def grupos_visibles_para_usuario(usuario):
    return (
        Group.objects
        .filter(
            Q(creador=usuario)
            | Q(
                membresias__usuario=usuario,
                membresias__activo=True,
            )
        )
        .select_related("creador")
        .prefetch_related("participantes")
        .distinct()
    )


def obtener_grupo_visible_para_usuario(
    usuario,
    grupo_id,
):
    return (
        grupos_visibles_para_usuario(usuario)
        .filter(id=grupo_id)
        .first()
    )


def grupo_esta_cerrado(grupo):
    return grupo.estado == Group.ESTADO_CERRADA


def grupo_esta_activo(grupo):
    return grupo.estado == Group.ESTADO_ACTIVA


def valor_historial(valor):
    if valor is None:
        return None

    if isinstance(valor, Decimal):
        return f"{valor:.2f}"

    if hasattr(valor, "isoformat"):
        return valor.isoformat()

    return valor


def datos_grupo_historial(grupo):
    return {
        "grupo_id": grupo.id,
        "nombre": grupo.nombre,
        "descripcion": grupo.descripcion,
        "fecha_inicio": valor_historial(
            grupo.fecha_inicio
        ),
        "fecha_fin": valor_historial(
            grupo.fecha_fin
        ),
        "estado": grupo.estado,
    }


def datos_gasto_historial(gasto):
    return {
        "gasto_id": gasto.id,
        "descripcion": gasto.descripcion,
        "monto": f"{gasto.monto:.2f}",
        "fecha_gasto": valor_historial(
            gasto.fecha_gasto
        ),
        "registrado_por": (
            gasto.registrado_por.username
            if gasto.registrado_por
            else None
        ),
        "participantes": list(
            gasto.participantes
            .order_by("id")
            .values_list(
                "username",
                flat=True,
            )
        ),
    }


def datos_pago_historial(pago):
    return {
        "pago_id": pago.id,
        "pagador_id": pago.pagador_id,
        "pagador_username": pago.pagador.username,
        "monto": f"{pago.monto:.2f}",
        "fecha_pago": valor_historial(
            pago.fecha_pago
        ),
        "registrado_por": (
            pago.registrado_por.username
            if pago.registrado_por
            else None
        ),
    }


def registrar_evento_historial(
    grupo,
    usuario,
    tipo_accion,
    descripcion,
    datos=None,
):
    return ActivityHistory.registrar(
        grupo=grupo,
        usuario=usuario,
        tipo_accion=tipo_accion,
        descripcion=descripcion,
        datos=datos,
    )


def respuesta_error_validacion(
    error,
):
    if hasattr(
        error,
        "message_dict",
    ):
        return error.message_dict

    return {
        "error": error.messages
    }


def crear_notificaciones_nuevo_gasto(
    gasto,
    usuario_registro,
):
    destinatarios_ids = (
        GroupMembership.objects
        .filter(
            grupo=gasto.grupo,
            activo=True,
        )
        .exclude(
            usuario=usuario_registro,
        )
        .values_list(
            "usuario_id",
            flat=True,
        )
        .distinct()
    )

    notificaciones = [
        Notification(
            usuario_id=usuario_id,
            titulo=(
                f"Nuevo gasto en {gasto.grupo.nombre}"
            ),
            mensaje=(
                f"{usuario_registro.username} registró "
                f'el gasto "{gasto.descripcion}" por '
                f"${gasto.monto:.2f}."
            ),
            enlace=f"/grupos/{gasto.grupo_id}",
        )
        for usuario_id in destinatarios_ids
    ]

    if notificaciones:
        Notification.objects.bulk_create(
            notificaciones
        )

    return len(notificaciones)


class GroupListCreateView(generics.ListCreateAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            grupos_visibles_para_usuario(
                self.request.user
            )
            .order_by("-fecha_creacion")
        )

    @transaction.atomic
    def perform_create(self, serializer):
        grupo = serializer.save(
            creador=self.request.user
        )

        grupo.participantes.add(
            self.request.user
        )

        membresia_creador = GroupMembership.objects.create(
            grupo=grupo,
            usuario=self.request.user,
        )

        registrar_evento_historial(
            grupo=grupo,
            usuario=self.request.user,
            tipo_accion=(
                ActivityHistory.TIPO_ACTIVIDAD_CREADA
            ),
            descripcion=(
                f'{self.request.user.username} creó la '
                f'actividad "{grupo.nombre}".'
            ),
            datos={
                **datos_grupo_historial(grupo),
                "membresia_creador_id": (
                    membresia_creador.id
                ),
            },
        )


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.method == "GET":
            return grupos_visibles_para_usuario(
                self.request.user
            )

        return Group.objects.filter(
            creador=self.request.user
        )

    @transaction.atomic
    def perform_update(self, serializer):
        grupo = serializer.instance

        datos_antes = datos_grupo_historial(
            grupo
        )

        campos_solicitados = list(
            serializer.validated_data.keys()
        )

        grupo_actualizado = serializer.save()

        datos_despues = datos_grupo_historial(
            grupo_actualizado
        )

        campos_modificados = [
            campo
            for campo in campos_solicitados
            if datos_antes.get(campo)
            != datos_despues.get(campo)
        ]

        if campos_modificados:
            registrar_evento_historial(
                grupo=grupo_actualizado,
                usuario=self.request.user,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_ACTIVIDAD_ACTUALIZADA
                ),
                descripcion=(
                    f'{self.request.user.username} actualizó '
                    f'la actividad '
                    f'"{grupo_actualizado.nombre}".'
                ),
                datos={
                    "campos_modificados": (
                        campos_modificados
                    ),
                    "antes": datos_antes,
                    "despues": datos_despues,
                },
            )


class GroupDebtResponsibleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def obtener_respuesta(
        self,
        grupo,
        request,
        mensaje=None,
    ):
        asignacion_vigente = (
            grupo.asignacion_responsable_deudas_vigente
        )

        asignaciones = (
            grupo.asignaciones_responsable_deudas
            .select_related(
                "responsable",
                "asignado_por",
            )
            .order_by(
                "-fecha_asignacion",
                "-id",
            )
        )

        return {
            "grupo_id": grupo.id,
            "grupo_nombre": grupo.nombre,
            "mensaje": (
                mensaje
                or grupo.mensaje_responsable_deudas
            ),
            "responsable": (
                UserSimpleSerializer(
                    asignacion_vigente.responsable,
                    context={
                        "request": request,
                    },
                ).data
                if asignacion_vigente
                else None
            ),
            "asignacion_vigente": (
                DebtReviewAssignmentSerializer(
                    asignacion_vigente,
                    context={
                        "request": request,
                    },
                ).data
                if asignacion_vigente
                else None
            ),
            "puede_revisar_solicitudes": (
                grupo.puede_revisar_solicitudes_deuda(
                    request.user
                )
            ),
            "total_asignaciones": asignaciones.count(),
            "historial_asignaciones": (
                DebtReviewAssignmentSerializer(
                    asignaciones,
                    many=True,
                    context={
                        "request": request,
                    },
                ).data
            ),
        }

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar al responsable de deudas."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            self.obtener_respuesta(
                grupo=grupo,
                request=request,
            ),
            status=status.HTTP_200_OK,
        )

    def put(self, request, pk):
        grupo = (
            Group.objects
            .filter(
                id=pk,
                creador=request.user,
            )
            .select_related("creador")
            .first()
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o solo el creador "
                        "puede asignar al responsable de deudas."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = (
            DebtReviewAssignmentRequestSerializer(
                data=request.data
            )
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        responsable = User.objects.get(
            id=serializer.validated_data[
                "responsable_id"
            ]
        )

        cantidad_anterior = (
            grupo.asignaciones_responsable_deudas
            .count()
        )

        try:
            asignacion, cambio_realizado = (
                grupo.asignar_responsable_deudas(
                    responsable=responsable,
                    asignado_por=request.user,
                    momento=timezone.now(),
                )
            )
        except ValidationError as error:
            errores = (
                error.message_dict
                if hasattr(
                    error,
                    "message_dict",
                )
                else {
                    "error": error.messages
                }
            )

            return Response(
                errores,
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not cambio_realizado:
            mensaje = (
                "El usuario seleccionado ya es el "
                "responsable vigente de las deudas."
            )
        elif cantidad_anterior == 0:
            mensaje = (
                "Responsable de deudas asignado "
                "correctamente."
            )
        else:
            mensaje = (
                "Responsable de deudas actualizado "
                "correctamente."
            )

        grupo.refresh_from_db()

        respuesta = self.obtener_respuesta(
            grupo=grupo,
            request=request,
            mensaje=mensaje,
        )

        respuesta["asignacion_realizada"] = (
            DebtReviewAssignmentSerializer(
                asignacion,
                context={
                    "request": request,
                },
            ).data
        )

        respuesta["cambio_realizado"] = (
            cambio_realizado
        )

        respuesta["grupo"] = GroupSerializer(
            grupo,
            context={
                "request": request,
            },
        ).data

        return Response(
            respuesta,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pk):
        return self.put(
            request,
            pk,
        )


class UserListView(generics.ListAPIView):
    serializer_class = UserSimpleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            User.objects
            .exclude(id=self.request.user.id)
            .order_by("username")
        )


class ParticipantDebtWarningView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(
        self,
        request,
        pk,
        usuario_id,
    ):
        grupo = (
            Group.objects
            .filter(
                id=pk,
                creador=request.user,
            )
            .select_related("creador")
            .first()
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o solo el "
                        "creador puede consultar esta "
                        "advertencia."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer_entrada = (
            ParticipantDebtWarningRequestSerializer(
                data={
                    "usuario_id": usuario_id,
                }
            )
        )

        if not serializer_entrada.is_valid():
            return Response(
                serializer_entrada.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = User.objects.get(
            id=serializer_entrada.validated_data[
                "usuario_id"
            ]
        )

        if GroupMembership.objects.filter(
            grupo=grupo,
            usuario=usuario,
            activo=True,
        ).exists():
            return Response(
                {
                    "error": (
                        "El usuario ya es participante "
                        "activo del grupo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        advertencia = (
            grupo.obtener_advertencia_deudas_usuario(
                usuario
            )
        )

        return Response(
            ParticipantDebtWarningSerializer(
                advertencia
            ).data,
            status=status.HTTP_200_OK,
        )


class AddParticipantView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        grupo = (
            Group.objects
            .filter(
                id=pk,
                creador=request.user,
            )
            .select_related("creador")
            .first()
        )

        if not grupo:
            return Response(
                {
                    "error": "Grupo no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer_entrada = (
            ParticipantIncorporationSerializer(
                data=request.data
            )
        )

        if not serializer_entrada.is_valid():
            return Response(
                serializer_entrada.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = User.objects.get(
            id=serializer_entrada.validated_data[
                "usuario_id"
            ]
        )

        confirmar_deudas = (
            serializer_entrada.validated_data[
                "confirmar_deudas"
            ]
        )

        try:
            (
                membresia,
                advertencia,
                incorporado,
            ) = grupo.incorporar_participante(
                usuario=usuario,
                agregado_por=request.user,
                confirmar_deudas=confirmar_deudas,
                momento=timezone.now(),
            )
        except ValidationError as error:
            return Response(
                respuesta_error_validacion(
                    error
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        advertencia_serializada = (
            ParticipantDebtWarningSerializer(
                advertencia
            ).data
        )

        if not incorporado:
            return Response(
                {
                    "mensaje": (
                        "El participante mantiene "
                        "obligaciones pendientes. "
                        "Debes confirmar o cancelar "
                        "la incorporación."
                    ),
                    "incorporado": False,
                    "requiere_confirmacion": True,
                    "advertencia": (
                        advertencia_serializada
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        grupo.refresh_from_db()

        mensaje = (
            "Participante agregado correctamente "
            "después de confirmar sus deudas pendientes."
            if advertencia[
                "tiene_deudas_pendientes"
            ]
            else (
                "Participante agregado "
                "correctamente."
            )
        )

        return Response(
            {
                "mensaje": mensaje,
                "incorporado": True,
                "requiere_confirmacion": False,
                "advertencia": (
                    advertencia_serializada
                ),
                "grupo": GroupSerializer(
                    grupo,
                    context={
                        "request": request,
                    },
                ).data,
                "membresia": (
                    GroupMembershipSerializer(
                        membresia,
                        context={
                            "request": request,
                        },
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )


class RemoveParticipantView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, usuario_id):
        grupo = Group.objects.filter(
            id=pk,
            creador=request.user,
        ).first()

        if not grupo:
            return Response(
                {
                    "error": "Grupo no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if grupo_esta_cerrado(grupo):
            return Response(
                {
                    "error": (
                        "No se pueden modificar participantes "
                        "porque la actividad está cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario = User.objects.filter(
            id=usuario_id
        ).first()

        if not usuario:
            return Response(
                {
                    "error": "Usuario no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if usuario == grupo.creador:
            return Response(
                {
                    "error": (
                        "No puedes eliminar al creador del grupo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        responsable_vigente = (
            grupo.responsable_deudas
        )

        if (
            responsable_vigente
            and responsable_vigente.id == usuario.id
        ):
            return Response(
                {
                    "error": (
                        "No puedes retirar al responsable "
                        "vigente de las deudas. Primero debes "
                        "asignar otro responsable."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membresia = (
            GroupMembership.objects
            .filter(
                grupo=grupo,
                usuario=usuario,
                activo=True,
            )
            .first()
        )

        if not membresia:
            return Response(
                {
                    "error": (
                        "El usuario no pertenece actualmente "
                        "a este grupo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            membresia.retirar()
            grupo.participantes.remove(usuario)

            registrar_evento_historial(
                grupo=grupo,
                usuario=request.user,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_PARTICIPANTE_RETIRO
                ),
                descripcion=(
                    f'{request.user.username} retiró a '
                    f'{usuario.username} de la actividad '
                    f'"{grupo.nombre}".'
                ),
                datos={
                    "participante_id": usuario.id,
                    "participante_username": (
                        usuario.username
                    ),
                    "membresia_id": membresia.id,
                    "fecha_salida": valor_historial(
                        membresia.fecha_salida
                    ),
                },
            )

        serializer = GroupSerializer(grupo)

        return Response(
            {
                "mensaje": (
                    "Participante retirado correctamente."
                ),
                "grupo": serializer.data,
                "membresia": (
                    GroupMembershipSerializer(
                        membresia
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )


class GroupMembershipHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar sus membresías."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        membresias = (
            GroupMembership.objects
            .filter(grupo=grupo)
            .select_related(
                "grupo",
                "usuario",
            )
            .order_by(
                "-fecha_ingreso",
                "-id",
            )
        )

        total_activas = membresias.filter(
            activo=True
        ).count()

        total_retiradas = membresias.filter(
            activo=False
        ).count()

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "total_membresias": membresias.count(),
                "total_activas": total_activas,
                "total_retiradas": total_retiradas,
                "membresias": (
                    GroupMembershipSerializer(
                        membresias,
                        many=True,
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )


class ExpenseCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar sus gastos."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        gastos = (
            Expense.objects
            .filter(grupo=grupo)
            .select_related(
                "grupo",
                "registrado_por",
            )
            .prefetch_related(
                "participantes",
                "divisiones__participante",
            )
            .order_by(
                "-fecha_gasto",
                "-fecha_registro",
            )
        )

        serializer = ExpenseSerializer(
            gastos,
            many=True,
        )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "total_registros": gastos.count(),
                "total_gastos": f"{grupo.total_gastos:.2f}",
                "gastos": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para registrar gastos."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not grupo_esta_activo(grupo):
            return Response(
                {
                    "error": (
                        "Solo se pueden registrar gastos mientras "
                        "la actividad está activa."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ExpenseSerializer(
            data=request.data,
            context={
                "request": request,
                "grupo": grupo,
            },
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            gasto = serializer.save(
                grupo=grupo,
                registrado_por=request.user,
            )

            notificaciones_generadas = (
                crear_notificaciones_nuevo_gasto(
                    gasto,
                    request.user,
                )
            )

            registrar_evento_historial(
                grupo=grupo,
                usuario=request.user,
                tipo_accion=(
                    ActivityHistory.TIPO_GASTO_CREADO
                ),
                descripcion=(
                    f'{request.user.username} registró el '
                    f'gasto "{gasto.descripcion}" por '
                    f'${gasto.monto:.2f} en la actividad '
                    f'"{grupo.nombre}".'
                ),
                datos=datos_gasto_historial(
                    gasto
                ),
            )

        gasto_actualizado = (
            Expense.objects
            .select_related(
                "grupo",
                "registrado_por",
            )
            .prefetch_related(
                "participantes",
                "divisiones__participante",
            )
            .get(id=gasto.id)
        )

        return Response(
            {
                "mensaje": (
                    "Gasto común registrado correctamente."
                ),
                "total_gastos": (
                    f"{grupo.total_gastos:.2f}"
                ),
                "notificaciones_generadas": (
                    notificaciones_generadas
                ),
                "gasto": ExpenseSerializer(
                    gasto_actualizado
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ExpenseDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, grupo_id, gasto_id):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            grupo_id,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar sus gastos."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        gasto = (
            Expense.objects
            .filter(
                id=gasto_id,
                grupo=grupo,
            )
            .select_related(
                "grupo",
                "registrado_por",
            )
            .prefetch_related(
                "participantes",
                "divisiones__participante",
            )
            .first()
        )

        if not gasto:
            return Response(
                {
                    "error": (
                        "El gasto no existe o no pertenece "
                        "a este grupo."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "gasto": ExpenseSerializer(gasto).data
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, grupo_id, gasto_id):
        grupo = Group.objects.filter(
            id=grupo_id,
            creador=request.user,
        ).first()

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para editar sus gastos."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if grupo_esta_cerrado(grupo):
            return Response(
                {
                    "error": (
                        "No se pueden modificar gastos porque "
                        "la actividad está cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        gasto = (
            Expense.objects
            .filter(
                id=gasto_id,
                grupo=grupo,
            )
            .select_related(
                "grupo",
                "registrado_por",
            )
            .prefetch_related(
                "participantes",
                "divisiones__participante",
            )
            .first()
        )

        if not gasto:
            return Response(
                {
                    "error": (
                        "El gasto no existe o no pertenece "
                        "a este grupo."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ExpenseSerializer(
            gasto,
            data=request.data,
            partial=True,
            context={
                "request": request,
                "grupo": grupo,
            },
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        datos_antes = datos_gasto_historial(
            gasto
        )

        with transaction.atomic():
            gasto_actualizado = serializer.save()

            datos_despues = datos_gasto_historial(
                gasto_actualizado
            )

            campos_modificados = [
                campo
                for campo in [
                    "descripcion",
                    "monto",
                    "fecha_gasto",
                ]
                if datos_antes.get(campo)
                != datos_despues.get(campo)
            ]

            if campos_modificados:
                registrar_evento_historial(
                    grupo=grupo,
                    usuario=request.user,
                    tipo_accion=(
                        ActivityHistory
                        .TIPO_GASTO_ACTUALIZADO
                    ),
                    descripcion=(
                        f'{request.user.username} actualizó '
                        f'el gasto '
                        f'"{gasto_actualizado.descripcion}" '
                        f'en la actividad "{grupo.nombre}".'
                    ),
                    datos={
                        "gasto_id": (
                            gasto_actualizado.id
                        ),
                        "campos_modificados": (
                            campos_modificados
                        ),
                        "antes": datos_antes,
                        "despues": datos_despues,
                    },
                )

        gasto_actualizado = (
            Expense.objects
            .select_related(
                "grupo",
                "registrado_por",
            )
            .prefetch_related(
                "participantes",
                "divisiones__participante",
            )
            .get(id=gasto_actualizado.id)
        )

        return Response(
            {
                "mensaje": (
                    "Gasto actualizado correctamente."
                ),
                "gasto": ExpenseSerializer(
                    gasto_actualizado
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, grupo_id, gasto_id):
        grupo = Group.objects.filter(
            id=grupo_id,
            creador=request.user,
        ).first()

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para eliminar sus gastos."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if grupo_esta_cerrado(grupo):
            return Response(
                {
                    "error": (
                        "No se pueden eliminar gastos porque "
                        "la actividad está cerrada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        gasto = Expense.objects.filter(
            id=gasto_id,
            grupo=grupo,
        ).first()

        if not gasto:
            return Response(
                {
                    "error": (
                        "El gasto no existe o no pertenece "
                        "a este grupo."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        gasto_eliminado_id = gasto.id
        datos_gasto_eliminado = (
            datos_gasto_historial(gasto)
        )

        with transaction.atomic():
            gasto.delete()

            registrar_evento_historial(
                grupo=grupo,
                usuario=request.user,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_GASTO_ELIMINADO
                ),
                descripcion=(
                    f'{request.user.username} eliminó el '
                    f'gasto '
                    f'"{datos_gasto_eliminado["descripcion"]}" '
                    f'por '
                    f'${datos_gasto_eliminado["monto"]} de la '
                    f'actividad "{grupo.nombre}".'
                ),
                datos=datos_gasto_eliminado,
            )

        return Response(
            {
                "mensaje": "Gasto eliminado correctamente.",
                "gasto_id": gasto_eliminado_id,
            },
            status=status.HTTP_200_OK,
        )


class GroupEconomicSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar su resumen económico."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        resumen_calculado = calcular_resumen_economico_grupo(
            grupo
        )

        cuotas = []

        for item in resumen_calculado["cuotas"]:
            cuotas.append(
                {
                    "participante": UserSimpleSerializer(
                        item["participante"]
                    ).data,
                    "activo": item["activo"],
                    "cuota_total": (
                        f'{item["cuota_total"]:.2f}'
                    ),
                    "total_aportado": (
                        f'{item["total_aportado"]:.2f}'
                    ),
                    "saldo_pendiente": (
                        f'{item["saldo_pendiente"]:.2f}'
                    ),
                    "estado": item["estado"],
                }
            )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "estado_actividad": grupo.estado,
                "resumen": {
                    "total_gastos": (
                        f'{resumen_calculado["total_gastos"]:.2f}'
                    ),
                    "cantidad_gastos": (
                        resumen_calculado["cantidad_gastos"]
                    ),
                    "total_cuotas": (
                        f'{resumen_calculado["total_cuotas"]:.2f}'
                    ),
                    "total_aportado": (
                        f'{resumen_calculado["total_aportado"]:.2f}'
                    ),
                    "total_pendiente": (
                        f'{resumen_calculado["total_pendiente"]:.2f}'
                    ),
                },
                "total_participantes": len(cuotas),
                "cuotas": cuotas,
            },
            status=status.HTTP_200_OK,
        )


class GroupClosingBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar sus saldos de cierre."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not grupo_esta_cerrado(grupo):
            return Response(
                {
                    "error": (
                        "Los saldos de cierre solo están "
                        "disponibles cuando la actividad "
                        "ha finalizado."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not grupo.fecha_generacion_saldos:
            return Response(
                {
                    "error": (
                        "El cierre automático todavía no ha "
                        "generado los saldos de la actividad."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        saldos = (
            ClosingBalance.objects
            .filter(grupo=grupo)
            .select_related(
                "grupo",
                "participante",
            )
            .order_by(
                "participante_username",
                "id",
            )
        )

        deudas = (
            Debt.objects
            .filter(grupo=grupo)
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

        resumen = (
            grupo.obtener_resumen_saldos_cierre()
        )

        total_saldados = saldos.filter(
            estado=ClosingBalance.ESTADO_SALDADO
        ).count()

        total_pendientes = saldos.filter(
            estado=ClosingBalance.ESTADO_PENDIENTE
        ).count()

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "estado_actividad": grupo.estado,
                "fecha_cierre_automatico": (
                    grupo.fecha_cierre_automatico
                ),
                "fecha_generacion_saldos": (
                    grupo.fecha_generacion_saldos
                ),
                "caso_excepcional_todos_deben": (
                    resumen["caso_todos_deben"]
                ),
                "fecha_deteccion_todos_deben": (
                    resumen[
                        "fecha_deteccion_todos_deben"
                    ]
                ),
                "mensaje": resumen["mensaje"],
                "puede_revisar_solicitudes": (
                    grupo.puede_revisar_solicitudes_deuda(
                        request.user
                    )
                ),
                "resumen": {
                    "total_participantes_con_obligacion": (
                        resumen[
                            "total_participantes_con_obligacion"
                        ]
                    ),
                    "total_saldos": (
                        resumen["total_saldos"]
                    ),
                    "total_saldados": total_saldados,
                    "total_pendientes": total_pendientes,
                    "total_deudas": (
                        resumen["total_deudas"]
                    ),
                    "total_cuotas": (
                        resumen["total_cuotas"]
                    ),
                    "total_pagado": (
                        resumen["total_pagado"]
                    ),
                    "total_pendiente": (
                        resumen["total_pendiente"]
                    ),
                },
                "deuda_propia": (
                    DebtSerializer(
                        grupo.obtener_deuda_propia(
                            request.user
                        ),
                        context={
                            "request": request,
                        },
                    ).data
                    if grupo.obtener_deuda_propia(
                        request.user
                    )
                    else None
                ),
                "saldos": ClosingBalanceSerializer(
                    saldos,
                    many=True,
                    context={
                        "request": request,
                    },
                ).data,
                "deudas": DebtSerializer(
                    deudas,
                    many=True,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class GroupOwnDebtView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar tu deuda."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not grupo_esta_cerrado(grupo):
            return Response(
                {
                    "error": (
                        "La deuda definitiva solo puede "
                        "consultarse después del cierre "
                        "de la actividad."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not grupo.fecha_generacion_saldos:
            return Response(
                {
                    "error": (
                        "El cierre automático todavía no ha "
                        "generado las deudas de la actividad."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        deuda = grupo.obtener_deuda_propia(
            request.user
        )

        if deuda:
            mensaje = (
                "Tu deuda pendiente fue consultada "
                "correctamente."
            )
        else:
            mensaje = (
                "No tienes una deuda pendiente en "
                "esta actividad."
            )

        resumen = (
            grupo.obtener_resumen_saldos_cierre()
        )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "estado_actividad": grupo.estado,
                "caso_excepcional_todos_deben": (
                    resumen["caso_todos_deben"]
                ),
                "fecha_deteccion_todos_deben": (
                    resumen[
                        "fecha_deteccion_todos_deben"
                    ]
                ),
                "mensaje": mensaje,
                "deuda": (
                    DebtSerializer(
                        deuda,
                        context={
                            "request": request,
                        },
                    ).data
                    if deuda
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )


class GroupDebtReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para revisar sus deudas."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not grupo_esta_cerrado(grupo):
            return Response(
                {
                    "error": (
                        "Las deudas definitivas solo pueden "
                        "revisarse después del cierre "
                        "de la actividad."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not grupo.fecha_generacion_saldos:
            return Response(
                {
                    "error": (
                        "El cierre automático todavía no ha "
                        "generado las deudas de la actividad."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            deudas = grupo.obtener_deudas_para_revision(
                request.user
            )
        except ValidationError as error:
            return Response(
                {
                    "error": error.messages[0]
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        resumen = (
            grupo.obtener_resumen_saldos_cierre()
        )

        mensaje = (
            "Todos los participantes con obligaciones "
            "mantienen saldos pendientes."
            if resumen["caso_todos_deben"]
            else (
                "Deudas disponibles para revisión "
                "consultadas correctamente."
            )
        )

        total_pendiente = sum(
            (
                deuda.saldo_pendiente
                for deuda in deudas
            ),
            Decimal("0.00"),
        )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "estado_actividad": grupo.estado,
                "caso_excepcional_todos_deben": (
                    resumen["caso_todos_deben"]
                ),
                "fecha_deteccion_todos_deben": (
                    resumen[
                        "fecha_deteccion_todos_deben"
                    ]
                ),
                "mensaje": mensaje,
                "responsable": UserSimpleSerializer(
                    request.user
                ).data,
                "total_deudas": deudas.count(),
                "monto_total_pendiente": (
                    f"{total_pendiente:.2f}"
                ),
                "deudas": DebtSerializer(
                    deudas,
                    many=True,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class GroupBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar sus balances."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        balances_calculados = calcular_balances_grupo(grupo)

        balances = []
        total_pagado_grupo = Decimal("0.00")
        total_correspondiente_grupo = Decimal("0.00")
        total_pagos_realizados = Decimal("0.00")
        total_pagos_recibidos = Decimal("0.00")
        balance_general = Decimal("0.00")

        for item in balances_calculados:
            participante = item["participante"]
            total_pagado = item["total_pagado"]
            total_correspondiente = item["total_correspondiente"]
            pagos_realizados = item["pagos_realizados"]
            pagos_recibidos = item["pagos_recibidos"]
            balance = item["balance"]

            if balance > Decimal("0.00"):
                estado = "a_favor"
            elif balance < Decimal("0.00"):
                estado = "debe"
            else:
                estado = "saldado"

            total_pagado_grupo += total_pagado
            total_correspondiente_grupo += total_correspondiente
            total_pagos_realizados += pagos_realizados
            total_pagos_recibidos += pagos_recibidos
            balance_general += balance

            balances.append(
                {
                    "participante": UserSimpleSerializer(
                        participante
                    ).data,
                    "total_pagado": f"{total_pagado:.2f}",
                    "total_correspondiente": (
                        f"{total_correspondiente:.2f}"
                    ),
                    "pagos_realizados": (
                        f"{pagos_realizados:.2f}"
                    ),
                    "pagos_recibidos": (
                        f"{pagos_recibidos:.2f}"
                    ),
                    "balance": f"{balance:.2f}",
                    "estado": estado,
                }
            )

        balance_general = balance_general.quantize(
            Decimal("0.01")
        )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "resumen": {
                    "total_pagado": (
                        f"{total_pagado_grupo:.2f}"
                    ),
                    "total_correspondiente": (
                        f"{total_correspondiente_grupo:.2f}"
                    ),
                    "total_pagos_realizados": (
                        f"{total_pagos_realizados:.2f}"
                    ),
                    "total_pagos_recibidos": (
                        f"{total_pagos_recibidos:.2f}"
                    ),
                    "balance_general": (
                        f"{balance_general:.2f}"
                    ),
                },
                "total_participantes": len(balances),
                "balances": balances,
            },
            status=status.HTTP_200_OK,
        )


class GroupDebtView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar sus deudas."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if grupo.fecha_generacion_saldos:
            deudas_persistentes = (
                Debt.objects
                .filter(grupo=grupo)
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

            total_deudas = sum(
                (
                    deuda.saldo_pendiente
                    for deuda in deudas_persistentes
                ),
                Decimal("0.00"),
            )

            resumen = (
                grupo.obtener_resumen_saldos_cierre()
            )

            return Response(
                {
                    "grupo_id": grupo.id,
                    "grupo_nombre": grupo.nombre,
                    "estado_actividad": grupo.estado,
                    "caso_excepcional_todos_deben": (
                        resumen["caso_todos_deben"]
                    ),
                    "mensaje": resumen["mensaje"],
                    "total_deudas": (
                        deudas_persistentes.count()
                    ),
                    "monto_total_pendiente": (
                        f"{total_deudas:.2f}"
                    ),
                    "deuda_propia": (
                        DebtSerializer(
                            grupo.obtener_deuda_propia(
                                request.user
                            ),
                            context={
                                "request": request,
                            },
                        ).data
                        if grupo.obtener_deuda_propia(
                            request.user
                        )
                        else None
                    ),
                    "deudas": DebtSerializer(
                        deudas_persistentes,
                        many=True,
                        context={
                            "request": request,
                        },
                    ).data,
                },
                status=status.HTTP_200_OK,
            )

        deudas_calculadas = calcular_deudas_grupo(grupo)

        deudas = []

        for deuda in deudas_calculadas:
            deudor = deuda["deudor"]
            acreedor = deuda["acreedor"]
            monto = deuda["monto"]

            deudas.append(
                {
                    "deudor": UserSimpleSerializer(
                        deudor
                    ).data,
                    "acreedor": UserSimpleSerializer(
                        acreedor
                    ).data,
                    "monto": f"{monto:.2f}",
                    "mensaje": (
                        f"{deudor.username} debe pagar "
                        f"${monto:.2f} a {acreedor.username}."
                    ),
                }
            )

        total_deudas = sum(
            (
                deuda["monto"]
                for deuda in deudas_calculadas
            ),
            Decimal("0.00"),
        )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "total_deudas": len(deudas),
                "monto_total_pendiente": (
                    f"{total_deudas:.2f}"
                ),
                "deudas": deudas,
            },
            status=status.HTTP_200_OK,
        )



class OwnDebtListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        deudas = (
            Debt.objects
            .filter(
                participante=request.user,
            )
            .select_related(
                "grupo",
                "participante",
                "saldo_cierre",
            )
            .prefetch_related(
                "solicitudes_resolucion",
                (
                    "solicitudes_resolucion"
                    "__solicitante"
                ),
                (
                    "solicitudes_resolucion"
                    "__revisado_por"
                ),
            )
            .order_by(
                "-fecha_generacion",
                "-id",
            )
        )

        total_deudas = deudas.count()

        monto_total_pendiente = (
            deudas.aggregate(
                total=Sum(
                    "saldo_pendiente"
                )
            )["total"]
            or Decimal("0.00")
        )

        mensaje = (
            "Deudas propias consultadas correctamente."
            if total_deudas > 0
            else "No tienes deudas registradas."
        )

        return Response(
            {
                "mensaje": mensaje,
                "total_deudas": total_deudas,
                "monto_total_pendiente": (
                    f"{monto_total_pendiente:.2f}"
                ),
                "deudas": DebtSerializer(
                    deudas,
                    many=True,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class OwnDebtDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, deuda_id):
        deuda = (
            Debt.objects
            .filter(
                id=deuda_id,
                participante=request.user,
            )
            .select_related(
                "grupo",
                "participante",
                "saldo_cierre",
            )
            .prefetch_related(
                "solicitudes_resolucion",
                (
                    "solicitudes_resolucion"
                    "__solicitante"
                ),
                (
                    "solicitudes_resolucion"
                    "__revisado_por"
                ),
            )
            .first()
        )

        if not deuda:
            return Response(
                {
                    "error": (
                        "Deuda no encontrada o no "
                        "te pertenece."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "mensaje": (
                    "Deuda propia consultada "
                    "correctamente."
                ),
                "deuda": DebtSerializer(
                    deuda,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class OwnDebtResolutionRequestListCreateView(
    APIView
):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [
        parsers.MultiPartParser,
        parsers.FormParser,
        parsers.JSONParser,
    ]

    def obtener_deuda(
        self,
        request,
        deuda_id,
    ):
        return (
            Debt.objects
            .filter(
                id=deuda_id,
                participante=request.user,
            )
            .select_related(
                "grupo",
                "participante",
                "saldo_cierre",
            )
            .first()
        )

    def get(self, request, deuda_id):
        deuda = self.obtener_deuda(
            request,
            deuda_id,
        )

        if not deuda:
            return Response(
                {
                    "error": (
                        "Deuda no encontrada o no "
                        "te pertenece."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        solicitudes = (
            deuda.obtener_solicitudes_ordenadas()
        )

        total_solicitudes = solicitudes.count()

        mensaje = (
            "Solicitudes de resolución "
            "consultadas correctamente."
            if total_solicitudes > 0
            else (
                "Esta deuda todavía no tiene "
                "solicitudes de resolución."
            )
        )

        return Response(
            {
                "deuda_id": deuda.id,
                "grupo_id": deuda.grupo_id,
                "grupo_nombre": deuda.grupo_nombre,
                "mensaje": mensaje,
                "total_solicitudes": (
                    total_solicitudes
                ),
                "tiene_solicitud_pendiente": (
                    deuda.tiene_solicitud_pendiente
                ),
                "solicitudes": (
                    DebtResolutionRequestSerializer(
                        solicitudes,
                        many=True,
                        context={
                            "request": request,
                        },
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, deuda_id):
        deuda = self.obtener_deuda(
            request,
            deuda_id,
        )

        if not deuda:
            return Response(
                {
                    "error": (
                        "Deuda no encontrada o no "
                        "te pertenece."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = (
            DebtResolutionRequestCreateSerializer(
                data=request.data,
                context={
                    "request": request,
                    "deuda": deuda,
                },
            )
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud = serializer.save()

        deuda.refresh_from_db()

        return Response(
            {
                "mensaje": (
                    "Solicitud de resolución enviada "
                    "correctamente."
                ),
                "solicitud": (
                    DebtResolutionRequestSerializer(
                        solicitud,
                        context={
                            "request": request,
                        },
                    ).data
                ),
                "deuda": DebtSerializer(
                    deuda,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class OwnDebtResolutionRequestDetailView(
    APIView
):
    permission_classes = [permissions.IsAuthenticated]

    def get(
        self,
        request,
        deuda_id,
        solicitud_id,
    ):
        solicitud = (
            DebtResolutionRequest.objects
            .filter(
                id=solicitud_id,
                deuda_id=deuda_id,
                deuda__participante=request.user,
                solicitante=request.user,
            )
            .select_related(
                "grupo",
                "deuda",
                "solicitante",
                "revisado_por",
            )
            .first()
        )

        if not solicitud:
            return Response(
                {
                    "error": (
                        "Solicitud no encontrada o "
                        "no te pertenece."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "mensaje": (
                    "Solicitud de resolución "
                    "consultada correctamente."
                ),
                "solicitud": (
                    DebtResolutionRequestSerializer(
                        solicitud,
                        context={
                            "request": request,
                        },
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )



class GroupDebtResolutionRequestReviewListView(
    APIView
):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = (
            Group.objects
            .filter(id=pk)
            .select_related("creador")
            .first()
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Actividad no encontrada."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            solicitudes_pendientes = (
                grupo
                .obtener_solicitudes_resolucion_para_revision(
                    request.user,
                    solo_pendientes=True,
                )
            )
        except ValidationError as error:
            return Response(
                respuesta_error_validacion(
                    error
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        total_solicitudes = (
            grupo.solicitudes_resolucion_deudas
            .count()
        )

        total_pendientes = (
            solicitudes_pendientes.count()
        )

        mensaje = (
            "Solicitudes pendientes de revisión "
            "consultadas correctamente."
            if total_pendientes > 0
            else (
                "No existen solicitudes pendientes "
                "de revisión en esta actividad."
            )
        )

        respuesta = {
            "grupo_id": grupo.id,
            "grupo_nombre": grupo.nombre,
            "estado_actividad": grupo.estado,
            "responsable": request.user,
            "total_solicitudes": total_solicitudes,
            "total_pendientes": total_pendientes,
            "mensaje": mensaje,
            "solicitudes": solicitudes_pendientes,
        }

        return Response(
            DebtResolutionReviewListResponseSerializer(
                respuesta,
                context={
                    "request": request,
                },
            ).data,
            status=status.HTTP_200_OK,
        )


class GroupDebtResolutionRequestDecisionView(
    APIView
):
    permission_classes = [permissions.IsAuthenticated]

    def obtener_solicitud(
        self,
        grupo_id,
        solicitud_id,
    ):
        return (
            DebtResolutionRequest.objects
            .filter(
                id=solicitud_id,
                grupo_id=grupo_id,
            )
            .select_related(
                "grupo",
                "grupo__creador",
                "deuda",
                "deuda__participante",
                "deuda__saldo_cierre",
                "solicitante",
                "revisado_por",
            )
            .first()
        )

    def get(
        self,
        request,
        pk,
        solicitud_id,
    ):
        solicitud = self.obtener_solicitud(
            grupo_id=pk,
            solicitud_id=solicitud_id,
        )

        if not solicitud:
            return Response(
                {
                    "error": (
                        "Solicitud no encontrada o no "
                        "pertenece a esta actividad."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not solicitud.grupo.puede_revisar_solicitudes_deuda(
            request.user
        ):
            return Response(
                {
                    "error": (
                        "Solo el responsable vigente "
                        "puede consultar esta solicitud."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "mensaje": (
                    "Solicitud consultada correctamente."
                ),
                "solicitud": (
                    DebtResolutionRequestSerializer(
                        solicitud,
                        context={
                            "request": request,
                        },
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )

    def patch(
        self,
        request,
        pk,
        solicitud_id,
    ):
        solicitud = self.obtener_solicitud(
            grupo_id=pk,
            solicitud_id=solicitud_id,
        )

        if not solicitud:
            return Response(
                {
                    "error": (
                        "Solicitud no encontrada o no "
                        "pertenece a esta actividad."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not solicitud.grupo.puede_revisar_solicitudes_deuda(
            request.user
        ):
            return Response(
                {
                    "error": (
                        "Solo el responsable vigente "
                        "puede tomar una decisión sobre "
                        "esta solicitud."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = (
            DebtResolutionReviewDecisionSerializer(
                data=request.data,
                context={
                    "request": request,
                    "solicitud": solicitud,
                },
            )
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            (
                solicitud_revisada,
                deuda_actualizada,
                notificacion,
            ) = serializer.save()
        except ValidationError as error:
            return Response(
                respuesta_error_validacion(
                    error
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud_revisada.refresh_from_db()
        deuda_actualizada.refresh_from_db()
        deuda_actualizada.saldo_cierre.refresh_from_db()
        notificacion.refresh_from_db()

        resumen_advertencia = (
            Debt.resumen_deudas_activas_usuario(
                solicitud_revisada.solicitante
            )
        )

        total_pendientes_actividad = (
            DebtResolutionRequest.objects
            .filter(
                grupo_id=pk,
                estado=(
                    DebtResolutionRequest
                    .ESTADO_PENDIENTE_REVISION
                ),
            )
            .count()
        )

        fue_aprobada = (
            solicitud_revisada.decision
            == (
                DebtResolutionRequest
                .DECISION_APROBADA
            )
        )

        mensaje = (
            "Solicitud aprobada y deuda resuelta "
            "correctamente."
            if fue_aprobada
            else (
                "Solicitud rechazada. La deuda "
                "permanece pendiente."
            )
        )

        return Response(
            {
                "mensaje": mensaje,
                "decision_guardada": True,
                "solicitud": (
                    DebtResolutionRequestSerializer(
                        solicitud_revisada,
                        context={
                            "request": request,
                        },
                    ).data
                ),
                "deuda": DebtSerializer(
                    deuda_actualizada,
                    context={
                        "request": request,
                    },
                ).data,
                "advertencia_actualizada": {
                    "usuario": {
                        "id": (
                            solicitud_revisada
                            .solicitante_id
                        ),
                        "username": (
                            solicitud_revisada
                            .solicitante_username
                        ),
                    },
                    "tiene_deudas_pendientes": (
                        resumen_advertencia[
                            "cantidad_deudas_pendientes"
                        ] > 0
                    ),
                    "cantidad_deudas_pendientes": (
                        resumen_advertencia[
                            "cantidad_deudas_pendientes"
                        ]
                    ),
                    "monto_total_pendiente": (
                        f'{resumen_advertencia[
                            "monto_total_pendiente"
                        ]:.2f}'
                    ),
                },
                "notificacion": (
                    NotificationSerializer(
                        notificacion,
                        context={
                            "request": request,
                        },
                    ).data
                ),
                "solicitudes_pendientes_actividad": (
                    total_pendientes_actividad
                ),
            },
            status=status.HTTP_200_OK,
        )

    def put(
        self,
        request,
        pk,
        solicitud_id,
    ):
        return self.patch(
            request,
            pk,
            solicitud_id,
        )


class PaymentCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar sus pagos."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        pagos = (
            Payment.objects
            .filter(grupo=grupo)
            .select_related(
                "grupo",
                "pagador",
                "registrado_por",
            )
            .order_by(
                "-fecha_registro",
                "-id",
            )
        )

        total_registros = pagos.count()

        mensaje = (
            "Pagos consultados correctamente."
            if total_registros > 0
            else "Todavía no existen pagos registrados."
        )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "estado_actividad": grupo.estado,
                "total_registros": total_registros,
                "mensaje": mensaje,
                "pagos": PaymentSerializer(
                    pagos,
                    many=True,
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para registrar pagos."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not grupo_esta_activo(grupo):
            return Response(
                {
                    "error": (
                        "Solo se pueden registrar pagos mientras "
                        "la actividad está activa."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membresia_activa = (
            GroupMembership.objects
            .filter(
                grupo=grupo,
                usuario=request.user,
                activo=True,
            )
            .exists()
        )

        if not membresia_activa:
            return Response(
                {
                    "error": (
                        "Solo un participante activo puede "
                        "registrar su propio pago."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PaymentSerializer(
            data=request.data,
            context={
                "request": request,
                "grupo": grupo,
            },
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            pago = serializer.save(
                grupo=grupo,
                pagador=request.user,
                registrado_por=request.user,
            )

            registrar_evento_historial(
                grupo=grupo,
                usuario=request.user,
                tipo_accion=(
                    ActivityHistory.TIPO_PAGO_CREADO
                ),
                descripcion=(
                    f'{request.user.username} registró un '
                    f'pago de ${pago.monto:.2f} en la '
                    f'actividad "{grupo.nombre}".'
                ),
                datos=datos_pago_historial(
                    pago
                ),
            )

        pago_registrado = (
            Payment.objects
            .select_related(
                "grupo",
                "pagador",
                "registrado_por",
            )
            .get(id=pago.id)
        )

        return Response(
            {
                "mensaje": (
                    "Pago propio registrado correctamente."
                ),
                "pago": PaymentSerializer(
                    pago_registrado
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, grupo_id, pago_id):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            grupo_id,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar sus pagos."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        pago = (
            Payment.objects
            .filter(
                id=pago_id,
                grupo=grupo,
            )
            .select_related(
                "grupo",
                "pagador",
                "registrado_por",
            )
            .first()
        )

        if not pago:
            return Response(
                {
                    "error": (
                        "El pago no existe o no pertenece "
                        "a esta actividad."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "estado_actividad": grupo.estado,
                "pago": PaymentSerializer(
                    pago
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class ActivityHistoryListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = obtener_grupo_visible_para_usuario(
            request.user,
            pk,
        )

        if not grupo:
            return Response(
                {
                    "error": (
                        "Grupo no encontrado o no tienes permiso "
                        "para consultar su historial."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        eventos = (
            ActivityHistory.objects
            .filter(grupo=grupo)
            .select_related(
                "grupo",
                "usuario",
            )
            .order_by(
                "-fecha_evento",
                "-id",
            )
        )

        total_eventos = eventos.count()

        mensaje = (
            "Historial consultado correctamente."
            if total_eventos > 0
            else (
                "Todavía no existen eventos registrados "
                "en esta actividad."
            )
        )

        return Response(
            {
                "grupo_id": grupo.id,
                "grupo_nombre": grupo.nombre,
                "estado_actividad": grupo.estado,
                "total_eventos": total_eventos,
                "mensaje": mensaje,
                "eventos": ActivityHistorySerializer(
                    eventos,
                    many=True,
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notificaciones = (
            Notification.objects
            .filter(usuario=request.user)
            .select_related("usuario")
            .order_by(
                "-fecha_creacion",
                "-id",
            )
        )

        total_notificaciones = notificaciones.count()

        total_no_leidas = notificaciones.filter(
            leida=False
        ).count()

        mensaje = (
            "Notificaciones consultadas correctamente."
            if total_notificaciones > 0
            else "No tienes notificaciones todavía."
        )

        return Response(
            {
                "total_notificaciones": total_notificaciones,
                "no_leidas": total_no_leidas,
                "mensaje": mensaje,
                "notificaciones": (
                    NotificationSerializer(
                        notificaciones,
                        many=True,
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, notification_id):
        notificacion = (
            Notification.objects
            .filter(
                id=notification_id,
                usuario=request.user,
            )
            .select_related("usuario")
            .first()
        )

        if not notificacion:
            return Response(
                {
                    "error": "Notificación no encontrada."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        cambio_realizado = (
            notificacion.marcar_como_leida()
        )

        total_no_leidas = (
            Notification.objects
            .filter(
                usuario=request.user,
                leida=False,
            )
            .count()
        )

        mensaje = (
            "Notificación marcada como leída."
            if cambio_realizado
            else "La notificación ya estaba leída."
        )

        return Response(
            {
                "mensaje": mensaje,
                "no_leidas": total_no_leidas,
                "notificacion": NotificationSerializer(
                    notificacion
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request):
        fecha_lectura = timezone.now()

        cantidad_actualizada = (
            Notification.objects
            .filter(
                usuario=request.user,
                leida=False,
            )
            .update(
                leida=True,
                fecha_lectura=fecha_lectura,
            )
        )

        mensaje = (
            "Todas las notificaciones fueron marcadas como leídas."
            if cantidad_actualizada > 0
            else "No tienes notificaciones pendientes de lectura."
        )

        return Response(
            {
                "mensaje": mensaje,
                "actualizadas": cantidad_actualizada,
                "no_leidas": 0,
            },
            status=status.HTTP_200_OK,
        )