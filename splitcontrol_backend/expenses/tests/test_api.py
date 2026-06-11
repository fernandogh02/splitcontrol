from rest_framework.test import APITestCase
from rest_framework import status


class PruebaApiBackendTest(APITestCase):

    def test_ruta_prueba_api(self):
        response = self.client.get('/api/prueba/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_respuesta_json_api(self):
        response = self.client.get('/api/prueba/')
        data = response.json()

        self.assertEqual(
            data["mensaje"],
            "API de SplitControl funcionando correctamente"
        )