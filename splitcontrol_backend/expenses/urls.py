from django.urls import path
from .views import prueba_api, GroupCreateView

urlpatterns = [
    path("prueba/", prueba_api, name="prueba_api"),
    path("grupos/", GroupCreateView.as_view(), name="crear_grupo"),
]