from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from expenses.models import Expense, Group


class PruebaApiBackendTest(APITestCase):

    def test_ruta_prueba_api(self):
        response = self.client.get("/api/prueba/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_respuesta_json_api(self):
        response = self.client.get("/api/prueba/")
        data = response.json()

        self.assertEqual(
            data["mensaje"],
            "API de SplitControl funcionando correctamente",
        )


class ActualizacionDivisionGastoTest(APITestCase):

    def setUp(self):
        self.carlita = User.objects.create_user(
            username="carlita",
            email="carlita@example.com",
            password="Prueba123",
        )

        self.andres = User.objects.create_user(
            username="andres",
            email="andres@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys",
            email="damarys@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Viaje",
            descripcion="Gastos compartidos del viaje",
            creador=self.carlita,
        )

        self.grupo.participantes.add(
            self.carlita,
            self.andres,
            self.damarys,
        )

        self.gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Cena",
            monto=Decimal("60.00"),
            pagado_por=self.carlita,
            registrado_por=self.carlita,
        )

        self.gasto.participantes.add(
            self.carlita,
            self.andres,
            self.damarys,
        )

        self.gasto.calcular_division_equitativa()

        self.client.force_authenticate(
            user=self.carlita
        )

    def test_actualizar_monto_recalcula_divisiones(self):
        divisiones_iniciales = list(
            self.gasto.divisiones.values_list(
                "monto_asignado",
                flat=True,
            )
        )

        self.assertEqual(
            len(divisiones_iniciales),
            3,
        )

        for monto in divisiones_iniciales:
            self.assertEqual(
                monto,
                Decimal("20.00"),
            )

        response = self.client.patch(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"gastos/{self.gasto.id}/"
            ),
            {
                "monto": "90.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.gasto.refresh_from_db()

        self.assertEqual(
            self.gasto.monto,
            Decimal("90.00"),
        )

        divisiones_actualizadas = list(
            self.gasto.divisiones.values_list(
                "monto_asignado",
                flat=True,
            )
        )

        self.assertEqual(
            len(divisiones_actualizadas),
            3,
        )

        for monto in divisiones_actualizadas:
            self.assertEqual(
                monto,
                Decimal("30.00"),
            )

        total_dividido = sum(
            divisiones_actualizadas,
            Decimal("0.00"),
        )

        self.assertEqual(
            total_dividido,
            Decimal("90.00"),
        )

        self.assertFalse(
            self.gasto.divisiones.filter(
                monto_asignado=Decimal("20.00")
            ).exists()
        )

        divisiones_respuesta = response.data[
            "gasto"
        ]["divisiones"]

        self.assertEqual(
            len(divisiones_respuesta),
            3,
        )

        for division in divisiones_respuesta:
            self.assertEqual(
                Decimal(division["monto_asignado"]),
                Decimal("30.00"),
            )