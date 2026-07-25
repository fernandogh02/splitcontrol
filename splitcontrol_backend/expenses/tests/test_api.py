from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from expenses.models import (
    Expense,
    Group,
    GroupMembership,
    Payment,
)


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


class ConsultaBalancesGrupoTest(APITestCase):

    def setUp(self):
        self.damarys = User.objects.create_user(
            username="damarys",
            email="damarys@example.com",
            password="Prueba123",
        )

        self.andres = User.objects.create_user(
            username="andres",
            email="andres@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita",
            email="carlita@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Grupo de prueba",
            descripcion="Prueba de balances",
            creador=self.damarys,
        )

        self.grupo.participantes.add(
            self.damarys,
            self.andres,
            self.carlita,
        )

        gasto_uno = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Cena",
            monto=Decimal("60.00"),
            pagado_por=self.andres,
            registrado_por=self.damarys,
        )

        gasto_uno.participantes.add(
            self.damarys,
            self.andres,
            self.carlita,
        )

        gasto_uno.calcular_division_equitativa()

        gasto_dos = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Transporte",
            monto=Decimal("30.00"),
            pagado_por=self.damarys,
            registrado_por=self.damarys,
        )

        gasto_dos.participantes.add(
            self.damarys,
            self.carlita,
        )

        gasto_dos.calcular_division_equitativa()

    def test_consultar_balances_del_grupo(self):
        self.client.force_authenticate(
            user=self.damarys
        )

        response = self.client.get(
            f"/api/grupos/{self.grupo.id}/balances/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["grupo_id"],
            self.grupo.id,
        )

        self.assertEqual(
            response.data["grupo_nombre"],
            "Grupo de prueba",
        )

        self.assertEqual(
            response.data["total_participantes"],
            3,
        )

        resumen = response.data["resumen"]

        self.assertEqual(
            Decimal(resumen["total_pagado"]),
            Decimal("90.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_correspondiente"]),
            Decimal("90.00"),
        )

        self.assertEqual(
            Decimal(resumen["balance_general"]),
            Decimal("0.00"),
        )

        balances = {
            balance["participante"]["username"]: balance
            for balance in response.data["balances"]
        }

        balance_andres = balances["andres"]

        self.assertEqual(
            Decimal(balance_andres["total_pagado"]),
            Decimal("60.00"),
        )

        self.assertEqual(
            Decimal(balance_andres["total_correspondiente"]),
            Decimal("20.00"),
        )

        self.assertEqual(
            Decimal(balance_andres["balance"]),
            Decimal("40.00"),
        )

        self.assertEqual(
            balance_andres["estado"],
            "a_favor",
        )

        balance_damarys = balances["damarys"]

        self.assertEqual(
            Decimal(balance_damarys["total_pagado"]),
            Decimal("30.00"),
        )

        self.assertEqual(
            Decimal(balance_damarys["total_correspondiente"]),
            Decimal("35.00"),
        )

        self.assertEqual(
            Decimal(balance_damarys["balance"]),
            Decimal("-5.00"),
        )

        self.assertEqual(
            balance_damarys["estado"],
            "debe",
        )

        balance_carlita = balances["carlita"]

        self.assertEqual(
            Decimal(balance_carlita["total_pagado"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(balance_carlita["total_correspondiente"]),
            Decimal("35.00"),
        )

        self.assertEqual(
            Decimal(balance_carlita["balance"]),
            Decimal("-35.00"),
        )

        self.assertEqual(
            balance_carlita["estado"],
            "debe",
        )

    def test_usuario_que_no_es_creador_no_puede_consultar_balances(self):
        self.client.force_authenticate(
            user=self.andres
        )

        response = self.client.get(
            f"/api/grupos/{self.grupo.id}/balances/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["error"],
            (
                "Grupo no encontrado o no tienes permiso "
                "para consultar sus balances."
            ),
        )
    
class ActualizacionBalancesAlRegistrarGastoTest(APITestCase):

    def setUp(self):
        self.damarys = User.objects.create_user(
            username="damarys_sc40",
            email="damarys_sc40@example.com",
            password="Prueba123",
        )

        self.andres = User.objects.create_user(
            username="andres_sc40",
            email="andres_sc40@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc40",
            email="carlita_sc40@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Grupo SC-40",
            descripcion="Prueba de actualización de balances",
            creador=self.damarys,
        )

        self.grupo.participantes.add(
            self.damarys,
            self.andres,
            self.carlita,
        )

        self.client.force_authenticate(
            user=self.damarys
        )

    def test_registrar_gasto_actualiza_balances(self):
        respuesta_inicial = self.client.get(
            f"/api/grupos/{self.grupo.id}/balances/"
        )

        self.assertEqual(
            respuesta_inicial.status_code,
            status.HTTP_200_OK,
        )

        resumen_inicial = respuesta_inicial.data["resumen"]

        self.assertEqual(
            Decimal(resumen_inicial["total_pagado"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(
                resumen_inicial["total_correspondiente"]
            ),
            Decimal("0.00"),
        )

        for balance in respuesta_inicial.data["balances"]:
            self.assertEqual(
                Decimal(balance["balance"]),
                Decimal("0.00"),
            )

            self.assertEqual(
                balance["estado"],
                "saldado",
            )

        respuesta_registro = self.client.post(
            f"/api/grupos/{self.grupo.id}/gastos/",
            {
                "descripcion": "Cena del grupo",
                "monto": "60.00",
                "fecha_gasto": "2026-07-20",
                "pagado_por_id": self.andres.id,
                "participantes_ids": [
                    self.damarys.id,
                    self.andres.id,
                    self.carlita.id,
                ],
            },
            format="json",
        )

        self.assertEqual(
            respuesta_registro.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            len(
                respuesta_registro.data["gasto"][
                    "divisiones"
                ]
            ),
            3,
        )

        respuesta_actualizada = self.client.get(
            f"/api/grupos/{self.grupo.id}/balances/"
        )

        self.assertEqual(
            respuesta_actualizada.status_code,
            status.HTTP_200_OK,
        )

        resumen_actualizado = (
            respuesta_actualizada.data["resumen"]
        )

        self.assertEqual(
            Decimal(resumen_actualizado["total_pagado"]),
            Decimal("60.00"),
        )

        self.assertEqual(
            Decimal(
                resumen_actualizado[
                    "total_correspondiente"
                ]
            ),
            Decimal("60.00"),
        )

        self.assertEqual(
            Decimal(
                resumen_actualizado["balance_general"]
            ),
            Decimal("0.00"),
        )

        balances = {
            balance["participante"]["username"]: balance
            for balance in respuesta_actualizada.data[
                "balances"
            ]
        }

        balance_andres = balances["andres_sc40"]

        self.assertEqual(
            Decimal(balance_andres["total_pagado"]),
            Decimal("60.00"),
        )

        self.assertEqual(
            Decimal(
                balance_andres["total_correspondiente"]
            ),
            Decimal("20.00"),
        )

        self.assertEqual(
            Decimal(balance_andres["balance"]),
            Decimal("40.00"),
        )

        self.assertEqual(
            balance_andres["estado"],
            "a_favor",
        )

        for username in [
            "damarys_sc40",
            "carlita_sc40",
        ]:
            balance_participante = balances[username]

            self.assertEqual(
                Decimal(
                    balance_participante["total_pagado"]
                ),
                Decimal("0.00"),
            )

            self.assertEqual(
                Decimal(
                    balance_participante[
                        "total_correspondiente"
                    ]
                ),
                Decimal("20.00"),
            )

            self.assertEqual(
                Decimal(
                    balance_participante["balance"]
                ),
                Decimal("-20.00"),
            )

            self.assertEqual(
                balance_participante["estado"],
                "debe",
            )


class RegistroPagoTest(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc43",
            email="fernando_sc43@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc43",
            email="carlita_sc43@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc43",
            email="damarys_sc43@example.com",
            password="Prueba123",
        )

        self.usuario_externo = User.objects.create_user(
            username="externo_sc43",
            email="externo_sc43@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Grupo SC-43",
            descripcion="Pruebas para registrar pagos",
            creador=self.fernando,
        )

        self.grupo.participantes.add(
            self.fernando,
            self.carlita,
            self.damarys,
        )

        self.url = (
            f"/api/grupos/{self.grupo.id}/pagos/"
        )

        self.client.force_authenticate(
            user=self.fernando
        )

    def test_registrar_pago_correctamente(self):
        response = self.client.post(
            self.url,
            {
                "pagador_id": self.carlita.id,
                "receptor_id": self.fernando.id,
                "monto": "15.50",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["mensaje"],
            "Pago registrado correctamente.",
        )

        self.assertEqual(
            Payment.objects.count(),
            1,
        )

        pago = Payment.objects.get()

        self.assertEqual(
            pago.grupo,
            self.grupo,
        )

        self.assertEqual(
            pago.pagador,
            self.carlita,
        )

        self.assertEqual(
            pago.receptor,
            self.fernando,
        )

        self.assertEqual(
            pago.monto,
            Decimal("15.50"),
        )

        self.assertEqual(
            pago.registrado_por,
            self.fernando,
        )

        self.assertEqual(
            response.data["pago"]["pagador"]["username"],
            "carlita_sc43",
        )

        self.assertEqual(
            response.data["pago"]["receptor"]["username"],
            "fernando_sc43",
        )

    def test_no_permite_pago_a_la_misma_persona(self):
        response = self.client.post(
            self.url,
            {
                "pagador_id": self.carlita.id,
                "receptor_id": self.carlita.id,
                "monto": "10.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "receptor_id",
            response.data,
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_pagador_debe_pertenecer_al_grupo(self):
        response = self.client.post(
            self.url,
            {
                "pagador_id": self.usuario_externo.id,
                "receptor_id": self.fernando.id,
                "monto": "10.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "pagador_id",
            response.data,
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_receptor_debe_pertenecer_al_grupo(self):
        response = self.client.post(
            self.url,
            {
                "pagador_id": self.carlita.id,
                "receptor_id": self.usuario_externo.id,
                "monto": "10.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "receptor_id",
            response.data,
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_monto_debe_ser_mayor_que_cero(self):
        response = self.client.post(
            self.url,
            {
                "pagador_id": self.carlita.id,
                "receptor_id": self.fernando.id,
                "monto": "0.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "monto",
            response.data,
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_usuario_no_creador_no_puede_registrar_pago(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response = self.client.post(
            self.url,
            {
                "pagador_id": self.carlita.id,
                "receptor_id": self.fernando.id,
                "monto": "10.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["error"],
            (
                "Grupo no encontrado o no tienes permiso "
                "para registrar pagos."
            ),
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )


class VigenciaEstadoActividadTest(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc43_v2",
            email="fernando_sc43_v2@example.com",
            password="Prueba123",
        )

        self.client.force_authenticate(
            user=self.fernando
        )

        self.url = "/api/grupos/"

    def test_crear_actividad_con_vigencia_valida(self):
        fecha_inicio = timezone.now() + timedelta(days=1)
        fecha_fin = fecha_inicio + timedelta(days=4)

        response = self.client.post(
            self.url,
            {
                "nombre": "Viaje a la playa",
                "descripcion": "Actividad entre amigos",
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["nombre"],
            "Viaje a la playa",
        )

        self.assertEqual(
            response.data["estado"],
            Group.ESTADO_PROGRAMADA,
        )

        grupo = Group.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            grupo.creador,
            self.fernando,
        )

        self.assertTrue(
            grupo.participantes.filter(
                id=self.fernando.id
            ).exists()
        )

        self.assertIsNotNone(
            grupo.fecha_inicio
        )

        self.assertIsNotNone(
            grupo.fecha_fin
        )

    def test_crear_actividad_exige_fecha_inicio_y_fin(self):
        response = self.client.post(
            self.url,
            {
                "nombre": "Actividad sin vigencia",
                "descripcion": "No debe crearse",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "fecha_inicio",
            response.data,
        )

        self.assertIn(
            "fecha_fin",
            response.data,
        )

        self.assertFalse(
            Group.objects.filter(
                nombre="Actividad sin vigencia"
            ).exists()
        )

    def test_fecha_fin_debe_ser_posterior_a_fecha_inicio(self):
        fecha_inicio = timezone.now() + timedelta(days=2)
        fecha_fin = fecha_inicio - timedelta(hours=1)

        response = self.client.post(
            self.url,
            {
                "nombre": "Actividad inválida",
                "descripcion": "Fechas incorrectas",
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "fecha_fin",
            response.data,
        )

        self.assertFalse(
            Group.objects.filter(
                nombre="Actividad inválida"
            ).exists()
        )

    def test_estado_no_se_puede_modificar_manualmente(self):
        fecha_inicio = timezone.now() + timedelta(days=1)
        fecha_fin = fecha_inicio + timedelta(days=2)

        response = self.client.post(
            self.url,
            {
                "nombre": "Actividad programada",
                "descripcion": "Estado calculado",
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
                "estado": Group.ESTADO_CERRADA,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["estado"],
            Group.ESTADO_PROGRAMADA,
        )

        grupo = Group.objects.get(
            id=response.data["id"]
        )

        response_patch = self.client.patch(
            f"/api/grupos/{grupo.id}/",
            {
                "estado": Group.ESTADO_CERRADA,
            },
            format="json",
        )

        self.assertEqual(
            response_patch.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response_patch.data["estado"],
            Group.ESTADO_PROGRAMADA,
        )

    def test_grupo_antiguo_sin_fechas_queda_sin_configurar(self):
        grupo = Group.objects.create(
            nombre="Grupo antiguo",
            descripcion="Creado antes de SC-43 V2",
            creador=self.fernando,
        )

        grupo.participantes.add(
            self.fernando
        )

        response = self.client.get(
            f"/api/grupos/{grupo.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsNone(
            response.data["fecha_inicio"]
        )

        self.assertIsNone(
            response.data["fecha_fin"]
        )

        self.assertEqual(
            response.data["estado"],
            Group.ESTADO_SIN_CONFIGURAR,
        )

    def test_estado_programada_activa_y_cerrada(self):
        momento_base = timezone.now()

        grupo = Group.objects.create(
            nombre="Estados de actividad",
            descripcion="Prueba de estados automáticos",
            creador=self.fernando,
            fecha_inicio=momento_base + timedelta(hours=1),
            fecha_fin=momento_base + timedelta(hours=5),
        )

        with patch(
            "expenses.models.timezone.now",
            return_value=momento_base,
        ):
            self.assertEqual(
                grupo.estado,
                Group.ESTADO_PROGRAMADA,
            )

        with patch(
            "expenses.models.timezone.now",
            return_value=momento_base + timedelta(hours=2),
        ):
            self.assertEqual(
                grupo.estado,
                Group.ESTADO_ACTIVA,
            )

        with patch(
            "expenses.models.timezone.now",
            return_value=momento_base + timedelta(hours=6),
        ):
            self.assertEqual(
                grupo.estado,
                Group.ESTADO_CERRADA,
            )


class GestionMembresiasHistorialTest(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc44",
            email="fernando_sc44@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc44",
            email="carlita_sc44@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc44",
            email="damarys_sc44@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Actividad SC-44",
            descripcion="Pruebas de membresías con historial",
            creador=self.fernando,
        )

        self.grupo.participantes.add(
            self.fernando
        )

        self.membresia_creador = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.fernando,
            )
        )

        self.url_agregar = (
            f"/api/grupos/{self.grupo.id}/"
            "participantes/"
        )

        self.url_historial = (
            f"/api/grupos/{self.grupo.id}/"
            "membresias/"
        )

        self.client.force_authenticate(
            user=self.fernando
        )

    def test_crear_actividad_genera_membresia_del_creador(self):
        fecha_inicio = timezone.now() + timedelta(days=1)
        fecha_fin = fecha_inicio + timedelta(days=2)

        response = self.client.post(
            "/api/grupos/",
            {
                "nombre": "Nueva actividad SC-44",
                "descripcion": "Actividad con membresía inicial",
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        grupo_creado = Group.objects.get(
            id=response.data["id"]
        )

        membresia = GroupMembership.objects.get(
            grupo=grupo_creado,
            usuario=self.fernando,
        )

        self.assertTrue(
            membresia.activo
        )

        self.assertIsNone(
            membresia.fecha_salida
        )

        self.assertTrue(
            grupo_creado.participantes.filter(
                id=self.fernando.id
            ).exists()
        )

    def test_agregar_participante_crea_membresia_activa(self):
        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.carlita.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["mensaje"],
            "Participante agregado correctamente.",
        )

        membresia = GroupMembership.objects.get(
            grupo=self.grupo,
            usuario=self.carlita,
        )

        self.assertTrue(
            membresia.activo
        )

        self.assertIsNone(
            membresia.fecha_salida
        )

        self.assertTrue(
            self.grupo.participantes.filter(
                id=self.carlita.id
            ).exists()
        )

        self.assertEqual(
            response.data["membresia"]["estado"],
            "activo",
        )

    def test_no_permite_duplicar_membresia_activa(self):
        primera_respuesta = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.carlita.id,
            },
            format="json",
        )

        segunda_respuesta = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.carlita.id,
            },
            format="json",
        )

        self.assertEqual(
            primera_respuesta.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            segunda_respuesta.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            segunda_respuesta.data["error"],
            (
                "El usuario ya es participante activo "
                "del grupo."
            ),
        )

        self.assertEqual(
            GroupMembership.objects.filter(
                grupo=self.grupo,
                usuario=self.carlita,
                activo=True,
            ).count(),
            1,
        )

    def test_retirar_participante_conserva_historial(self):
        self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.carlita.id,
            },
            format="json",
        )

        response = self.client.delete(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"participantes/{self.carlita.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["mensaje"],
            "Participante retirado correctamente.",
        )

        membresia = GroupMembership.objects.get(
            grupo=self.grupo,
            usuario=self.carlita,
        )

        self.assertFalse(
            membresia.activo
        )

        self.assertIsNotNone(
            membresia.fecha_salida
        )

        self.assertFalse(
            self.grupo.participantes.filter(
                id=self.carlita.id
            ).exists()
        )

        self.assertEqual(
            response.data["membresia"]["estado"],
            "retirado",
        )

    def test_no_permite_retirar_al_creador(self):
        response = self.client.delete(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"participantes/{self.fernando.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["error"],
            "No puedes eliminar al creador del grupo.",
        )

        self.membresia_creador.refresh_from_db()

        self.assertTrue(
            self.membresia_creador.activo
        )

        self.assertTrue(
            self.grupo.participantes.filter(
                id=self.fernando.id
            ).exists()
        )

    def test_participante_retirado_puede_reingresar(self):
        self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.carlita.id,
            },
            format="json",
        )

        self.client.delete(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"participantes/{self.carlita.id}/"
            )
        )

        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.carlita.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        membresias = GroupMembership.objects.filter(
            grupo=self.grupo,
            usuario=self.carlita,
        ).order_by("fecha_ingreso", "id")

        self.assertEqual(
            membresias.count(),
            2,
        )

        self.assertEqual(
            membresias.filter(
                activo=False
            ).count(),
            1,
        )

        self.assertEqual(
            membresias.filter(
                activo=True
            ).count(),
            1,
        )

        membresia_retirada = membresias.filter(
            activo=False
        ).first()

        membresia_activa = membresias.filter(
            activo=True
        ).first()

        self.assertIsNotNone(
            membresia_retirada.fecha_salida
        )

        self.assertIsNone(
            membresia_activa.fecha_salida
        )

        self.assertTrue(
            self.grupo.participantes.filter(
                id=self.carlita.id
            ).exists()
        )

    def test_historial_muestra_membresias_activas_y_retiradas(self):
        self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.carlita.id,
            },
            format="json",
        )

        self.client.delete(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"participantes/{self.carlita.id}/"
            )
        )

        self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.damarys.id,
            },
            format="json",
        )

        response = self.client.get(
            self.url_historial
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["grupo_id"],
            self.grupo.id,
        )

        self.assertEqual(
            response.data["total_membresias"],
            3,
        )

        self.assertEqual(
            response.data["total_activas"],
            2,
        )

        self.assertEqual(
            response.data["total_retiradas"],
            1,
        )

        estados_por_usuario = {}

        for membresia in response.data["membresias"]:
            username = membresia["usuario"]["username"]

            estados_por_usuario.setdefault(
                username,
                [],
            ).append(
                membresia["estado"]
            )

        self.assertIn(
            "activo",
            estados_por_usuario["fernando_sc44"],
        )

        self.assertIn(
            "retirado",
            estados_por_usuario["carlita_sc44"],
        )

        self.assertIn(
            "activo",
            estados_por_usuario["damarys_sc44"],
        )

    def test_usuario_no_creador_no_puede_consultar_historial(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response = self.client.get(
            self.url_historial
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["error"],
            (
                "Grupo no encontrado o no tienes permiso "
                "para consultar sus membresías."
            ),
        )


class ConsultaActividadesCompartidasTest(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc45",
            email="fernando_sc45@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc45",
            email="carlita_sc45@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc45",
            email="damarys_sc45@example.com",
            password="Prueba123",
        )

        self.usuario_externo = User.objects.create_user(
            username="externo_sc45",
            email="externo_sc45@example.com",
            password="Prueba123",
        )

        self.grupo = Group.objects.create(
            nombre="Actividad compartida SC-45",
            descripcion="Actividad visible para miembros activos",
            creador=self.fernando,
        )

        self.grupo.participantes.add(
            self.fernando,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.fernando,
        )

        self.membresia_carlita = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.carlita,
            )
        )

        membresia_damarys = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.damarys,
        )
        membresia_damarys.retirar()

        self.gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Almuerzo compartido",
            monto=Decimal("20.00"),
            pagado_por=self.fernando,
            registrado_por=self.fernando,
        )

        self.gasto.participantes.add(
            self.fernando,
            self.carlita,
        )
        self.gasto.calcular_division_equitativa()

    def test_participante_activo_ve_actividad_en_listado(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response = self.client.get(
            "/api/grupos/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        grupos_ids = [
            grupo["id"]
            for grupo in response.data
        ]

        self.assertIn(
            self.grupo.id,
            grupos_ids,
        )

        self.assertEqual(
            grupos_ids.count(self.grupo.id),
            1,
        )

    def test_creador_no_recibe_actividad_duplicada(self):
        self.client.force_authenticate(
            user=self.fernando
        )

        response = self.client.get(
            "/api/grupos/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        grupos_ids = [
            grupo["id"]
            for grupo in response.data
        ]

        self.assertEqual(
            grupos_ids.count(self.grupo.id),
            1,
        )

    def test_participante_retirado_no_ve_actividad_en_listado(self):
        self.client.force_authenticate(
            user=self.damarys
        )

        response = self.client.get(
            "/api/grupos/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        grupos_ids = [
            grupo["id"]
            for grupo in response.data
        ]

        self.assertNotIn(
            self.grupo.id,
            grupos_ids,
        )

    def test_usuario_externo_no_ve_actividad_en_listado(self):
        self.client.force_authenticate(
            user=self.usuario_externo
        )

        response = self.client.get(
            "/api/grupos/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        grupos_ids = [
            grupo["id"]
            for grupo in response.data
        ]

        self.assertNotIn(
            self.grupo.id,
            grupos_ids,
        )

    def test_participante_activo_puede_consultar_detalle(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response = self.client.get(
            f"/api/grupos/{self.grupo.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.grupo.id,
        )

        self.assertEqual(
            response.data["nombre"],
            "Actividad compartida SC-45",
        )

        self.assertEqual(
            response.data["creador_username"],
            "fernando_sc45",
        )

    def test_retirado_y_externo_no_pueden_consultar_detalle(self):
        for usuario in [
            self.damarys,
            self.usuario_externo,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            response = self.client.get(
                f"/api/grupos/{self.grupo.id}/"
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_participante_activo_puede_consultar_datos_compartidos(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        rutas = [
            f"/api/grupos/{self.grupo.id}/gastos/",
            (
                f"/api/grupos/{self.grupo.id}/"
                f"gastos/{self.gasto.id}/"
            ),
            f"/api/grupos/{self.grupo.id}/membresias/",
            f"/api/grupos/{self.grupo.id}/balances/",
            f"/api/grupos/{self.grupo.id}/deudas/",
        ]

        for ruta in rutas:
            response = self.client.get(ruta)

            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                msg=f"Falló la consulta de {ruta}",
            )

    def test_participante_activo_no_puede_editar_ni_eliminar_grupo(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response_patch = self.client.patch(
            f"/api/grupos/{self.grupo.id}/",
            {
                "nombre": "Nombre no autorizado",
            },
            format="json",
        )

        self.assertEqual(
            response_patch.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.grupo.refresh_from_db()

        self.assertEqual(
            self.grupo.nombre,
            "Actividad compartida SC-45",
        )

        response_delete = self.client.delete(
            f"/api/grupos/{self.grupo.id}/"
        )

        self.assertEqual(
            response_delete.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(
            Group.objects.filter(
                id=self.grupo.id
            ).exists()
        )

    def test_participante_activo_no_puede_administrar_participantes(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response_agregar = self.client.post(
            (
                f"/api/grupos/{self.grupo.id}/"
                "participantes/"
            ),
            {
                "usuario_id": self.usuario_externo.id,
            },
            format="json",
        )

        self.assertEqual(
            response_agregar.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        response_retirar = self.client.delete(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"participantes/{self.fernando.id}/"
            )
        )

        self.assertEqual(
            response_retirar.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                grupo=self.grupo,
                usuario=self.usuario_externo,
                activo=True,
            ).exists()
        )

        self.membresia_carlita.refresh_from_db()

        self.assertTrue(
            self.membresia_carlita.activo
        )

    def test_participante_activo_no_puede_registrar_gastos_ni_pagos(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response_gasto = self.client.post(
            f"/api/grupos/{self.grupo.id}/gastos/",
            {
                "descripcion": "Gasto no autorizado",
                "monto": "10.00",
                "fecha_gasto": "2026-07-25",
                "pagado_por_id": self.carlita.id,
                "participantes_ids": [
                    self.fernando.id,
                    self.carlita.id,
                ],
            },
            format="json",
        )

        self.assertEqual(
            response_gasto.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        response_pago = self.client.post(
            f"/api/grupos/{self.grupo.id}/pagos/",
            {
                "pagador_id": self.carlita.id,
                "receptor_id": self.fernando.id,
                "monto": "5.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response_pago.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertFalse(
            Expense.objects.filter(
                grupo=self.grupo,
                descripcion="Gasto no autorizado",
            ).exists()
        )

        self.assertFalse(
            Payment.objects.filter(
                grupo=self.grupo,
                pagador=self.carlita,
                receptor=self.fernando,
            ).exists()
        )