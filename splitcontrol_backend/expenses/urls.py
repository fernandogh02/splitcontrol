from django.urls import path
from .views import prueba_api, GroupListCreateView, GroupDetailView

urlpatterns = [
    path("prueba/", prueba_api, name="prueba_api"),
    path("grupos/", GroupListCreateView.as_view(), name="listar_crear_grupos"),
    path("grupos/<int:pk>/", GroupDetailView.as_view(), name="detalle_grupo"),
]