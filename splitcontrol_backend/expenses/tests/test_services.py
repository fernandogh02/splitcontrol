from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from expenses.models import Expense, Group


class DivisionGastoTest(TestCase):

    def setUp(self):
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

        self.carlita = User.objects.create_user(
            username="carlita",
            email="carlita@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Viaje",
            descripcion="Gastos del viaje",
            creador=self.carlita,
        )

        self.grupo.participantes.add(
            self.andres,
            self.damarys,
            self.carlita,
        )

    def crear_gasto(self, monto=Decimal("60.00")):
        gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Cena",
            monto=monto,
            pagado_por=self.carlita,
            registrado_por=self.carlita,
        )

        return gasto

    def test_dividir_solo_entre_participantes_seleccionados(self):
        gasto = self.crear_gasto()

        gasto.participantes.add(
            self.andres,
            self.damarys,
        )

        gasto.calcular_division_equitativa()

        divisiones = gasto.divisiones.all()

        participantes_divididos = set(
            divisiones.values_list(
                "participante_id",
                flat=True,
            )
        )

        self.assertEqual(divisiones.count(), 2)

        self.assertSetEqual(
            participantes_divididos,
            {
                self.andres.id,
                self.damarys.id,
            },
        )

        self.assertFalse(
            divisiones.filter(
                participante=self.carlita
            ).exists()
        )

    def test_participante_no_seleccionado_no_recibe_division(self):
        gasto = self.crear_gasto()

        gasto.participantes.add(
            self.andres,
            self.damarys,
        )

        gasto.calcular_division_equitativa()

        division_carlita = gasto.divisiones.filter(
            participante=self.carlita
        )

        self.assertFalse(
            division_carlita.exists()
        )

    def test_suma_divisiones_coincide_con_monto_total(self):
        gasto = self.crear_gasto(
            monto=Decimal("42.50")
        )

        gasto.participantes.add(
            self.andres,
            self.damarys,
        )

        gasto.calcular_division_equitativa()

        total_dividido = sum(
            (
                division.monto_asignado
                for division in gasto.divisiones.all()
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            total_dividido,
            Decimal("42.50"),
        )

        for division in gasto.divisiones.all():
            self.assertEqual(
                division.monto_asignado,
                Decimal("21.25"),
            )

    def test_recalcular_elimina_participantes_anteriores(self):
        gasto = self.crear_gasto()

        gasto.participantes.add(
            self.andres,
            self.damarys,
        )

        gasto.calcular_division_equitativa()

        gasto.participantes.set([
            self.damarys,
            self.carlita,
        ])

        gasto.calcular_division_equitativa()

        participantes_divididos = set(
            gasto.divisiones.values_list(
                "participante_id",
                flat=True,
            )
        )

        self.assertSetEqual(
            participantes_divididos,
            {
                self.damarys.id,
                self.carlita.id,
            },
        )

        self.assertFalse(
            gasto.divisiones.filter(
                participante=self.andres
            ).exists()
        )

    def test_repartir_centavos_sin_perder_dinero(self):
        gasto = self.crear_gasto(
            monto=Decimal("10.00")
        )

        gasto.participantes.add(
            self.andres,
            self.damarys,
            self.carlita,
        )

        gasto.calcular_division_equitativa()

        montos = list(
            gasto.divisiones
            .order_by("participante_id")
            .values_list(
                "monto_asignado",
                flat=True,
            )
        )

        self.assertEqual(
            montos,
            [
                Decimal("3.34"),
                Decimal("3.33"),
                Decimal("3.33"),
            ],
        )

        self.assertEqual(
            sum(montos, Decimal("0.00")),
            Decimal("10.00"),
        )