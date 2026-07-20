from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Expense, ExpenseDivision, Group
from .services import calcular_deudas_grupo
from .serializers import (
    ExpenseSerializer,
    GroupSerializer,
    UserSimpleSerializer,
)


def prueba_api(request):
    return JsonResponse({
        "mensaje": "API de SplitControl funcionando correctamente"
    })


class GroupListCreateView(generics.ListCreateAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(
            creador=self.request.user
        )

    def perform_create(self, serializer):
        grupo = serializer.save(
            creador=self.request.user
        )

        grupo.participantes.add(
            self.request.user
        )


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(
            creador=self.request.user
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

        if grupo.participantes.filter(
            id=usuario.id
        ).exists():
            return Response(
                {
                    "error": (
                        "El usuario ya es participante del grupo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        grupo.participantes.add(usuario)

        serializer = GroupSerializer(grupo)

        return Response(
            {
                "mensaje": (
                    "Participante agregado correctamente."
                ),
                "grupo": serializer.data,
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

        if not grupo.participantes.filter(
            id=usuario.id
        ).exists():
            return Response(
                {
                    "error": (
                        "El usuario no pertenece a este grupo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        grupo.participantes.remove(usuario)

        serializer = GroupSerializer(grupo)

        return Response(
            {
                "mensaje": (
                    "Participante eliminado correctamente."
                ),
                "grupo": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ExpenseCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = Group.objects.filter(
            id=pk,
            creador=request.user,
        ).first()

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
                "pagado_por",
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
                "total_gastos": gastos.count(),
                "gastos": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk):
        grupo = Group.objects.filter(
            id=pk,
            creador=request.user,
        ).first()

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

        gasto = serializer.save(
            grupo=grupo,
            registrado_por=request.user,
        )

        gasto_actualizado = (
            Expense.objects
            .select_related(
                "grupo",
                "pagado_por",
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
                    "Gasto registrado correctamente."
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
        grupo = Group.objects.filter(
            id=grupo_id,
            creador=request.user,
        ).first()

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
                "pagado_por",
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

        gasto = (
            Expense.objects
            .filter(
                id=gasto_id,
                grupo=grupo,
            )
            .select_related(
                "grupo",
                "pagado_por",
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

        gasto_actualizado = serializer.save()

        gasto_actualizado = (
            Expense.objects
            .select_related(
                "grupo",
                "pagado_por",
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

        gasto.delete()

        return Response(
            {
                "mensaje": "Gasto eliminado correctamente.",
                "gasto_id": gasto_eliminado_id,
            },
            status=status.HTTP_200_OK,
        )

class GroupBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        grupo = (
            Group.objects
            .filter(
                id=pk,
                creador=request.user,
            )
            .prefetch_related("participantes")
            .first()
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

        pagos_agrupados = (
            Expense.objects
            .filter(grupo=grupo)
            .values("pagado_por_id")
            .annotate(total=Sum("monto"))
        )

        valores_asignados = (
            ExpenseDivision.objects
            .filter(gasto__grupo=grupo)
            .values("participante_id")
            .annotate(total=Sum("monto_asignado"))
        )

        pagos_por_participante = {
            item["pagado_por_id"]: (
                item["total"] or Decimal("0.00")
            )
            for item in pagos_agrupados
        }

        asignado_por_participante = {
            item["participante_id"]: (
                item["total"] or Decimal("0.00")
            )
            for item in valores_asignados
        }

        balances = []
        total_pagado_grupo = Decimal("0.00")
        total_correspondiente_grupo = Decimal("0.00")

        participantes = grupo.participantes.all().order_by(
            "username"
        )

        for participante in participantes:
            total_pagado = pagos_por_participante.get(
                participante.id,
                Decimal("0.00"),
            )

            total_correspondiente = (
                asignado_por_participante.get(
                    participante.id,
                    Decimal("0.00"),
                )
            )

            balance = (
                total_pagado - total_correspondiente
            ).quantize(Decimal("0.01"))

            if balance > Decimal("0.00"):
                estado = "a_favor"
            elif balance < Decimal("0.00"):
                estado = "debe"
            else:
                estado = "saldado"

            total_pagado_grupo += total_pagado
            total_correspondiente_grupo += (
                total_correspondiente
            )

            balances.append(
                {
                    "participante": UserSimpleSerializer(
                        participante
                    ).data,
                    "total_pagado": f"{total_pagado:.2f}",
                    "total_correspondiente": (
                        f"{total_correspondiente:.2f}"
                    ),
                    "balance": f"{balance:.2f}",
                    "estado": estado,
                }
            )

        balance_general = (
            total_pagado_grupo
            - total_correspondiente_grupo
        ).quantize(Decimal("0.01"))

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
        grupo = (
            Group.objects
            .filter(
                id=pk,
                creador=request.user,
            )
            .prefetch_related("participantes")
            .first()
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