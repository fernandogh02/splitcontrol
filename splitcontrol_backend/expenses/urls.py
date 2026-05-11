from django.urls import path
from .views import prueba_api

urlpatterns = [
    path('prueba/', prueba_api, name='prueba_api'),
]