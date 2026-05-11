from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse

def prueba_api(request):
    return JsonResponse({
        "mensaje": "API de SplitControl funcionando correctamente"
    })

