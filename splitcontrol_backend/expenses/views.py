from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Group
from .serializers import GroupSerializer, UserSimpleSerializer


def prueba_api(request):
    return JsonResponse({
        "mensaje": "API de SplitControl funcionando correctamente"
    })


class GroupListCreateView(generics.ListCreateAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(creador=self.request.user)

    def perform_create(self, serializer):
        grupo = serializer.save(creador=self.request.user)
        grupo.participantes.add(self.request.user)


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(creador=self.request.user)


class UserListView(generics.ListAPIView):
    serializer_class = UserSimpleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.exclude(id=self.request.user.id).order_by("username")


class AddParticipantView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        grupo = Group.objects.filter(
            id=pk,
            creador=request.user
        ).first()

        if not grupo:
            return Response(
                {"error": "Grupo no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        usuario_id = request.data.get("usuario_id")

        if not usuario_id:
            return Response(
                {"error": "Debe seleccionar un usuario."},
                status=status.HTTP_400_BAD_REQUEST
            )

        usuario = User.objects.filter(id=usuario_id).first()

        if not usuario:
            return Response(
                {"error": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        if grupo.participantes.filter(id=usuario.id).exists():
            return Response(
                {"error": "El usuario ya es participante del grupo."},
                status=status.HTTP_400_BAD_REQUEST
            )

        grupo.participantes.add(usuario)

        serializer = GroupSerializer(grupo)

        return Response(
            {
                "mensaje": "Participante agregado correctamente.",
                "grupo": serializer.data
            },
            status=status.HTTP_200_OK
        )