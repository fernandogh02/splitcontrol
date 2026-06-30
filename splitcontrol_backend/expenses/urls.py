from django.urls import path
from .views import (
    prueba_api,
    GroupListCreateView,
    GroupDetailView,
    UserListView,
    AddParticipantView,
)

urlpatterns = [
    path("prueba/", prueba_api, name="prueba_api"),
    path("grupos/", GroupListCreateView.as_view(), name="listar_crear_grupos"),
    path("grupos/<int:pk>/", GroupDetailView.as_view(), name="detalle_grupo"),
    path("usuarios/", UserListView.as_view(), name="listar_usuarios"),
    path(
        "grupos/<int:pk>/participantes/",
        AddParticipantView.as_view(),
        name="agregar_participante"
    ),
]