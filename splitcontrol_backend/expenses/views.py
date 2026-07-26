from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ActivityHistory,
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
    ExpenseSerializer,
    GroupMembershipSerializer,
    GroupSerializer,
    NotificationSerializer,
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


class UserListView(generics.ListAPIView):
    serializer_class = UserSimpleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            User.objects
            .exclude(id=self.request.user.id)
            .order_by("username")
        )


class AddParticipantView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
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

        usuario_id = request.data.get("usuario_id")

        if not usuario_id:
            return Response(
                {
                    "error": "Debe seleccionar un usuario."
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

        membresia_activa = (
            GroupMembership.objects
            .filter(
                grupo=grupo,
                usuario=usuario,
                activo=True,
            )
            .first()
        )

        tenia_membresia_previa = (
            GroupMembership.objects
            .filter(
                grupo=grupo,
                usuario=usuario,
                activo=False,
            )
            .exists()
        )

        if membresia_activa:
            grupo.participantes.add(usuario)

            return Response(
                {
                    "error": (
                        "El usuario ya es participante activo "
                        "del grupo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            membresia = GroupMembership.objects.create(
                grupo=grupo,
                usuario=usuario,
            )

            grupo.participantes.add(usuario)

            tipo_evento = (
                ActivityHistory
                .TIPO_PARTICIPANTE_REINGRESO
                if tenia_membresia_previa
                else ActivityHistory
                .TIPO_PARTICIPANTE_INGRESO
            )

            accion_descripcion = (
                "reingresó a"
                if tenia_membresia_previa
                else "ingresó a"
            )

            registrar_evento_historial(
                grupo=grupo,
                usuario=request.user,
                tipo_accion=tipo_evento,
                descripcion=(
                    f'{request.user.username} agregó a '
                    f'{usuario.username}, quien '
                    f'{accion_descripcion} la actividad '
                    f'"{grupo.nombre}".'
                ),
                datos={
                    "participante_id": usuario.id,
                    "participante_username": (
                        usuario.username
                    ),
                    "membresia_id": membresia.id,
                    "es_reingreso": (
                        tenia_membresia_previa
                    ),
                },
            )

        serializer = GroupSerializer(grupo)

        return Response(
            {
                "mensaje": (
                    "Participante agregado correctamente."
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