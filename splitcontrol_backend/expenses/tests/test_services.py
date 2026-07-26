from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from expenses.models import (
    Expense,
    ExpenseDivision,
    Group,
    GroupMembership,
)
from expenses.services import calcular_deudas_grupo


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
            descripcion="Gastos comunes del viaje",
            creador=self.carlita,
        )

        self.grupo.participantes.add(
            self.andres,
            self.damarys,
            self.carlita,
        )

        self.membresia_andres = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.andres,
        )

        self.membresia_damarys = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.damarys,
        )

        self.membresia_carlita = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.carlita,
        )

    def crear_gasto(self, monto=Decimal("60.00")):
        gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Cena",
            monto=monto,
            registrado_por=self.carlita,
        )

        gasto.sincronizar_integrantes_activos()

        return gasto

    def test_asocia_automaticamente_integrantes_activos(self):
        gasto = self.crear_gasto()

        participantes_asociados = set(
            gasto.participantes.values_list(
                "id",
                flat=True,
            )
        )

        participantes_divididos = set(
            gasto.divisiones.values_list(
                "participante_id",
                flat=True,
            )
        )

        esperados = {
            self.andres.id,
            self.damarys.id,
            self.carlita.id,
        }

        self.assertSetEqual(
            participantes_asociados,
            esperados,
        )

        self.assertSetEqual(
            participantes_divididos,
            esperados,
        )

        self.assertEqual(
            gasto.divisiones.count(),
            3,
        )

    def test_membresia_retirada_no_recibe_division(self):
        self.membresia_damarys.retirar()

        gasto = self.crear_gasto()

        participantes_divididos = set(
            gasto.divisiones.values_list(
                "participante_id",
                flat=True,
            )
        )

        self.assertSetEqual(
            participantes_divididos,
            {
                self.andres.id,
                self.carlita.id,
            },
        )

        self.assertFalse(
            gasto.participantes.filter(
                id=self.damarys.id
            ).exists()
        )

        self.assertFalse(
            gasto.divisiones.filter(
                participante=self.damarys
            ).exists()
        )

    def test_suma_divisiones_coincide_con_monto_total(self):
        gasto = self.crear_gasto(
            monto=Decimal("42.50")
        )

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

        self.assertEqual(
            gasto.divisiones.count(),
            3,
        )

    def test_recalcular_actualiza_divisiones(self):
        gasto = self.crear_gasto(
            monto=Decimal("60.00")
        )

        for division in gasto.divisiones.all():
            self.assertEqual(
                division.monto_asignado,
                Decimal("20.00"),
            )

        gasto.monto = Decimal("90.00")
        gasto.save(update_fields=["monto"])
        gasto.calcular_division_equitativa()

        divisiones_actualizadas = list(
            gasto.divisiones.values_list(
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

        self.assertEqual(
            sum(
                divisiones_actualizadas,
                Decimal("0.00"),
            ),
            Decimal("90.00"),
        )

    def test_repartir_centavos_sin_perder_dinero(self):
        gasto = self.crear_gasto(
            monto=Decimal("10.00")
        )

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


class DivisionAutomaticaGastoSC48Test(TestCase):

    def setUp(self):
        self.carlita = User.objects.create_user(
            username="carlita_sc48",
            email="carlita_sc48@example.com",
            password="Prueba123",
        )

        self.andres = User.objects.create_user(
            username="andres_sc48",
            email="andres_sc48@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc48",
            email="damarys_sc48@example.com",
            password="Prueba123",
        )

        self.fernando = User.objects.create_user(
            username="fernando_sc48",
            email="fernando_sc48@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Actividad SC-48",
            descripcion="División automática e histórica",
            creador=self.carlita,
        )

        self.grupo.participantes.add(
            self.carlita,
            self.andres,
            self.damarys,
        )

        self.membresia_carlita = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.carlita,
        )

        self.membresia_andres = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.andres,
        )

        self.membresia_damarys = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.damarys,
        )

    def crear_gasto(self, monto=Decimal("60.00")):
        gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Gasto común SC-48",
            monto=monto,
            registrado_por=self.carlita,
        )

        gasto.sincronizar_integrantes_activos()

        return gasto

    def test_divisiones_quedan_guardadas_en_expense_division(self):
        gasto = self.crear_gasto(
            monto=Decimal("45.00")
        )

        divisiones = ExpenseDivision.objects.filter(
            gasto=gasto
        )

        self.assertEqual(
            divisiones.count(),
            3,
        )

        self.assertEqual(
            sum(
                (
                    division.monto_asignado
                    for division in divisiones
                ),
                Decimal("0.00"),
            ),
            Decimal("45.00"),
        )

    def test_agregar_persona_despues_no_cambia_divisiones_anteriores(
        self,
    ):
        gasto = self.crear_gasto(
            monto=Decimal("60.00")
        )

        divisiones_originales = {
            division.participante_id: division.monto_asignado
            for division in gasto.divisiones.all()
        }

        self.grupo.participantes.add(
            self.fernando
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.fernando,
        )

        divisiones_posteriores = {
            division.participante_id: division.monto_asignado
            for division in gasto.divisiones.all()
        }

        self.assertDictEqual(
            divisiones_posteriores,
            divisiones_originales,
        )

        self.assertFalse(
            gasto.participantes.filter(
                id=self.fernando.id
            ).exists()
        )

        self.assertFalse(
            gasto.divisiones.filter(
                participante=self.fernando
            ).exists()
        )

    def test_retirar_persona_despues_no_cambia_divisiones_anteriores(
        self,
    ):
        gasto = self.crear_gasto(
            monto=Decimal("60.00")
        )

        divisiones_originales = {
            division.participante_id: division.monto_asignado
            for division in gasto.divisiones.all()
        }

        self.membresia_damarys.retirar()
        self.grupo.participantes.remove(
            self.damarys
        )

        divisiones_posteriores = {
            division.participante_id: division.monto_asignado
            for division in gasto.divisiones.all()
        }

        self.assertDictEqual(
            divisiones_posteriores,
            divisiones_originales,
        )

        self.assertTrue(
            gasto.participantes.filter(
                id=self.damarys.id
            ).exists()
        )

        self.assertTrue(
            gasto.divisiones.filter(
                participante=self.damarys
            ).exists()
        )

    def test_editar_recalcula_solo_participantes_originales(self):
        gasto = self.crear_gasto(
            monto=Decimal("60.00")
        )

        participantes_originales = set(
            gasto.participantes.values_list(
                "id",
                flat=True,
            )
        )

        self.grupo.participantes.add(
            self.fernando
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.fernando,
        )

        gasto.monto = Decimal("90.00")
        gasto.save(update_fields=["monto"])
        gasto.calcular_division_equitativa()

        participantes_recalculados = set(
            gasto.divisiones.values_list(
                "participante_id",
                flat=True,
            )
        )

        self.assertSetEqual(
            participantes_recalculados,
            participantes_originales,
        )

        self.assertFalse(
            gasto.divisiones.filter(
                participante=self.fernando
            ).exists()
        )

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
                Decimal("30.00"),
                Decimal("30.00"),
                Decimal("30.00"),
            ],
        )

        self.assertEqual(
            sum(montos, Decimal("0.00")),
            Decimal("90.00"),
        )


