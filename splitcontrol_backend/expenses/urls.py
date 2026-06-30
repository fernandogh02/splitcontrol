from django.urls import path
from .views import prueba_api, GroupListCreateView

urlpatterns = [
    path("prueba/", prueba_api, name="prueba_api"),
    path("grupos/", GroupListCreateView.as_view(), name="listar_crear_grupos"),
]