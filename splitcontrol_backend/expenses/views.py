from django.http import JsonResponse
from rest_framework import generics, permissions

from .models import Group
from .serializers import GroupSerializer


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
        serializer.save(creador=self.request.user)


class GroupDetailView(generics.RetrieveAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(creador=self.request.user)