class CalculoDeudasGrupoTest(TestCase):

    def setUp(self):
        self.andres = User.objects.create_user(
            username="andres_deudas",
            email="andres_deudas@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_deudas",
            email="damarys_deudas@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_deudas",
            email="carlita_deudas@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Grupo de deudas comunes",
            descripcion="Pruebas del modelo de gasto común",
            creador=self.damarys,
        )

        self.grupo.participantes.add(
            self.andres,
            self.damarys,
            self.carlita,
        )

        for usuario in [
            self.andres,
            self.damarys,
            self.carlita,
        ]:
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=usuario,
            )

    def crear_gasto(
        self,
        descripcion,
        monto,
    ):
        gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion=descripcion,
            monto=monto,
            registrado_por=self.damarys,
        )

        gasto.sincronizar_integrantes_activos()

        return gasto

    def test_gasto_comun_sin_pagos_no_genera_deudas_directas(self):
        self.crear_gasto(
            descripcion="Cena",
            monto=Decimal("42.50"),
        )

        deudas = calcular_deudas_grupo(
            self.grupo
        )

        self.assertEqual(
            deudas,
            [],
        )

    def test_varios_gastos_comunes_sin_pagos_no_generan_deudas_directas(
        self,
    ):
        self.crear_gasto(
            descripcion="Hospedaje",
            monto=Decimal("90.00"),
        )

        self.crear_gasto(
            descripcion="Transporte",
            monto=Decimal("30.00"),
        )

        deudas = calcular_deudas_grupo(
            self.grupo
        )

        self.assertEqual(
            deudas,
            [],
        )

        self.assertEqual(
            self.grupo.total_gastos,
            Decimal("120.00"),
        )

    def test_grupo_sin_gastos_no_genera_deudas(self):
        deudas = calcular_deudas_grupo(
            self.grupo
        )

        self.assertEqual(
            deudas,
            [],
        )