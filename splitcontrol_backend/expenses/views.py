from django.http import JsonResponse
from rest_framework import generics, permissions

from .models import Group
from .serializers import GroupSerializer


def prueba_api(request):
    return JsonResponse({
        "mensaje": "API de SplitControl funcionando correctamente"
    })


class GroupCreateView(generics.CreateAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(creador=self.request.user)