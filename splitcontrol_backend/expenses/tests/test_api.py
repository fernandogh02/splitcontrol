from datetime import timedelta
from io import StringIO
from tempfile import TemporaryDirectory
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from expenses.models import (
    ActivityHistory,
    ClosingBalance,
    Debt,
    DebtResolutionRequest,
    DebtReviewAssignment,
    Expense,
    ExpenseDivision,
    Group,
    GroupMembership,
    Notification,
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

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Viaje",
            descripcion="Gastos compartidos del viaje",
            creador=self.carlita,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo.participantes.add(
            self.carlita,
            self.andres,
            self.damarys,
        )

        for usuario in [
            self.carlita,
            self.andres,
            self.damarys,
        ]:
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=usuario,
            )

        self.gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Cena",
            monto=Decimal("60.00"),
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

        for usuario in [
            self.damarys,
            self.andres,
            self.carlita,
        ]:
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=usuario,
            )

        gasto_uno = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Cena",
            monto=Decimal("60.00"),
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
            response.data["total_participantes"],
            3,
        )

        resumen = response.data["resumen"]

        self.assertEqual(
            Decimal(resumen["total_pagado"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_correspondiente"]),
            Decimal("90.00"),
        )

        self.assertEqual(
            Decimal(resumen["balance_general"]),
            Decimal("-90.00"),
        )

        balances = {
            balance["participante"]["username"]: balance
            for balance in response.data["balances"]
        }

        self.assertEqual(
            Decimal(balances["andres"]["total_correspondiente"]),
            Decimal("20.00"),
        )
        self.assertEqual(
            Decimal(balances["andres"]["balance"]),
            Decimal("-20.00"),
        )

        for username in [
            "damarys",
            "carlita",
        ]:
            self.assertEqual(
                Decimal(
                    balances[username]["total_correspondiente"]
                ),
                Decimal("35.00"),
            )
            self.assertEqual(
                Decimal(balances[username]["balance"]),
                Decimal("-35.00"),
            )
            self.assertEqual(
                balances[username]["estado"],
                "debe",
            )

    def test_participante_activo_puede_consultar_balances(self):
        self.client.force_authenticate(
            user=self.andres
        )

        response = self.client.get(
            f"/api/grupos/{self.grupo.id}/balances/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
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

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Grupo SC-40",
            descripcion="Prueba de actualización de balances",
            creador=self.damarys,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo.participantes.add(
            self.damarys,
            self.andres,
            self.carlita,
        )

        for usuario in [
            self.damarys,
            self.andres,
            self.carlita,
        ]:
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=usuario,
            )

        self.client.force_authenticate(
            user=self.damarys
        )

    def test_registrar_gasto_actualiza_total_y_balances(self):
        respuesta_registro = self.client.post(
            f"/api/grupos/{self.grupo.id}/gastos/",
            {
                "descripcion": "Cena del grupo",
                "monto": "60.00",
                "fecha_gasto": "2026-07-20",
            },
            format="json",
        )

        self.assertEqual(
            respuesta_registro.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            respuesta_registro.data["mensaje"],
            "Gasto común registrado correctamente.",
        )

        self.assertEqual(
            Decimal(respuesta_registro.data["total_gastos"]),
            Decimal("60.00"),
        )

        gasto_respuesta = respuesta_registro.data["gasto"]

        self.assertNotIn(
            "pagado_por",
            gasto_respuesta,
        )

        self.assertEqual(
            gasto_respuesta["registrado_por"]["username"],
            "damarys_sc40",
        )

        self.assertEqual(
            len(gasto_respuesta["participantes"]),
            3,
        )

        self.assertEqual(
            len(gasto_respuesta["divisiones"]),
            3,
        )

        respuesta_actualizada = self.client.get(
            f"/api/grupos/{self.grupo.id}/balances/"
        )

        resumen = respuesta_actualizada.data["resumen"]

        self.assertEqual(
            Decimal(resumen["total_pagado"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_correspondiente"]),
            Decimal("60.00"),
        )

        self.assertEqual(
            Decimal(resumen["balance_general"]),
            Decimal("-60.00"),
        )

        for balance in respuesta_actualizada.data["balances"]:
            self.assertEqual(
                Decimal(balance["total_correspondiente"]),
                Decimal("20.00"),
            )
            self.assertEqual(
                Decimal(balance["balance"]),
                Decimal("-20.00"),
            )
            self.assertEqual(
                balance["estado"],
                "debe",
            )

        respuesta_grupo = self.client.get(
            f"/api/grupos/{self.grupo.id}/"
        )

        self.assertEqual(
            Decimal(respuesta_grupo.data["total_gastos"]),
            Decimal("60.00"),
        )

class RegistroPagoPropioSC51Test(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc51",
            email="fernando_sc51@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc51",
            email="carlita_sc51@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc51",
            email="damarys_sc51@example.com",
            password="Prueba123",
        )

        self.usuario_externo = User.objects.create_user(
            username="externo_sc51",
            email="externo_sc51@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad activa SC-51",
            descripcion="Registro de pagos propios",
            creador=self.fernando,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo.participantes.add(
            self.fernando,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.fernando,
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.carlita,
        )

        membresia_retirada = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.damarys,
        )
        membresia_retirada.retirar()

        self.gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Gasto común SC-51",
            monto=Decimal("40.00"),
            fecha_gasto="2026-07-25",
            registrado_por=self.fernando,
        )
        self.gasto.sincronizar_integrantes_activos()

        self.url = (
            f"/api/grupos/{self.grupo.id}/pagos/"
        )

        self.client.force_authenticate(
            user=self.fernando
        )

    def crear_grupo_no_activo(
        self,
        nombre,
        fecha_inicio=None,
        fecha_fin=None,
    ):
        grupo = Group.objects.create(
            nombre=nombre,
            descripcion="Actividad no habilitada para pagos",
            creador=self.fernando,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

        grupo.participantes.add(
            self.fernando
        )

        GroupMembership.objects.create(
            grupo=grupo,
            usuario=self.fernando,
        )

        return grupo

    def test_participante_activo_registra_pago_propio(self):
        response = self.client.post(
            self.url,
            {
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
            "Pago propio registrado correctamente.",
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
            self.fernando,
        )

        self.assertEqual(
            pago.registrado_por,
            self.fernando,
        )

        self.assertEqual(
            pago.monto,
            Decimal("15.50"),
        )

        self.assertEqual(
            pago.fecha_pago.isoformat(),
            "2026-07-25",
        )

        self.assertEqual(
            response.data["pago"]["pagador"]["username"],
            "fernando_sc51",
        )

        self.assertNotIn(
            "receptor",
            response.data["pago"],
        )

        self.assertNotIn(
            "receptor_id",
            response.data["pago"],
        )

    def test_pagador_se_asigna_desde_usuario_autenticado(self):
        response = self.client.post(
            self.url,
            {
                "pagador_id": self.carlita.id,
                "monto": "8.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        pago = Payment.objects.get()

        self.assertEqual(
            pago.pagador,
            self.fernando,
        )

        self.assertEqual(
            pago.registrado_por,
            self.fernando,
        )

        self.assertNotEqual(
            pago.pagador,
            self.carlita,
        )

    def test_monto_debe_ser_mayor_que_cero(self):
        response = self.client.post(
            self.url,
            {
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

    def test_fecha_del_pago_es_obligatoria(self):
        response = self.client.post(
            self.url,
            {
                "monto": "10.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "fecha_pago",
            response.data,
        )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_otro_participante_activo_registra_su_pago(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response = self.client.post(
            self.url,
            {
                "monto": "10.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        pago = Payment.objects.get()

        self.assertEqual(
            pago.pagador,
            self.carlita,
        )

        self.assertEqual(
            pago.registrado_por,
            self.carlita,
        )

    def test_retirado_y_externo_no_pueden_registrar_pago(self):
        for usuario in [
            self.damarys,
            self.usuario_externo,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            response = self.client.post(
                self.url,
                {
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
            Payment.objects.count(),
            0,
        )

    def test_solo_actividad_activa_permite_registrar_pago(self):
        ahora = timezone.now()

        grupos_no_activos = [
            self.crear_grupo_no_activo(
                nombre="Actividad programada SC-51",
                fecha_inicio=ahora + timedelta(days=1),
                fecha_fin=ahora + timedelta(days=2),
            ),
            self.crear_grupo_no_activo(
                nombre="Actividad cerrada SC-51",
                fecha_inicio=ahora - timedelta(days=2),
                fecha_fin=ahora - timedelta(days=1),
            ),
            self.crear_grupo_no_activo(
                nombre="Actividad sin configurar SC-51",
            ),
        ]

        for grupo in grupos_no_activos:
            response = self.client.post(
                f"/api/grupos/{grupo.id}/pagos/",
                {
                    "monto": "10.00",
                    "fecha_pago": "2026-07-25",
                },
                format="json",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
            )

            self.assertEqual(
                response.data["error"],
                (
                    "Solo se pueden registrar pagos mientras "
                    "la actividad está activa."
                ),
            )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_pago_actualiza_resumen_economico(self):
        resumen_inicial = self.client.get(
            (
                f"/api/grupos/{self.grupo.id}/"
                "resumen-economico/"
            )
        )

        self.assertEqual(
            Decimal(
                resumen_inicial.data[
                    "resumen"
                ]["total_aportado"]
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(
                resumen_inicial.data[
                    "resumen"
                ]["total_pendiente"]
            ),
            Decimal("40.00"),
        )

        response = self.client.post(
            self.url,
            {
                "monto": "15.50",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        resumen_actualizado = self.client.get(
            (
                f"/api/grupos/{self.grupo.id}/"
                "resumen-economico/"
            )
        )

        self.assertEqual(
            Decimal(
                resumen_actualizado.data[
                    "resumen"
                ]["total_aportado"]
            ),
            Decimal("15.50"),
        )

        self.assertEqual(
            Decimal(
                resumen_actualizado.data[
                    "resumen"
                ]["total_pendiente"]
            ),
            Decimal("24.50"),
        )

        cuotas = {
            cuota["participante"]["username"]: cuota
            for cuota in resumen_actualizado.data["cuotas"]
        }

        self.assertEqual(
            Decimal(
                cuotas["fernando_sc51"]["total_aportado"]
            ),
            Decimal("15.50"),
        )

        self.assertEqual(
            Decimal(
                cuotas["fernando_sc51"]["saldo_pendiente"]
            ),
            Decimal("4.50"),
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

        mensaje_duplicado = (
            segunda_respuesta.data.get("error")
        )

        if mensaje_duplicado is None:
            mensaje_duplicado = str(
                segunda_respuesta.data[
                    "usuario_id"
                ][0]
            )

        self.assertEqual(
            mensaje_duplicado,
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

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad compartida SC-45",
            descripcion="Actividad visible para miembros activos",
            creador=self.fernando,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo.participantes.add(
            self.fernando,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.fernando,
        )

        self.membresia_carlita = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.carlita,
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

        response = self.client.get("/api/grupos/")

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

        response = self.client.get("/api/grupos/")

        grupos_ids = [
            grupo["id"]
            for grupo in response.data
        ]

        self.assertEqual(
            grupos_ids.count(self.grupo.id),
            1,
        )

    def test_retirado_y_externo_no_ven_actividad(self):
        for usuario in [
            self.damarys,
            self.usuario_externo,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            listado = self.client.get("/api/grupos/")
            grupos_ids = [
                grupo["id"]
                for grupo in listado.data
            ]

            self.assertNotIn(
                self.grupo.id,
                grupos_ids,
            )

            detalle = self.client.get(
                f"/api/grupos/{self.grupo.id}/"
            )

            self.assertEqual(
                detalle.status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_participante_activo_puede_consultar_datos_compartidos(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        rutas = [
            f"/api/grupos/{self.grupo.id}/",
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

    def test_participante_activo_no_puede_administrar_grupo(self):
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

        response_delete = self.client.delete(
            f"/api/grupos/{self.grupo.id}/"
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
            response_patch.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response_delete.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response_agregar.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_participante_activo_puede_registrar_gasto_comun_y_pago(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response_gasto = self.client.post(
            f"/api/grupos/{self.grupo.id}/gastos/",
            {
                "descripcion": "Gasto del participante",
                "monto": "10.00",
                "fecha_gasto": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response_gasto.status_code,
            status.HTTP_201_CREATED,
        )

        gasto = Expense.objects.get(
            grupo=self.grupo,
            descripcion="Gasto del participante",
        )

        self.assertEqual(
            gasto.registrado_por,
            self.carlita,
        )

        self.assertSetEqual(
            set(
                gasto.participantes.values_list(
                    "id",
                    flat=True,
                )
            ),
            {
                self.fernando.id,
                self.carlita.id,
            },
        )

        response_pago = self.client.post(
            f"/api/grupos/{self.grupo.id}/pagos/",
            {
                "monto": "5.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response_pago.status_code,
            status.HTTP_201_CREATED,
        )

class PermisosSegunRolEstadoTest(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc46",
            email="fernando_sc46@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc46",
            email="carlita_sc46@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc46",
            email="damarys_sc46@example.com",
            password="Prueba123",
        )

        self.usuario_externo = User.objects.create_user(
            username="externo_sc46",
            email="externo_sc46@example.com",
            password="Prueba123",
        )

        self.nuevo_usuario = User.objects.create_user(
            username="nuevo_sc46",
            email="nuevo_sc46@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo_activo = Group.objects.create(
            nombre="Actividad activa SC-46",
            descripcion="Actividad con operaciones habilitadas",
            creador=self.fernando,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo_activo.participantes.add(
            self.fernando,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo_activo,
            usuario=self.fernando,
        )

        GroupMembership.objects.create(
            grupo=self.grupo_activo,
            usuario=self.carlita,
        )

        membresia_retirada = GroupMembership.objects.create(
            grupo=self.grupo_activo,
            usuario=self.damarys,
        )
        membresia_retirada.retirar()

        self.grupo_cerrado = Group.objects.create(
            nombre="Actividad cerrada SC-46",
            descripcion="Actividad sin nuevas operaciones",
            creador=self.fernando,
            fecha_inicio=ahora - timedelta(days=3),
            fecha_fin=ahora - timedelta(days=1),
        )

        self.grupo_cerrado.participantes.add(
            self.fernando,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo_cerrado,
            usuario=self.fernando,
        )

        GroupMembership.objects.create(
            grupo=self.grupo_cerrado,
            usuario=self.carlita,
        )

        self.gasto_cerrado = Expense.objects.create(
            grupo=self.grupo_cerrado,
            descripcion="Gasto histórico cerrado",
            monto=Decimal("20.00"),
            registrado_por=self.fernando,
        )

        self.gasto_cerrado.participantes.add(
            self.fernando,
            self.carlita,
        )
        self.gasto_cerrado.calcular_division_equitativa()

    def test_retirado_y_externo_no_pueden_registrar_operaciones(self):
        for usuario in [
            self.damarys,
            self.usuario_externo,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            response_gasto = self.client.post(
                f"/api/grupos/{self.grupo_activo.id}/gastos/",
                {
                    "descripcion": "Operación no autorizada",
                    "monto": "10.00",
                    "fecha_gasto": "2026-07-25",
                },
                format="json",
            )

            response_pago = self.client.post(
                f"/api/grupos/{self.grupo_activo.id}/pagos/",
                {
                    "monto": "5.00",
                    "fecha_pago": "2026-07-25",
                },
                format="json",
            )

            self.assertEqual(
                response_gasto.status_code,
                status.HTTP_404_NOT_FOUND,
            )
            self.assertEqual(
                response_pago.status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_grupo_cerrado_no_permite_registrar_gastos_ni_pagos(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response_gasto = self.client.post(
            f"/api/grupos/{self.grupo_cerrado.id}/gastos/",
            {
                "descripcion": "Gasto posterior al cierre",
                "monto": "10.00",
                "fecha_gasto": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response_gasto.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response_gasto.data["error"],
            (
                "Solo se pueden registrar gastos mientras "
                "la actividad está activa."
            ),
        )

        response_pago = self.client.post(
            f"/api/grupos/{self.grupo_cerrado.id}/pagos/",
            {
                "monto": "5.00",
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response_pago.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_grupo_cerrado_no_permite_cambios_de_participantes(self):
        self.client.force_authenticate(
            user=self.fernando
        )

        response_agregar = self.client.post(
            (
                f"/api/grupos/{self.grupo_cerrado.id}/"
                "participantes/"
            ),
            {
                "usuario_id": self.nuevo_usuario.id,
            },
            format="json",
        )

        response_retirar = self.client.delete(
            (
                f"/api/grupos/{self.grupo_cerrado.id}/"
                f"participantes/{self.carlita.id}/"
            )
        )

        self.assertEqual(
            response_agregar.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response_retirar.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_grupo_cerrado_no_permite_editar_ni_eliminar_gastos(self):
        self.client.force_authenticate(
            user=self.fernando
        )

        response_patch = self.client.patch(
            (
                f"/api/grupos/{self.grupo_cerrado.id}/"
                f"gastos/{self.gasto_cerrado.id}/"
            ),
            {
                "monto": "30.00",
            },
            format="json",
        )

        response_delete = self.client.delete(
            (
                f"/api/grupos/{self.grupo_cerrado.id}/"
                f"gastos/{self.gasto_cerrado.id}/"
            )
        )

        self.assertEqual(
            response_patch.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response_delete.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_creador_puede_editar_datos_generales_de_grupo_cerrado(self):
        self.client.force_authenticate(
            user=self.fernando
        )

        response = self.client.patch(
            f"/api/grupos/{self.grupo_cerrado.id}/",
            {
                "nombre": "Actividad cerrada actualizada",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_participante_no_puede_editar_ni_eliminar_grupo(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        response_patch = self.client.patch(
            f"/api/grupos/{self.grupo_activo.id}/",
            {
                "nombre": "Cambio no autorizado",
            },
            format="json",
        )

        response_delete = self.client.delete(
            f"/api/grupos/{self.grupo_activo.id}/"
        )

        self.assertEqual(
            response_patch.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            response_delete.status_code,
            status.HTTP_404_NOT_FOUND,
        )

class RegistroGastoComunTest(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc47",
            email="fernando_sc47@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc47",
            email="carlita_sc47@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc47",
            email="damarys_sc47@example.com",
            password="Prueba123",
        )

        self.retirado = User.objects.create_user(
            username="retirado_sc47",
            email="retirado_sc47@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo_activo = self.crear_grupo_con_miembros(
            nombre="Actividad activa SC-47",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo_programado = self.crear_grupo_con_miembros(
            nombre="Actividad programada SC-47",
            fecha_inicio=ahora + timedelta(days=1),
            fecha_fin=ahora + timedelta(days=2),
        )

        self.grupo_cerrado = self.crear_grupo_con_miembros(
            nombre="Actividad cerrada SC-47",
            fecha_inicio=ahora - timedelta(days=2),
            fecha_fin=ahora - timedelta(days=1),
        )

        membresia_retirada = GroupMembership.objects.create(
            grupo=self.grupo_activo,
            usuario=self.retirado,
        )
        membresia_retirada.retirar()

        self.client.force_authenticate(
            user=self.carlita
        )

    def crear_grupo_con_miembros(
        self,
        nombre,
        fecha_inicio,
        fecha_fin,
    ):
        grupo = Group.objects.create(
            nombre=nombre,
            descripcion="Pruebas de gasto común",
            creador=self.fernando,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

        grupo.participantes.add(
            self.fernando,
            self.carlita,
            self.damarys,
        )

        for usuario in [
            self.fernando,
            self.carlita,
            self.damarys,
        ]:
            GroupMembership.objects.create(
                grupo=grupo,
                usuario=usuario,
            )

        return grupo

    def test_participante_activo_registra_gasto_comun(self):
        response = self.client.post(
            f"/api/grupos/{self.grupo_activo.id}/gastos/",
            {
                "descripcion": "Transporte",
                "monto": "75.00",
                "fecha_gasto": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        gasto = Expense.objects.get()

        self.assertEqual(
            gasto.registrado_por,
            self.carlita,
        )

        self.assertSetEqual(
            set(
                gasto.participantes.values_list(
                    "id",
                    flat=True,
                )
            ),
            {
                self.fernando.id,
                self.carlita.id,
                self.damarys.id,
            },
        )

        self.assertEqual(
            gasto.divisiones.count(),
            3,
        )

        for division in gasto.divisiones.all():
            self.assertEqual(
                division.monto_asignado,
                Decimal("25.00"),
            )

    def test_campos_antiguos_no_modifican_asociacion_automatica(self):
        response = self.client.post(
            f"/api/grupos/{self.grupo_activo.id}/gastos/",
            {
                "descripcion": "Hospedaje",
                "monto": "90.00",
                "fecha_gasto": "2026-07-25",
                "pagado_por_id": self.retirado.id,
                "participantes_ids": [
                    self.retirado.id,
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        gasto = Expense.objects.get()

        self.assertSetEqual(
            set(
                gasto.participantes.values_list(
                    "id",
                    flat=True,
                )
            ),
            {
                self.fernando.id,
                self.carlita.id,
                self.damarys.id,
            },
        )

        self.assertNotIn(
            "pagado_por",
            response.data["gasto"],
        )

    def test_total_comun_aumenta_inmediatamente(self):
        for descripcion, monto in [
            ("Alimentación", "40.00"),
            ("Entradas", "15.50"),
        ]:
            response = self.client.post(
                f"/api/grupos/{self.grupo_activo.id}/gastos/",
                {
                    "descripcion": descripcion,
                    "monto": monto,
                    "fecha_gasto": "2026-07-25",
                },
                format="json",
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
            )

        detalle = self.client.get(
            f"/api/grupos/{self.grupo_activo.id}/"
        )

        self.assertEqual(
            Decimal(detalle.data["total_gastos"]),
            Decimal("55.50"),
        )

        listado = self.client.get(
            f"/api/grupos/{self.grupo_activo.id}/gastos/"
        )

        self.assertEqual(
            listado.data["total_registros"],
            2,
        )

        self.assertEqual(
            Decimal(listado.data["total_gastos"]),
            Decimal("55.50"),
        )

    def test_grupo_programado_no_permite_registrar_gastos(self):
        response = self.client.post(
            f"/api/grupos/{self.grupo_programado.id}/gastos/",
            {
                "descripcion": "Gasto anticipado",
                "monto": "10.00",
                "fecha_gasto": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["error"],
            (
                "Solo se pueden registrar gastos mientras "
                "la actividad está activa."
            ),
        )

    def test_grupo_cerrado_no_permite_registrar_gastos(self):
        response = self.client.post(
            f"/api/grupos/{self.grupo_cerrado.id}/gastos/",
            {
                "descripcion": "Gasto tardío",
                "monto": "10.00",
                "fecha_gasto": "2026-07-25",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_fecha_del_gasto_es_obligatoria(self):
        response = self.client.post(
            f"/api/grupos/{self.grupo_activo.id}/gastos/",
            {
                "descripcion": "Gasto sin fecha",
                "monto": "10.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "fecha_gasto",
            response.data,
        )


class EditarEliminarGastoSC49Test(APITestCase):

    def setUp(self):
        self.carlita = User.objects.create_user(
            username="carlita_sc49",
            email="carlita_sc49@example.com",
            password="Prueba123",
        )

        self.andres = User.objects.create_user(
            username="andres_sc49",
            email="andres_sc49@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc49",
            email="damarys_sc49@example.com",
            password="Prueba123",
        )

        self.fernando = User.objects.create_user(
            username="fernando_sc49",
            email="fernando_sc49@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo_activo = Group.objects.create(
            nombre="Actividad activa SC-49",
            descripcion="Edición y eliminación de gastos",
            creador=self.carlita,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo_activo.participantes.add(
            self.carlita,
            self.andres,
            self.damarys,
        )

        self.membresias_activas = {}

        for usuario in [
            self.carlita,
            self.andres,
            self.damarys,
        ]:
            self.membresias_activas[usuario.id] = (
                GroupMembership.objects.create(
                    grupo=self.grupo_activo,
                    usuario=usuario,
                )
            )

        self.gasto = Expense.objects.create(
            grupo=self.grupo_activo,
            descripcion="Cena original",
            monto=Decimal("60.00"),
            fecha_gasto="2026-07-20",
            registrado_por=self.carlita,
        )

        self.gasto.sincronizar_integrantes_activos()

        self.gasto_secundario = Expense.objects.create(
            grupo=self.grupo_activo,
            descripcion="Transporte",
            monto=Decimal("15.00"),
            fecha_gasto="2026-07-21",
            registrado_por=self.andres,
        )

        self.gasto_secundario.sincronizar_integrantes_activos()

        self.grupo_cerrado = Group.objects.create(
            nombre="Actividad cerrada SC-49",
            descripcion="Gastos históricos protegidos",
            creador=self.carlita,
            fecha_inicio=ahora - timedelta(days=3),
            fecha_fin=ahora - timedelta(days=1),
        )

        self.grupo_cerrado.participantes.add(
            self.carlita,
            self.andres,
        )

        for usuario in [
            self.carlita,
            self.andres,
        ]:
            GroupMembership.objects.create(
                grupo=self.grupo_cerrado,
                usuario=usuario,
            )

        self.gasto_cerrado = Expense.objects.create(
            grupo=self.grupo_cerrado,
            descripcion="Gasto histórico",
            monto=Decimal("20.00"),
            fecha_gasto="2026-07-18",
            registrado_por=self.carlita,
        )

        self.gasto_cerrado.sincronizar_integrantes_activos()

        self.client.force_authenticate(
            user=self.carlita
        )

    def url_gasto(self, grupo, gasto):
        return (
            f"/api/grupos/{grupo.id}/"
            f"gastos/{gasto.id}/"
        )

    def test_creador_edita_descripcion_y_fecha_preservando_division(
        self,
    ):
        participantes_originales = set(
            self.gasto.participantes.values_list(
                "id",
                flat=True,
            )
        )

        divisiones_originales = {
            division.participante_id: division.monto_asignado
            for division in self.gasto.divisiones.all()
        }

        response = self.client.patch(
            self.url_gasto(
                self.grupo_activo,
                self.gasto,
            ),
            {
                "descripcion": "Cena actualizada",
                "fecha_gasto": "2026-07-22",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.gasto.refresh_from_db()

        self.assertEqual(
            self.gasto.descripcion,
            "Cena actualizada",
        )

        self.assertEqual(
            self.gasto.fecha_gasto.isoformat(),
            "2026-07-22",
        )

        self.assertSetEqual(
            set(
                self.gasto.participantes.values_list(
                    "id",
                    flat=True,
                )
            ),
            participantes_originales,
        )

        self.assertDictEqual(
            {
                division.participante_id: division.monto_asignado
                for division in self.gasto.divisiones.all()
            },
            divisiones_originales,
        )

    def test_editar_monto_recalcula_solo_participantes_originales(
        self,
    ):
        participantes_originales = set(
            self.gasto.participantes.values_list(
                "id",
                flat=True,
            )
        )

        self.grupo_activo.participantes.add(
            self.fernando
        )

        GroupMembership.objects.create(
            grupo=self.grupo_activo,
            usuario=self.fernando,
        )

        response = self.client.patch(
            self.url_gasto(
                self.grupo_activo,
                self.gasto,
            ),
            {
                "monto": "100.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        participantes_recalculados = set(
            self.gasto.divisiones.values_list(
                "participante_id",
                flat=True,
            )
        )

        self.assertSetEqual(
            participantes_recalculados,
            participantes_originales,
        )

        self.assertNotIn(
            self.fernando.id,
            participantes_recalculados,
        )

        montos = list(
            self.gasto.divisiones
            .order_by("participante_id")
            .values_list(
                "monto_asignado",
                flat=True,
            )
        )

        self.assertEqual(
            montos,
            [
                Decimal("33.34"),
                Decimal("33.33"),
                Decimal("33.33"),
            ],
        )

        self.assertEqual(
            sum(montos, Decimal("0.00")),
            Decimal("100.00"),
        )

    def test_retirar_integrante_despues_preserva_su_division_al_editar(
        self,
    ):
        self.membresias_activas[
            self.damarys.id
        ].retirar()

        self.grupo_activo.participantes.remove(
            self.damarys
        )

        response = self.client.patch(
            self.url_gasto(
                self.grupo_activo,
                self.gasto,
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

        self.assertTrue(
            self.gasto.participantes.filter(
                id=self.damarys.id
            ).exists()
        )

        self.assertTrue(
            self.gasto.divisiones.filter(
                participante=self.damarys
            ).exists()
        )

        montos = list(
            self.gasto.divisiones.values_list(
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

    def test_campos_de_participantes_enviados_manualmente_son_ignorados(
        self,
    ):
        response = self.client.patch(
            self.url_gasto(
                self.grupo_activo,
                self.gasto,
            ),
            {
                "monto": "90.00",
                "participantes_ids": [
                    self.carlita.id,
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertSetEqual(
            set(
                self.gasto.participantes.values_list(
                    "id",
                    flat=True,
                )
            ),
            {
                self.carlita.id,
                self.andres.id,
                self.damarys.id,
            },
        )

        self.assertEqual(
            self.gasto.divisiones.count(),
            3,
        )

    def test_editar_monto_actualiza_total_comun_inmediatamente(self):
        response = self.client.patch(
            self.url_gasto(
                self.grupo_activo,
                self.gasto,
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

        self.assertEqual(
            self.grupo_activo.total_gastos,
            Decimal("105.00"),
        )

        detalle_grupo = self.client.get(
            f"/api/grupos/{self.grupo_activo.id}/"
        )

        self.assertEqual(
            Decimal(detalle_grupo.data["total_gastos"]),
            Decimal("105.00"),
        )

    def test_participante_no_creador_no_puede_editar_ni_eliminar(
        self,
    ):
        self.client.force_authenticate(
            user=self.andres
        )

        response_patch = self.client.patch(
            self.url_gasto(
                self.grupo_activo,
                self.gasto,
            ),
            {
                "monto": "90.00",
            },
            format="json",
        )

        response_delete = self.client.delete(
            self.url_gasto(
                self.grupo_activo,
                self.gasto,
            )
        )

        self.assertEqual(
            response_patch.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response_delete.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.gasto.refresh_from_db()

        self.assertEqual(
            self.gasto.monto,
            Decimal("60.00"),
        )

        self.assertTrue(
            Expense.objects.filter(
                id=self.gasto.id
            ).exists()
        )

    def test_eliminar_gasto_elimina_divisiones_y_actualiza_total(
        self,
    ):
        gasto_id = self.gasto.id

        divisiones_ids = list(
            self.gasto.divisiones.values_list(
                "id",
                flat=True,
            )
        )

        self.assertEqual(
            self.grupo_activo.total_gastos,
            Decimal("75.00"),
        )

        response = self.client.delete(
            self.url_gasto(
                self.grupo_activo,
                self.gasto,
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            Expense.objects.filter(
                id=gasto_id
            ).exists()
        )

        self.assertFalse(
            ExpenseDivision.objects.filter(
                id__in=divisiones_ids
            ).exists()
        )

        self.assertEqual(
            self.grupo_activo.total_gastos,
            Decimal("15.00"),
        )

        detalle_grupo = self.client.get(
            f"/api/grupos/{self.grupo_activo.id}/"
        )

        self.assertEqual(
            Decimal(detalle_grupo.data["total_gastos"]),
            Decimal("15.00"),
        )

    def test_actividad_cerrada_bloquea_edicion_y_eliminacion(
        self,
    ):
        response_patch = self.client.patch(
            self.url_gasto(
                self.grupo_cerrado,
                self.gasto_cerrado,
            ),
            {
                "monto": "30.00",
            },
            format="json",
        )

        response_delete = self.client.delete(
            self.url_gasto(
                self.grupo_cerrado,
                self.gasto_cerrado,
            )
        )

        self.assertEqual(
            response_patch.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response_delete.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.gasto_cerrado.refresh_from_db()

        self.assertEqual(
            self.gasto_cerrado.monto,
            Decimal("20.00"),
        )

        self.assertTrue(
            Expense.objects.filter(
                id=self.gasto_cerrado.id
            ).exists()
        )


class ResumenEconomicoCuotasSC50Test(APITestCase):

    def setUp(self):
        self.carlita = User.objects.create_user(
            username="carlita_sc50",
            email="carlita_sc50@example.com",
            password="Prueba123",
        )

        self.andres = User.objects.create_user(
            username="andres_sc50",
            email="andres_sc50@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc50",
            email="damarys_sc50@example.com",
            password="Prueba123",
        )

        self.usuario_externo = User.objects.create_user(
            username="externo_sc50",
            email="externo_sc50@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad económica SC-50",
            descripcion="Resumen de gastos y cuotas",
            creador=self.carlita,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
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

        self.gasto_uno = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Hospedaje",
            monto=Decimal("60.00"),
            fecha_gasto="2026-07-20",
            registrado_por=self.carlita,
        )
        self.gasto_uno.sincronizar_integrantes_activos()

        self.membresia_damarys.retirar()
        self.grupo.participantes.remove(
            self.damarys
        )

        self.gasto_dos = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Transporte",
            monto=Decimal("30.00"),
            fecha_gasto="2026-07-21",
            registrado_por=self.andres,
        )
        self.gasto_dos.sincronizar_integrantes_activos()

        Payment.objects.create(
            grupo=self.grupo,
            pagador=self.carlita,
            monto=Decimal("10.00"),
            fecha_pago="2026-07-22",
            registrado_por=self.carlita,
        )

        self.url = (
            f"/api/grupos/{self.grupo.id}/"
            "resumen-economico/"
        )

        self.client.force_authenticate(
            user=self.carlita
        )

    def obtener_cuotas_por_usuario(self, response):
        return {
            cuota["participante"]["username"]: cuota
            for cuota in response.data["cuotas"]
        }

    def test_creador_consulta_resumen_economico_completo(self):
        response = self.client.get(
            self.url
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
            "Actividad económica SC-50",
        )

        self.assertEqual(
            response.data["estado_actividad"],
            Group.ESTADO_ACTIVA,
        )

        resumen = response.data["resumen"]

        self.assertEqual(
            Decimal(resumen["total_gastos"]),
            Decimal("90.00"),
        )

        self.assertEqual(
            resumen["cantidad_gastos"],
            2,
        )

        self.assertEqual(
            Decimal(resumen["total_cuotas"]),
            Decimal("90.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_aportado"]),
            Decimal("10.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_pendiente"]),
            Decimal("80.00"),
        )

        self.assertEqual(
            response.data["total_participantes"],
            3,
        )

    def test_muestra_cuotas_individuales_y_saldos_pendientes(self):
        response = self.client.get(
            self.url
        )

        cuotas = self.obtener_cuotas_por_usuario(
            response
        )

        self.assertEqual(
            Decimal(
                cuotas["carlita_sc50"]["cuota_total"]
            ),
            Decimal("35.00"),
        )

        self.assertEqual(
            Decimal(
                cuotas["carlita_sc50"]["total_aportado"]
            ),
            Decimal("10.00"),
        )

        self.assertEqual(
            Decimal(
                cuotas["carlita_sc50"]["saldo_pendiente"]
            ),
            Decimal("25.00"),
        )

        self.assertEqual(
            cuotas["carlita_sc50"]["estado"],
            "pendiente",
        )

        self.assertEqual(
            Decimal(
                cuotas["andres_sc50"]["cuota_total"]
            ),
            Decimal("35.00"),
        )

        self.assertEqual(
            Decimal(
                cuotas["andres_sc50"]["total_aportado"]
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(
                cuotas["andres_sc50"]["saldo_pendiente"]
            ),
            Decimal("35.00"),
        )

    def test_participante_retirado_conserva_cuota_historica(self):
        response = self.client.get(
            self.url
        )

        cuotas = self.obtener_cuotas_por_usuario(
            response
        )

        cuota_damarys = cuotas[
            "damarys_sc50"
        ]

        self.assertFalse(
            cuota_damarys["activo"]
        )

        self.assertEqual(
            Decimal(
                cuota_damarys["cuota_total"]
            ),
            Decimal("20.00"),
        )

        self.assertEqual(
            Decimal(
                cuota_damarys["total_aportado"]
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(
                cuota_damarys["saldo_pendiente"]
            ),
            Decimal("20.00"),
        )

        self.assertEqual(
            cuota_damarys["estado"],
            "pendiente",
        )

    def test_suma_de_cuotas_coincide_con_total_de_gastos(self):
        response = self.client.get(
            self.url
        )

        total_cuotas_individuales = sum(
            (
                Decimal(
                    cuota["cuota_total"]
                )
                for cuota in response.data["cuotas"]
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            total_cuotas_individuales,
            Decimal("90.00"),
        )

        self.assertEqual(
            total_cuotas_individuales,
            Decimal(
                response.data["resumen"]["total_gastos"]
            ),
        )

        for cuota in response.data["cuotas"]:
            self.assertRegex(
                cuota["cuota_total"],
                r"^\d+\.\d{2}$",
            )

            self.assertRegex(
                cuota["total_aportado"],
                r"^\d+\.\d{2}$",
            )

            self.assertRegex(
                cuota["saldo_pendiente"],
                r"^\d+\.\d{2}$",
            )

    def test_participante_activo_puede_consultar_resumen(self):
        self.client.force_authenticate(
            user=self.andres
        )

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_retirado_y_externo_no_pueden_consultar_resumen(self):
        for usuario in [
            self.damarys,
            self.usuario_externo,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            response = self.client.get(
                self.url
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_resumen_se_actualiza_al_editar_y_eliminar_gastos(self):
        response_editar = self.client.patch(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"gastos/{self.gasto_dos.id}/"
            ),
            {
                "monto": "40.00",
            },
            format="json",
        )

        self.assertEqual(
            response_editar.status_code,
            status.HTTP_200_OK,
        )

        resumen_editado = self.client.get(
            self.url
        )

        self.assertEqual(
            Decimal(
                resumen_editado.data[
                    "resumen"
                ]["total_gastos"]
            ),
            Decimal("100.00"),
        )

        self.assertEqual(
            Decimal(
                resumen_editado.data[
                    "resumen"
                ]["total_cuotas"]
            ),
            Decimal("100.00"),
        )

        response_eliminar = self.client.delete(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"gastos/{self.gasto_dos.id}/"
            )
        )

        self.assertEqual(
            response_eliminar.status_code,
            status.HTTP_200_OK,
        )

        resumen_eliminado = self.client.get(
            self.url
        )

        self.assertEqual(
            Decimal(
                resumen_eliminado.data[
                    "resumen"
                ]["total_gastos"]
            ),
            Decimal("60.00"),
        )

        self.assertEqual(
            resumen_eliminado.data[
                "resumen"
            ]["cantidad_gastos"],
            1,
        )

        self.assertEqual(
            Decimal(
                resumen_eliminado.data[
                    "resumen"
                ]["total_cuotas"]
            ),
            Decimal("60.00"),
        )

    def test_actividad_cerrada_conserva_resumen_historico(self):
        ahora = timezone.now()

        grupo_cerrado = Group.objects.create(
            nombre="Actividad cerrada SC-50",
            descripcion="Resumen histórico disponible",
            creador=self.carlita,
            fecha_inicio=ahora - timedelta(days=3),
            fecha_fin=ahora - timedelta(days=1),
        )

        grupo_cerrado.participantes.add(
            self.carlita,
            self.andres,
        )

        GroupMembership.objects.create(
            grupo=grupo_cerrado,
            usuario=self.carlita,
        )

        GroupMembership.objects.create(
            grupo=grupo_cerrado,
            usuario=self.andres,
        )

        gasto_cerrado = Expense.objects.create(
            grupo=grupo_cerrado,
            descripcion="Gasto final",
            monto=Decimal("20.00"),
            fecha_gasto="2026-07-18",
            registrado_por=self.carlita,
        )
        gasto_cerrado.sincronizar_integrantes_activos()

        response = self.client.get(
            (
                f"/api/grupos/{grupo_cerrado.id}/"
                "resumen-economico/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["estado_actividad"],
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            Decimal(
                response.data["resumen"]["total_gastos"]
            ),
            Decimal("20.00"),
        )

        self.assertEqual(
            Decimal(
                response.data["resumen"]["total_cuotas"]
            ),
            Decimal("20.00"),
        )


class ValidacionSaldoPendienteSC52Test(APITestCase):

    def setUp(self):
        self.damarys = User.objects.create_user(
            username="damarys_sc52",
            email="damarys_sc52@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc52",
            email="carlita_sc52@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad activa SC-52",
            descripcion="Validación de pagos contra saldo pendiente",
            creador=self.damarys,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo.participantes.add(
            self.damarys,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.damarys,
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.carlita,
        )

        self.gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Hospedaje SC-52",
            monto=Decimal("40.00"),
            fecha_gasto="2026-07-25",
            registrado_por=self.damarys,
        )
        self.gasto.sincronizar_integrantes_activos()

        self.url = (
            f"/api/grupos/{self.grupo.id}/pagos/"
        )

        self.client.force_authenticate(
            user=self.damarys
        )

    def registrar_pago(self, monto):
        return self.client.post(
            self.url,
            {
                "monto": monto,
                "fecha_pago": "2026-07-25",
            },
            format="json",
        )

    def obtener_cuota_usuario(self, username):
        response = self.client.get(
            (
                f"/api/grupos/{self.grupo.id}/"
                "resumen-economico/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        return next(
            cuota
            for cuota in response.data["cuotas"]
            if cuota["participante"]["username"] == username
        )

    def test_permite_pagos_parciales_hasta_cubrir_la_cuota(self):
        primer_pago = self.registrar_pago(
            "8.00"
        )

        segundo_pago = self.registrar_pago(
            "7.00"
        )

        self.assertEqual(
            primer_pago.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            segundo_pago.status_code,
            status.HTTP_201_CREATED,
        )

        total_pagado = sum(
            Payment.objects.filter(
                grupo=self.grupo,
                pagador=self.damarys,
            ).values_list(
                "monto",
                flat=True,
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            total_pagado,
            Decimal("15.00"),
        )

        cuota = self.obtener_cuota_usuario(
            "damarys_sc52"
        )

        self.assertEqual(
            Decimal(cuota["saldo_pendiente"]),
            Decimal("5.00"),
        )

        self.assertEqual(
            cuota["estado"],
            "pendiente",
        )

    def test_rechaza_pago_mayor_al_saldo_pendiente(self):
        pago_inicial = self.registrar_pago(
            "15.00"
        )

        self.assertEqual(
            pago_inicial.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.registrar_pago(
            "5.01"
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
            str(response.data["monto"][0]),
            (
                "El monto del pago no puede superar "
                "tu saldo pendiente de $5.00."
            ),
        )

        self.assertEqual(
            Payment.objects.filter(
                grupo=self.grupo,
                pagador=self.damarys,
            ).count(),
            1,
        )

    def test_permite_pago_igual_al_saldo_pendiente(self):
        primer_pago = self.registrar_pago(
            "15.00"
        )

        segundo_pago = self.registrar_pago(
            "5.00"
        )

        self.assertEqual(
            primer_pago.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            segundo_pago.status_code,
            status.HTTP_201_CREATED,
        )

        cuota = self.obtener_cuota_usuario(
            "damarys_sc52"
        )

        self.assertEqual(
            Decimal(cuota["cuota_total"]),
            Decimal("20.00"),
        )

        self.assertEqual(
            Decimal(cuota["total_aportado"]),
            Decimal("20.00"),
        )

        self.assertEqual(
            Decimal(cuota["saldo_pendiente"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            cuota["estado"],
            "saldado",
        )

    def test_usuario_saldado_no_puede_registrar_otro_pago(self):
        pago_completo = self.registrar_pago(
            "20.00"
        )

        self.assertEqual(
            pago_completo.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.registrar_pago(
            "1.00"
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
            str(response.data["monto"][0]),
            "Tu cuota ya se encuentra saldada.",
        )

        self.assertEqual(
            Payment.objects.filter(
                grupo=self.grupo,
                pagador=self.damarys,
            ).count(),
            1,
        )

    def test_validacion_es_independiente_para_cada_participante(self):
        pago_damarys = self.registrar_pago(
            "20.00"
        )

        self.assertEqual(
            pago_damarys.status_code,
            status.HTTP_201_CREATED,
        )

        self.client.force_authenticate(
            user=self.carlita
        )

        pago_carlita = self.registrar_pago(
            "10.00"
        )

        self.assertEqual(
            pago_carlita.status_code,
            status.HTTP_201_CREATED,
        )

        cuota_carlita = self.obtener_cuota_usuario(
            "carlita_sc52"
        )

        self.assertEqual(
            Decimal(cuota_carlita["cuota_total"]),
            Decimal("20.00"),
        )

        self.assertEqual(
            Decimal(cuota_carlita["total_aportado"]),
            Decimal("10.00"),
        )

        self.assertEqual(
            Decimal(cuota_carlita["saldo_pendiente"]),
            Decimal("10.00"),
        )

        self.assertEqual(
            cuota_carlita["estado"],
            "pendiente",
        )

    def test_aumento_de_gasto_habilita_nuevo_saldo_pendiente(self):
        pago_inicial = self.registrar_pago(
            "20.00"
        )

        self.assertEqual(
            pago_inicial.status_code,
            status.HTTP_201_CREATED,
        )

        response_edicion = self.client.patch(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"gastos/{self.gasto.id}/"
            ),
            {
                "monto": "60.00",
            },
            format="json",
        )

        self.assertEqual(
            response_edicion.status_code,
            status.HTTP_200_OK,
        )

        nuevo_pago = self.registrar_pago(
            "10.00"
        )

        self.assertEqual(
            nuevo_pago.status_code,
            status.HTTP_201_CREATED,
        )

        cuota = self.obtener_cuota_usuario(
            "damarys_sc52"
        )

        self.assertEqual(
            Decimal(cuota["cuota_total"]),
            Decimal("30.00"),
        )

        self.assertEqual(
            Decimal(cuota["total_aportado"]),
            Decimal("30.00"),
        )

        self.assertEqual(
            Decimal(cuota["saldo_pendiente"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            cuota["estado"],
            "saldado",
        )

    def test_pago_rechazado_no_modifica_resumen_economico(self):
        pago_inicial = self.registrar_pago(
            "12.00"
        )

        self.assertEqual(
            pago_inicial.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.registrar_pago(
            "8.01"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        cuota = self.obtener_cuota_usuario(
            "damarys_sc52"
        )

        self.assertEqual(
            Decimal(cuota["total_aportado"]),
            Decimal("12.00"),
        )

        self.assertEqual(
            Decimal(cuota["saldo_pendiente"]),
            Decimal("8.00"),
        )

        self.assertEqual(
            Payment.objects.filter(
                grupo=self.grupo,
                pagador=self.damarys,
            ).count(),
            1,
        )


class ListarDetallePagosSC53Test(APITestCase):

    def setUp(self):
        self.damarys = User.objects.create_user(
            username="damarys_sc53",
            email="damarys_sc53@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc53",
            email="carlita_sc53@example.com",
            password="Prueba123",
        )

        self.fernando = User.objects.create_user(
            username="fernando_sc53",
            email="fernando_sc53@example.com",
            password="Prueba123",
        )

        self.usuario_externo = User.objects.create_user(
            username="externo_sc53",
            email="externo_sc53@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad de pagos SC-53",
            descripcion="Listado y detalle de pagos",
            creador=self.damarys,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo.participantes.add(
            self.damarys,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.damarys,
        )

        GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.carlita,
        )

        membresia_retirada = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.fernando,
        )
        membresia_retirada.retirar()

        self.pago_antiguo = Payment.objects.create(
            grupo=self.grupo,
            pagador=self.damarys,
            monto=Decimal("5.00"),
            fecha_pago="2026-07-24",
            registrado_por=self.damarys,
        )

        self.pago_reciente = Payment.objects.create(
            grupo=self.grupo,
            pagador=self.carlita,
            monto=Decimal("12.50"),
            fecha_pago="2026-07-25",
            registrado_por=self.carlita,
        )

        fecha_antigua = ahora - timedelta(hours=2)
        fecha_reciente = ahora - timedelta(hours=1)

        Payment.objects.filter(
            id=self.pago_antiguo.id
        ).update(
            fecha_registro=fecha_antigua
        )

        Payment.objects.filter(
            id=self.pago_reciente.id
        ).update(
            fecha_registro=fecha_reciente
        )

        self.pago_antiguo.refresh_from_db()
        self.pago_reciente.refresh_from_db()

        self.otro_grupo = Group.objects.create(
            nombre="Otra actividad SC-53",
            descripcion="Actividad diferente",
            creador=self.damarys,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.otro_grupo.participantes.add(
            self.damarys
        )

        GroupMembership.objects.create(
            grupo=self.otro_grupo,
            usuario=self.damarys,
        )

        self.pago_otro_grupo = Payment.objects.create(
            grupo=self.otro_grupo,
            pagador=self.damarys,
            monto=Decimal("9.75"),
            fecha_pago="2026-07-25",
            registrado_por=self.damarys,
        )

        self.grupo_cerrado = Group.objects.create(
            nombre="Actividad cerrada SC-53",
            descripcion="Historial de pagos disponible",
            creador=self.damarys,
            fecha_inicio=ahora - timedelta(days=3),
            fecha_fin=ahora - timedelta(days=1),
        )

        self.grupo_cerrado.participantes.add(
            self.damarys,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo_cerrado,
            usuario=self.damarys,
        )

        GroupMembership.objects.create(
            grupo=self.grupo_cerrado,
            usuario=self.carlita,
        )

        self.pago_cerrado = Payment.objects.create(
            grupo=self.grupo_cerrado,
            pagador=self.carlita,
            monto=Decimal("20.00"),
            fecha_pago="2026-07-20",
            registrado_por=self.carlita,
        )

        self.url_listado = (
            f"/api/grupos/{self.grupo.id}/pagos/"
        )

        self.client.force_authenticate(
            user=self.damarys
        )

    def url_detalle(self, grupo, pago):
        return (
            f"/api/grupos/{grupo.id}/"
            f"pagos/{pago.id}/"
        )

    def test_creador_puede_listar_pagos_de_la_actividad(self):
        response = self.client.get(
            self.url_listado
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
            "Actividad de pagos SC-53",
        )

        self.assertEqual(
            response.data["estado_actividad"],
            Group.ESTADO_ACTIVA,
        )

        self.assertEqual(
            response.data["total_registros"],
            2,
        )

        self.assertEqual(
            response.data["mensaje"],
            "Pagos consultados correctamente.",
        )

    def test_participante_activo_puede_listar_y_consultar_detalle(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        listado = self.client.get(
            self.url_listado
        )

        detalle = self.client.get(
            self.url_detalle(
                self.grupo,
                self.pago_antiguo,
            )
        )

        self.assertEqual(
            listado.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            detalle.status_code,
            status.HTTP_200_OK,
        )

    def test_listado_muestra_campos_y_orden_mas_reciente(self):
        response = self.client.get(
            self.url_listado
        )

        pagos = response.data["pagos"]

        self.assertEqual(
            len(pagos),
            2,
        )

        self.assertEqual(
            pagos[0]["id"],
            self.pago_reciente.id,
        )

        self.assertEqual(
            pagos[1]["id"],
            self.pago_antiguo.id,
        )

        self.assertEqual(
            pagos[0]["pagador"]["username"],
            "carlita_sc53",
        )

        self.assertEqual(
            pagos[0]["monto"],
            "12.50",
        )

        self.assertEqual(
            pagos[1]["monto"],
            "5.00",
        )

        for pago in pagos:
            self.assertIn(
                "fecha_pago",
                pago,
            )

            self.assertIn(
                "fecha_registro",
                pago,
            )

            self.assertIn(
                "registrado_por",
                pago,
            )

            self.assertRegex(
                pago["monto"],
                r"^\d+\.\d{2}$",
            )

    def test_detalle_muestra_toda_la_informacion_del_pago(self):
        response = self.client.get(
            self.url_detalle(
                self.grupo,
                self.pago_reciente,
            )
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
            "Actividad de pagos SC-53",
        )

        pago = response.data["pago"]

        self.assertEqual(
            pago["id"],
            self.pago_reciente.id,
        )

        self.assertEqual(
            pago["grupo"],
            self.grupo.id,
        )

        self.assertEqual(
            pago["pagador"]["username"],
            "carlita_sc53",
        )

        self.assertEqual(
            pago["monto"],
            "12.50",
        )

        self.assertEqual(
            pago["fecha_pago"],
            "2026-07-25",
        )

        self.assertEqual(
            pago["registrado_por"]["username"],
            "carlita_sc53",
        )

        self.assertIsNotNone(
            pago["fecha_registro"]
        )

    def test_actividad_cerrada_conserva_historial_de_pagos(self):
        self.client.force_authenticate(
            user=self.carlita
        )

        listado = self.client.get(
            (
                f"/api/grupos/{self.grupo_cerrado.id}/"
                "pagos/"
            )
        )

        detalle = self.client.get(
            self.url_detalle(
                self.grupo_cerrado,
                self.pago_cerrado,
            )
        )

        self.assertEqual(
            listado.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            listado.data["estado_actividad"],
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            listado.data["total_registros"],
            1,
        )

        self.assertEqual(
            detalle.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            detalle.data["estado_actividad"],
            Group.ESTADO_CERRADA,
        )

    def test_retirado_y_externo_no_pueden_consultar_pagos(self):
        for usuario in [
            self.fernando,
            self.usuario_externo,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            listado = self.client.get(
                self.url_listado
            )

            detalle = self.client.get(
                self.url_detalle(
                    self.grupo,
                    self.pago_reciente,
                )
            )

            self.assertEqual(
                listado.status_code,
                status.HTTP_404_NOT_FOUND,
            )

            self.assertEqual(
                detalle.status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_pago_inexistente_o_de_otra_actividad_responde_404(self):
        pago_inexistente = self.client.get(
            (
                f"/api/grupos/{self.grupo.id}/"
                "pagos/999999/"
            )
        )

        pago_otra_actividad = self.client.get(
            self.url_detalle(
                self.grupo,
                self.pago_otro_grupo,
            )
        )

        self.assertEqual(
            pago_inexistente.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            pago_otra_actividad.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            pago_otra_actividad.data["error"],
            (
                "El pago no existe o no pertenece "
                "a esta actividad."
            ),
        )

    def test_listado_vacio_devuelve_mensaje_informativo(self):
        ahora = timezone.now()

        grupo_sin_pagos = Group.objects.create(
            nombre="Actividad sin pagos SC-53",
            descripcion="Listado vacío",
            creador=self.damarys,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        grupo_sin_pagos.participantes.add(
            self.damarys
        )

        GroupMembership.objects.create(
            grupo=grupo_sin_pagos,
            usuario=self.damarys,
        )

        response = self.client.get(
            (
                f"/api/grupos/{grupo_sin_pagos.id}/"
                "pagos/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_registros"],
            0,
        )

        self.assertEqual(
            response.data["pagos"],
            [],
        )

        self.assertEqual(
            response.data["mensaje"],
            "Todavía no existen pagos registrados.",
        )


class CentroNotificacionesSC54Test(APITestCase):

    def setUp(self):
        self.damarys = User.objects.create_user(
            username="damarys_sc54",
            email="damarys_sc54@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc54",
            email="carlita_sc54@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.notificacion_antigua = Notification.objects.create(
            usuario=self.damarys,
            titulo="Actividad creada",
            mensaje=(
                "La actividad Viaje SC-54 fue creada "
                "correctamente."
            ),
            enlace="/grupos/10",
        )

        self.notificacion_leida = Notification.objects.create(
            usuario=self.damarys,
            titulo="Pago registrado",
            mensaje="Tu aporte fue registrado correctamente.",
            enlace="/grupos/10",
            leida=True,
            fecha_lectura=ahora - timedelta(minutes=20),
        )

        self.notificacion_reciente = Notification.objects.create(
            usuario=self.damarys,
            titulo="Nuevo gasto",
            mensaje=(
                "Se registró un nuevo gasto en la actividad."
            ),
            enlace="/grupos/10",
        )

        Notification.objects.filter(
            id=self.notificacion_antigua.id
        ).update(
            fecha_creacion=ahora - timedelta(hours=3)
        )

        Notification.objects.filter(
            id=self.notificacion_leida.id
        ).update(
            fecha_creacion=ahora - timedelta(hours=2)
        )

        Notification.objects.filter(
            id=self.notificacion_reciente.id
        ).update(
            fecha_creacion=ahora - timedelta(hours=1)
        )

        self.notificacion_ajena = Notification.objects.create(
            usuario=self.carlita,
            titulo="Notificación privada de Carlita",
            mensaje="Este mensaje solo pertenece a Carlita.",
            enlace="/grupos/20",
        )

        self.url_listado = "/api/notificaciones/"
        self.url_marcar_todas = (
            "/api/notificaciones/marcar-todas-leidas/"
        )

        self.client.force_authenticate(
            user=self.damarys
        )

    def url_marcar_leida(self, notificacion):
        return (
            f"/api/notificaciones/"
            f"{notificacion.id}/leer/"
        )

    def test_usuario_autenticado_consulta_su_centro_personal(self):
        response = self.client.get(
            self.url_listado
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_notificaciones"],
            3,
        )

        self.assertEqual(
            response.data["no_leidas"],
            2,
        )

        usuarios = {
            item["usuario"]["username"]
            for item in response.data["notificaciones"]
        }

        self.assertSetEqual(
            usuarios,
            {"damarys_sc54"},
        )

        ids = {
            item["id"]
            for item in response.data["notificaciones"]
        }

        self.assertNotIn(
            self.notificacion_ajena.id,
            ids,
        )

    def test_notificaciones_se_ordenan_desde_la_mas_reciente(self):
        response = self.client.get(
            self.url_listado
        )

        ids = [
            item["id"]
            for item in response.data["notificaciones"]
        ]

        self.assertEqual(
            ids,
            [
                self.notificacion_reciente.id,
                self.notificacion_leida.id,
                self.notificacion_antigua.id,
            ],
        )

    def test_notificacion_contiene_campos_estado_y_enlace(self):
        response = self.client.get(
            self.url_listado
        )

        notificaciones = {
            item["id"]: item
            for item in response.data["notificaciones"]
        }

        no_leida = notificaciones[
            self.notificacion_reciente.id
        ]

        leida = notificaciones[
            self.notificacion_leida.id
        ]

        for item in [
            no_leida,
            leida,
        ]:
            self.assertIn(
                "titulo",
                item,
            )
            self.assertIn(
                "mensaje",
                item,
            )
            self.assertIn(
                "fecha_creacion",
                item,
            )
            self.assertIn(
                "leida",
                item,
            )
            self.assertIn(
                "estado",
                item,
            )
            self.assertIn(
                "enlace",
                item,
            )

        self.assertEqual(
            no_leida["titulo"],
            "Nuevo gasto",
        )

        self.assertEqual(
            no_leida["enlace"],
            "/grupos/10",
        )

        self.assertFalse(
            no_leida["leida"]
        )

        self.assertEqual(
            no_leida["estado"],
            "no_leida",
        )

        self.assertIsNone(
            no_leida["fecha_lectura"]
        )

        self.assertTrue(
            leida["leida"]
        )

        self.assertEqual(
            leida["estado"],
            "leida",
        )

        self.assertIsNotNone(
            leida["fecha_lectura"]
        )

    def test_usuario_marca_una_notificacion_como_leida(self):
        response = self.client.patch(
            self.url_marcar_leida(
                self.notificacion_reciente
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["mensaje"],
            "Notificación marcada como leída.",
        )

        self.assertEqual(
            response.data["no_leidas"],
            1,
        )

        self.notificacion_reciente.refresh_from_db()

        self.assertTrue(
            self.notificacion_reciente.leida
        )

        self.assertIsNotNone(
            self.notificacion_reciente.fecha_lectura
        )

        self.assertTrue(
            response.data["notificacion"]["leida"]
        )

        self.assertEqual(
            response.data["notificacion"]["estado"],
            "leida",
        )

    def test_marcar_notificacion_leida_es_idempotente(self):
        response = self.client.patch(
            self.url_marcar_leida(
                self.notificacion_leida
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["mensaje"],
            "La notificación ya estaba leída.",
        )

        self.assertEqual(
            response.data["no_leidas"],
            2,
        )

    def test_usuario_puede_marcar_todas_sus_notificaciones_leidas(self):
        response = self.client.patch(
            self.url_marcar_todas,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["actualizadas"],
            2,
        )

        self.assertEqual(
            response.data["no_leidas"],
            0,
        )

        self.assertFalse(
            Notification.objects.filter(
                usuario=self.damarys,
                leida=False,
            ).exists()
        )

        self.assertEqual(
            Notification.objects.filter(
                usuario=self.damarys,
                leida=True,
                fecha_lectura__isnull=False,
            ).count(),
            3,
        )

    def test_marcar_todas_no_modifica_notificaciones_ajenas(self):
        self.client.patch(
            self.url_marcar_todas,
            {},
            format="json",
        )

        self.notificacion_ajena.refresh_from_db()

        self.assertFalse(
            self.notificacion_ajena.leida
        )

        self.assertIsNone(
            self.notificacion_ajena.fecha_lectura
        )

    def test_usuario_no_puede_modificar_notificacion_ajena(self):
        response = self.client.patch(
            self.url_marcar_leida(
                self.notificacion_ajena
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            response.data["error"],
            "Notificación no encontrada.",
        )

        self.notificacion_ajena.refresh_from_db()

        self.assertFalse(
            self.notificacion_ajena.leida
        )

        self.assertIsNone(
            self.notificacion_ajena.fecha_lectura
        )

    def test_centro_vacio_muestra_mensaje_informativo(self):
        usuario_sin_notificaciones = User.objects.create_user(
            username="sin_notificaciones_sc54",
            email="sin_notificaciones_sc54@example.com",
            password="Prueba123",
        )

        self.client.force_authenticate(
            user=usuario_sin_notificaciones
        )

        response = self.client.get(
            self.url_listado
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_notificaciones"],
            0,
        )

        self.assertEqual(
            response.data["no_leidas"],
            0,
        )

        self.assertEqual(
            response.data["notificaciones"],
            [],
        )

        self.assertEqual(
            response.data["mensaje"],
            "No tienes notificaciones todavía.",
        )

    def test_usuario_no_autenticado_no_puede_acceder(self):
        self.client.force_authenticate(
            user=None
        )

        respuestas = [
            self.client.get(
                self.url_listado
            ),
            self.client.patch(
                self.url_marcar_todas,
                {},
                format="json",
            ),
            self.client.patch(
                self.url_marcar_leida(
                    self.notificacion_reciente
                ),
                {},
                format="json",
            ),
        ]

        for response in respuestas:
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )


class NotificarRegistroGastoSC55Test(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc55",
            email="fernando_sc55@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc55",
            email="carlita_sc55@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc55",
            email="damarys_sc55@example.com",
            password="Prueba123",
        )

        self.retirado = User.objects.create_user(
            username="retirado_sc55",
            email="retirado_sc55@example.com",
            password="Prueba123",
        )

        self.externo = User.objects.create_user(
            username="externo_sc55",
            email="externo_sc55@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Viaje SC-55",
            descripcion="Actividad para probar notificaciones",
            creador=self.fernando,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )

        self.grupo.participantes.add(
            self.fernando,
            self.carlita,
            self.damarys,
        )

        for usuario in [
            self.fernando,
            self.carlita,
            self.damarys,
        ]:
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=usuario,
            )

        membresia_retirada = GroupMembership.objects.create(
            grupo=self.grupo,
            usuario=self.retirado,
        )
        membresia_retirada.retirar()

        self.url = (
            f"/api/grupos/{self.grupo.id}/gastos/"
        )

        self.client.force_authenticate(
            user=self.carlita
        )

    def registrar_gasto(
        self,
        descripcion="Transporte al aeropuerto",
        monto="45.75",
    ):
        return self.client.post(
            self.url,
            {
                "descripcion": descripcion,
                "monto": monto,
                "fecha_gasto": "2026-07-26",
            },
            format="json",
        )

    def test_registro_correcto_notifica_a_otros_miembros_activos(
        self,
    ):
        response = self.registrar_gasto()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["notificaciones_generadas"],
            2,
        )

        destinatarios = set(
            Notification.objects.values_list(
                "usuario__username",
                flat=True,
            )
        )

        self.assertSetEqual(
            destinatarios,
            {
                "fernando_sc55",
                "damarys_sc55",
            },
        )

    def test_usuario_que_registra_no_recibe_notificacion_propia(
        self,
    ):
        self.registrar_gasto()

        self.assertFalse(
            Notification.objects.filter(
                usuario=self.carlita,
            ).exists()
        )

        self.assertEqual(
            Notification.objects.count(),
            2,
        )

    def test_notificacion_identifica_actividad_gasto_monto_y_usuario(
        self,
    ):
        response = self.registrar_gasto()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        notificacion = Notification.objects.get(
            usuario=self.fernando,
        )

        self.assertEqual(
            notificacion.titulo,
            "Nuevo gasto en Viaje SC-55",
        )

        self.assertIn(
            "carlita_sc55",
            notificacion.mensaje,
        )

        self.assertIn(
            "Transporte al aeropuerto",
            notificacion.mensaje,
        )

        self.assertIn(
            "$45.75",
            notificacion.mensaje,
        )

        self.assertEqual(
            notificacion.enlace,
            f"/grupos/{self.grupo.id}",
        )

    def test_notificaciones_quedan_inicialmente_no_leidas(
        self,
    ):
        self.registrar_gasto()

        notificaciones = Notification.objects.all()

        self.assertEqual(
            notificaciones.count(),
            2,
        )

        for notificacion in notificaciones:
            self.assertFalse(
                notificacion.leida
            )

            self.assertIsNone(
                notificacion.fecha_lectura
            )

    def test_retirados_y_externos_no_reciben_notificaciones(
        self,
    ):
        self.registrar_gasto()

        self.assertFalse(
            Notification.objects.filter(
                usuario=self.retirado,
            ).exists()
        )

        self.assertFalse(
            Notification.objects.filter(
                usuario=self.externo,
            ).exists()
        )

    def test_cada_destinatario_recibe_una_sola_notificacion_por_gasto(
        self,
    ):
        response = self.registrar_gasto()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        gasto = Expense.objects.get(
            descripcion="Transporte al aeropuerto",
        )

        for usuario in [
            self.fernando,
            self.damarys,
        ]:
            self.assertEqual(
                Notification.objects.filter(
                    usuario=usuario,
                    enlace=f"/grupos/{gasto.grupo_id}",
                    mensaje__contains=(
                        "Transporte al aeropuerto"
                    ),
                ).count(),
                1,
            )

    def test_registro_invalido_no_crea_gasto_ni_notificaciones(
        self,
    ):
        response = self.registrar_gasto(
            descripcion="",
            monto="0.00",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            Expense.objects.count(),
            0,
        )

        self.assertEqual(
            Notification.objects.count(),
            0,
        )

    def test_error_al_crear_notificaciones_revierte_el_gasto(
        self,
    ):
        with patch(
            (
                "expenses.views.Notification.objects."
                "bulk_create"
            ),
            side_effect=RuntimeError(
                "Fallo simulado al crear notificaciones"
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.registrar_gasto()

        self.assertEqual(
            Expense.objects.count(),
            0,
        )

        self.assertEqual(
            Notification.objects.count(),
            0,
        )

    def test_destinatario_visualiza_notificacion_en_su_centro(
        self,
    ):
        self.registrar_gasto()

        self.client.force_authenticate(
            user=self.fernando
        )

        response = self.client.get(
            "/api/notificaciones/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_notificaciones"],
            1,
        )

        self.assertEqual(
            response.data["no_leidas"],
            1,
        )

        notificacion = response.data[
            "notificaciones"
        ][0]

        self.assertEqual(
            notificacion["titulo"],
            "Nuevo gasto en Viaje SC-55",
        )

        self.assertEqual(
            notificacion["enlace"],
            f"/grupos/{self.grupo.id}",
        )

        self.assertFalse(
            notificacion["leida"]
        )


class HistorialActividadSC56Test(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc56",
            email="fernando_sc56@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc56",
            email="carlita_sc56@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc56",
            email="damarys_sc56@example.com",
            password="Prueba123",
        )

        self.retirado = User.objects.create_user(
            username="retirado_sc56",
            email="retirado_sc56@example.com",
            password="Prueba123",
        )

        self.externo = User.objects.create_user(
            username="externo_sc56",
            email="externo_sc56@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad SC-56",
            descripcion="Prueba del historial general",
            creador=self.fernando,
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
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

        self.membresia_retirada = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.retirado,
            )
        )
        self.membresia_retirada.retirar()

        self.url_historial = (
            f"/api/grupos/{self.grupo.id}/historial/"
        )

        self.client.force_authenticate(
            user=self.fernando
        )

    def test_crear_actividad_registra_evento_automaticamente(
        self,
    ):
        fecha_inicio = timezone.now() + timedelta(days=1)
        fecha_fin = fecha_inicio + timedelta(days=3)

        response = self.client.post(
            "/api/grupos/",
            {
                "nombre": "Nueva actividad SC-56",
                "descripcion": "Creación con historial",
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

        evento = ActivityHistory.objects.get(
            grupo=grupo_creado,
            tipo_accion=(
                ActivityHistory.TIPO_ACTIVIDAD_CREADA
            ),
        )

        self.assertEqual(
            evento.usuario,
            self.fernando,
        )

        self.assertEqual(
            evento.usuario_username,
            "fernando_sc56",
        )

        self.assertEqual(
            evento.grupo_nombre,
            "Nueva actividad SC-56",
        )

        self.assertIn(
            "creó la actividad",
            evento.descripcion,
        )

        self.assertIsNotNone(
            evento.fecha_evento,
        )

    def test_actualizar_actividad_registra_cambios_antes_y_despues(
        self,
    ):
        response = self.client.patch(
            f"/api/grupos/{self.grupo.id}/",
            {
                "nombre": "Actividad SC-56 actualizada",
                "descripcion": "Descripción modificada",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        evento = ActivityHistory.objects.get(
            grupo=self.grupo,
            tipo_accion=(
                ActivityHistory
                .TIPO_ACTIVIDAD_ACTUALIZADA
            ),
        )

        self.assertEqual(
            evento.usuario,
            self.fernando,
        )

        self.assertCountEqual(
            evento.datos["campos_modificados"],
            [
                "nombre",
                "descripcion",
            ],
        )

        self.assertEqual(
            evento.datos["antes"]["nombre"],
            "Actividad SC-56",
        )

        self.assertEqual(
            evento.datos["despues"]["nombre"],
            "Actividad SC-56 actualizada",
        )

    def test_registra_ingreso_retiro_y_reingreso_participante(
        self,
    ):
        agregar = (
            f"/api/grupos/{self.grupo.id}/participantes/"
        )

        retirar = (
            f"/api/grupos/{self.grupo.id}/"
            f"participantes/{self.damarys.id}/"
        )

        respuesta_ingreso = self.client.post(
            agregar,
            {
                "usuario_id": self.damarys.id,
            },
            format="json",
        )

        respuesta_retiro = self.client.delete(
            retirar
        )

        respuesta_reingreso = self.client.post(
            agregar,
            {
                "usuario_id": self.damarys.id,
            },
            format="json",
        )

        self.assertEqual(
            respuesta_ingreso.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            respuesta_retiro.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            respuesta_reingreso.status_code,
            status.HTTP_200_OK,
        )

        tipos = list(
            ActivityHistory.objects
            .filter(grupo=self.grupo)
            .order_by("fecha_evento", "id")
            .values_list(
                "tipo_accion",
                flat=True,
            )
        )

        self.assertEqual(
            tipos,
            [
                ActivityHistory
                .TIPO_PARTICIPANTE_INGRESO,
                ActivityHistory
                .TIPO_PARTICIPANTE_RETIRO,
                ActivityHistory
                .TIPO_PARTICIPANTE_REINGRESO,
            ],
        )

        for evento in ActivityHistory.objects.filter(
            grupo=self.grupo
        ):
            self.assertEqual(
                evento.usuario,
                self.fernando,
            )

            self.assertEqual(
                evento.datos["participante_username"],
                "damarys_sc56",
            )

    def test_registra_creacion_edicion_y_eliminacion_de_gasto(
        self,
    ):
        respuesta_creacion = self.client.post(
            f"/api/grupos/{self.grupo.id}/gastos/",
            {
                "descripcion": "Cena SC-56",
                "monto": "30.00",
                "fecha_gasto": "2026-07-26",
            },
            format="json",
        )

        self.assertEqual(
            respuesta_creacion.status_code,
            status.HTTP_201_CREATED,
        )

        gasto_id = respuesta_creacion.data["gasto"]["id"]

        respuesta_edicion = self.client.patch(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"gastos/{gasto_id}/"
            ),
            {
                "descripcion": "Cena actualizada SC-56",
                "monto": "40.00",
            },
            format="json",
        )

        self.assertEqual(
            respuesta_edicion.status_code,
            status.HTTP_200_OK,
        )

        respuesta_eliminacion = self.client.delete(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"gastos/{gasto_id}/"
            )
        )

        self.assertEqual(
            respuesta_eliminacion.status_code,
            status.HTTP_200_OK,
        )

        tipos = set(
            ActivityHistory.objects
            .filter(grupo=self.grupo)
            .values_list(
                "tipo_accion",
                flat=True,
            )
        )

        self.assertSetEqual(
            tipos,
            {
                ActivityHistory.TIPO_GASTO_CREADO,
                ActivityHistory.TIPO_GASTO_ACTUALIZADO,
                ActivityHistory.TIPO_GASTO_ELIMINADO,
            },
        )

        evento_eliminacion = ActivityHistory.objects.get(
            grupo=self.grupo,
            tipo_accion=(
                ActivityHistory.TIPO_GASTO_ELIMINADO
            ),
        )

        self.assertEqual(
            evento_eliminacion.datos["gasto_id"],
            gasto_id,
        )

        self.assertEqual(
            evento_eliminacion.datos["descripcion"],
            "Cena actualizada SC-56",
        )

        self.assertEqual(
            evento_eliminacion.datos["monto"],
            "40.00",
        )

        self.assertFalse(
            Expense.objects.filter(
                id=gasto_id
            ).exists()
        )

    def test_registrar_pago_genera_evento_con_usuario_y_monto(
        self,
    ):
        gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Gasto base SC-56",
            monto=Decimal("20.00"),
            fecha_gasto="2026-07-26",
            registrado_por=self.fernando,
        )
        gasto.sincronizar_integrantes_activos()

        response = self.client.post(
            f"/api/grupos/{self.grupo.id}/pagos/",
            {
                "monto": "5.00",
                "fecha_pago": "2026-07-26",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        evento = ActivityHistory.objects.get(
            grupo=self.grupo,
            tipo_accion=(
                ActivityHistory.TIPO_PAGO_CREADO
            ),
        )

        self.assertEqual(
            evento.usuario,
            self.fernando,
        )

        self.assertEqual(
            evento.usuario_username,
            "fernando_sc56",
        )

        self.assertEqual(
            evento.datos["monto"],
            "5.00",
        )

        self.assertEqual(
            evento.datos["pagador_username"],
            "fernando_sc56",
        )

    def test_creador_y_participante_activo_consultan_historial(
        self,
    ):
        ActivityHistory.registrar(
            grupo=self.grupo,
            usuario=self.fernando,
            tipo_accion=(
                ActivityHistory.TIPO_ACTIVIDAD_CREADA
            ),
            descripcion="Evento visible para miembros activos.",
            datos={
                "referencia": "SC-56",
            },
        )

        respuesta_creador = self.client.get(
            self.url_historial
        )

        self.client.force_authenticate(
            user=self.carlita
        )

        respuesta_participante = self.client.get(
            self.url_historial
        )

        self.assertEqual(
            respuesta_creador.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            respuesta_participante.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            respuesta_participante.data["total_eventos"],
            1,
        )

    def test_retirado_y_externo_no_pueden_consultar_historial(
        self,
    ):
        for usuario in [
            self.retirado,
            self.externo,
        ]:
            self.client.force_authenticate(
                user=usuario
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
                    "para consultar su historial."
                ),
            )

    def test_actividad_cerrada_conserva_y_muestra_historial(
        self,
    ):
        ahora = timezone.now()

        grupo_cerrado = Group.objects.create(
            nombre="Actividad cerrada SC-56",
            descripcion="Historial permanente",
            creador=self.fernando,
            fecha_inicio=ahora - timedelta(days=3),
            fecha_fin=ahora - timedelta(days=1),
        )

        grupo_cerrado.participantes.add(
            self.fernando,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=grupo_cerrado,
            usuario=self.fernando,
        )

        GroupMembership.objects.create(
            grupo=grupo_cerrado,
            usuario=self.carlita,
        )

        ActivityHistory.registrar(
            grupo=grupo_cerrado,
            usuario=self.fernando,
            tipo_accion=(
                ActivityHistory.TIPO_GASTO_CREADO
            ),
            descripcion="Gasto histórico conservado.",
            datos={
                "gasto_id": 999,
                "descripcion": "Gasto eliminado",
                "monto": "18.00",
            },
        )

        response = self.client.get(
            (
                f"/api/grupos/{grupo_cerrado.id}/"
                "historial/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["estado_actividad"],
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            response.data["total_eventos"],
            1,
        )

        self.assertEqual(
            response.data["eventos"][0]["datos"]["monto"],
            "18.00",
        )

    def test_eventos_se_ordenan_del_mas_reciente_al_mas_antiguo(
        self,
    ):
        ahora = timezone.now()

        evento_antiguo = ActivityHistory.registrar(
            grupo=self.grupo,
            usuario=self.fernando,
            tipo_accion=(
                ActivityHistory.TIPO_ACTIVIDAD_CREADA
            ),
            descripcion="Evento antiguo.",
        )

        evento_reciente = ActivityHistory.registrar(
            grupo=self.grupo,
            usuario=self.fernando,
            tipo_accion=(
                ActivityHistory.TIPO_ACTIVIDAD_ACTUALIZADA
            ),
            descripcion="Evento reciente.",
        )

        ActivityHistory.objects.filter(
            id=evento_antiguo.id
        ).update(
            fecha_evento=ahora - timedelta(hours=2)
        )

        ActivityHistory.objects.filter(
            id=evento_reciente.id
        ).update(
            fecha_evento=ahora - timedelta(hours=1)
        )

        response = self.client.get(
            self.url_historial
        )

        ids = [
            evento["id"]
            for evento in response.data["eventos"]
        ]

        self.assertEqual(
            ids,
            [
                evento_reciente.id,
                evento_antiguo.id,
            ],
        )

    def test_historial_solo_lectura_no_permite_editar_ni_eliminar(
        self,
    ):
        ActivityHistory.registrar(
            grupo=self.grupo,
            usuario=self.fernando,
            tipo_accion=(
                ActivityHistory.TIPO_ACTIVIDAD_CREADA
            ),
            descripcion="Evento protegido.",
        )

        respuesta_patch = self.client.patch(
            self.url_historial,
            {
                "descripcion": "Cambio no permitido",
            },
            format="json",
        )

        respuesta_delete = self.client.delete(
            self.url_historial
        )

        respuesta_post = self.client.post(
            self.url_historial,
            {
                "tipo_accion": "manual",
            },
            format="json",
        )

        self.assertEqual(
            respuesta_patch.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertEqual(
            respuesta_delete.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertEqual(
            respuesta_post.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertEqual(
            ActivityHistory.objects.filter(
                grupo=self.grupo
            ).count(),
            1,
        )

    def test_operacion_invalida_no_genera_evento(
        self,
    ):
        response = self.client.post(
            f"/api/grupos/{self.grupo.id}/gastos/",
            {
                "descripcion": "",
                "monto": "0.00",
                "fecha_gasto": "2026-07-26",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            Expense.objects.filter(
                grupo=self.grupo
            ).count(),
            0,
        )

        self.assertEqual(
            ActivityHistory.objects.filter(
                grupo=self.grupo
            ).count(),
            0,
        )

    def test_fallo_del_historial_revierte_operacion_principal(
        self,
    ):
        with patch(
            "expenses.views.registrar_evento_historial",
            side_effect=RuntimeError(
                "Fallo simulado del historial"
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    f"/api/grupos/{self.grupo.id}/gastos/",
                    {
                        "descripcion": "Gasto revertido",
                        "monto": "20.00",
                        "fecha_gasto": "2026-07-26",
                    },
                    format="json",
                )

        self.assertFalse(
            Expense.objects.filter(
                grupo=self.grupo,
                descripcion="Gasto revertido",
            ).exists()
        )

        self.assertEqual(
            ActivityHistory.objects.filter(
                grupo=self.grupo
            ).count(),
            0,
        )

    def test_historial_vacio_muestra_mensaje_informativo(
        self,
    ):
        response = self.client.get(
            self.url_historial
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_eventos"],
            0,
        )

        self.assertEqual(
            response.data["eventos"],
            [],
        )

        self.assertEqual(
            response.data["mensaje"],
            (
                "Todavía no existen eventos registrados "
                "en esta actividad."
            ),
        )

    def test_snapshots_se_conservan_aunque_cambien_datos_relacionados(
        self,
    ):
        evento = ActivityHistory.registrar(
            grupo=self.grupo,
            usuario=self.fernando,
            tipo_accion=(
                ActivityHistory.TIPO_GASTO_ELIMINADO
            ),
            descripcion=(
                "fernando_sc56 eliminó el gasto "
                '"Hospedaje original".'
            ),
            datos={
                "gasto_id": 501,
                "descripcion": "Hospedaje original",
                "monto": "80.00",
                "participantes": [
                    "fernando_sc56",
                    "carlita_sc56",
                ],
            },
        )

        self.grupo.nombre = "Nombre actual distinto"
        self.grupo.save(
            update_fields=["nombre"]
        )

        self.fernando.username = "fernando_modificado"
        self.fernando.save(
            update_fields=["username"]
        )

        evento.refresh_from_db()

        self.assertEqual(
            evento.grupo_nombre,
            "Actividad SC-56",
        )

        self.assertEqual(
            evento.usuario_username,
            "fernando_sc56",
        )

        self.assertEqual(
            evento.datos["descripcion"],
            "Hospedaje original",
        )

        self.assertEqual(
            evento.datos["monto"],
            "80.00",
        )

        response = self.client.get(
            self.url_historial
        )

        evento_respuesta = response.data["eventos"][0]

        self.assertEqual(
            evento_respuesta["grupo_nombre"],
            "Actividad SC-56",
        )

        self.assertEqual(
            evento_respuesta["usuario_username"],
            "fernando_sc56",
        )

        self.assertEqual(
            evento_respuesta["datos"]["gasto_id"],
            501,
        )


class CierreAutomaticoActividadSC57Test(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc57",
            email="fernando_sc57@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc57",
            email="carlita_sc57@example.com",
            password="Prueba123",
        )

        self.nuevo_usuario = User.objects.create_user(
            username="nuevo_sc57",
            email="nuevo_sc57@example.com",
            password="Prueba123",
        )

        self.momento_base = timezone.now()

        self.grupo_vencido = Group.objects.create(
            nombre="Actividad vencida SC-57",
            descripcion="Debe cerrarse automáticamente",
            creador=self.fernando,
            fecha_inicio=(
                self.momento_base
                - timedelta(days=2)
            ),
            fecha_fin=(
                self.momento_base
                - timedelta(hours=1)
            ),
        )

        self.grupo_vencido.participantes.add(
            self.fernando,
            self.carlita,
        )

        GroupMembership.objects.create(
            grupo=self.grupo_vencido,
            usuario=self.fernando,
        )

        GroupMembership.objects.create(
            grupo=self.grupo_vencido,
            usuario=self.carlita,
        )

        self.grupo_activo = Group.objects.create(
            nombre="Actividad activa SC-57",
            descripcion="Todavía no debe cerrarse",
            creador=self.fernando,
            fecha_inicio=(
                self.momento_base
                - timedelta(hours=1)
            ),
            fecha_fin=(
                self.momento_base
                + timedelta(hours=2)
            ),
        )

        self.grupo_activo.participantes.add(
            self.fernando
        )

        GroupMembership.objects.create(
            grupo=self.grupo_activo,
            usuario=self.fernando,
        )

        self.client.force_authenticate(
            user=self.fernando
        )

    def test_actividad_se_cierra_al_alcanzar_fecha_fin(
        self,
    ):
        fecha_fin = self.momento_base

        grupo = Group.objects.create(
            nombre="Cierre exacto SC-57",
            descripcion="Cierra justo en fecha fin",
            creador=self.fernando,
            fecha_inicio=(
                fecha_fin
                - timedelta(hours=1)
            ),
            fecha_fin=fecha_fin,
        )

        resultado = grupo.cerrar_automaticamente(
            momento=fecha_fin
        )

        self.assertTrue(
            resultado
        )

        grupo.refresh_from_db()

        self.assertEqual(
            grupo.estado,
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            grupo.fecha_cierre_automatico,
            fecha_fin,
        )

    def test_cierre_persistente_guarda_fecha_programada(
        self,
    ):
        resultado = (
            self.grupo_vencido
            .cerrar_automaticamente(
                momento=self.momento_base
            )
        )

        self.assertTrue(
            resultado
        )

        self.grupo_vencido.refresh_from_db()

        self.assertEqual(
            self.grupo_vencido
            .fecha_cierre_automatico,
            self.grupo_vencido.fecha_fin,
        )

        self.assertEqual(
            self.grupo_vencido.estado,
            Group.ESTADO_CERRADA,
        )

    def test_cierre_registra_evento_unico_del_sistema(
        self,
    ):
        self.grupo_vencido.cerrar_automaticamente(
            momento=self.momento_base
        )

        evento = ActivityHistory.objects.get(
            grupo=self.grupo_vencido,
            tipo_accion=(
                ActivityHistory
                .TIPO_ACTIVIDAD_CERRADA_AUTOMATICAMENTE
            ),
        )

        self.assertIsNone(
            evento.usuario,
        )

        self.assertEqual(
            evento.usuario_username,
            "sistema",
        )

        self.assertEqual(
            evento.grupo_nombre,
            "Actividad vencida SC-57",
        )

        self.assertIn(
            "cerró automáticamente",
            evento.descripcion,
        )

        self.assertEqual(
            evento.datos["origen"],
            "sistema",
        )

        self.assertEqual(
            evento.datos["estado"],
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            evento.datos["fecha_fin_programada"],
            self.grupo_vencido.fecha_fin.isoformat(),
        )

        self.assertIsNotNone(
            evento.fecha_evento,
        )

    def test_ejecucion_repetida_no_duplica_cierre_ni_historial(
        self,
    ):
        primer_resultado = (
            self.grupo_vencido
            .cerrar_automaticamente(
                momento=self.momento_base
            )
        )

        segundo_resultado = (
            self.grupo_vencido
            .cerrar_automaticamente(
                momento=(
                    self.momento_base
                    + timedelta(minutes=10)
                )
            )
        )

        self.assertTrue(
            primer_resultado
        )

        self.assertFalse(
            segundo_resultado
        )

        self.assertEqual(
            ActivityHistory.objects.filter(
                grupo=self.grupo_vencido,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_ACTIVIDAD_CERRADA_AUTOMATICAMENTE
                ),
            ).count(),
            1,
        )

    def test_cierre_masivo_procesa_solo_actividades_vencidas(
        self,
    ):
        otro_grupo_vencido = Group.objects.create(
            nombre="Otra actividad vencida SC-57",
            descripcion="También debe cerrarse",
            creador=self.fernando,
            fecha_inicio=(
                self.momento_base
                - timedelta(days=3)
            ),
            fecha_fin=(
                self.momento_base
                - timedelta(minutes=30)
            ),
        )

        cantidad = (
            Group.cerrar_actividades_vencidas(
                momento=self.momento_base
            )
        )

        self.assertEqual(
            cantidad,
            2,
        )

        self.grupo_vencido.refresh_from_db()
        otro_grupo_vencido.refresh_from_db()
        self.grupo_activo.refresh_from_db()

        self.assertIsNotNone(
            self.grupo_vencido
            .fecha_cierre_automatico
        )

        self.assertIsNotNone(
            otro_grupo_vencido
            .fecha_cierre_automatico
        )

        self.assertIsNone(
            self.grupo_activo
            .fecha_cierre_automatico
        )

        self.assertEqual(
            self.grupo_activo.estado,
            Group.ESTADO_ACTIVA,
        )

    def test_comando_cierra_actividades_vencidas(
        self,
    ):
        salida = StringIO()

        call_command(
            "cerrar_actividades",
            stdout=salida,
        )

        self.grupo_vencido.refresh_from_db()

        self.assertEqual(
            self.grupo_vencido.estado,
            Group.ESTADO_CERRADA,
        )

        self.assertIsNotNone(
            self.grupo_vencido
            .fecha_cierre_automatico
        )

        self.assertIn(
            "1 actividad(es) cerrada(s) automáticamente.",
            salida.getvalue(),
        )

    def test_comando_repetido_informa_que_no_hay_pendientes(
        self,
    ):
        primera_salida = StringIO()
        segunda_salida = StringIO()

        call_command(
            "cerrar_actividades",
            stdout=primera_salida,
        )

        call_command(
            "cerrar_actividades",
            stdout=segunda_salida,
        )

        self.assertIn(
            "No existen actividades pendientes de cierre.",
            segunda_salida.getvalue(),
        )

        self.assertEqual(
            ActivityHistory.objects.filter(
                grupo=self.grupo_vencido,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_ACTIVIDAD_CERRADA_AUTOMATICAMENTE
                ),
            ).count(),
            1,
        )

    def test_fallo_del_historial_revierte_el_cierre(
        self,
    ):
        with patch(
            "expenses.models.ActivityHistory.registrar",
            side_effect=RuntimeError(
                "Fallo simulado del historial"
            ),
        ):
            with self.assertRaises(RuntimeError):
                (
                    self.grupo_vencido
                    .cerrar_automaticamente(
                        momento=self.momento_base
                    )
                )

        self.grupo_vencido.refresh_from_db()

        self.assertIsNone(
            self.grupo_vencido
            .fecha_cierre_automatico
        )

        self.assertEqual(
            ActivityHistory.objects.filter(
                grupo=self.grupo_vencido,
            ).count(),
            0,
        )

    def test_actividad_cerrada_bloquea_nuevas_operaciones(
        self,
    ):
        self.grupo_vencido.cerrar_automaticamente(
            momento=self.momento_base
        )

        respuesta_gasto = self.client.post(
            (
                f"/api/grupos/"
                f"{self.grupo_vencido.id}/gastos/"
            ),
            {
                "descripcion": "Gasto posterior al cierre",
                "monto": "10.00",
                "fecha_gasto": "2026-07-26",
            },
            format="json",
        )

        respuesta_pago = self.client.post(
            (
                f"/api/grupos/"
                f"{self.grupo_vencido.id}/pagos/"
            ),
            {
                "monto": "5.00",
                "fecha_pago": "2026-07-26",
            },
            format="json",
        )

        respuesta_agregar = self.client.post(
            (
                f"/api/grupos/"
                f"{self.grupo_vencido.id}/"
                "participantes/"
            ),
            {
                "usuario_id": self.nuevo_usuario.id,
            },
            format="json",
        )

        respuesta_retirar = self.client.delete(
            (
                f"/api/grupos/"
                f"{self.grupo_vencido.id}/"
                f"participantes/{self.carlita.id}/"
            )
        )

        for response in [
            respuesta_gasto,
            respuesta_pago,
            respuesta_agregar,
            respuesta_retirar,
        ]:
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
            )

        self.assertFalse(
            Expense.objects.filter(
                grupo=self.grupo_vencido,
            ).exists()
        )

        self.assertFalse(
            Payment.objects.filter(
                grupo=self.grupo_vencido,
            ).exists()
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                grupo=self.grupo_vencido,
                usuario=self.nuevo_usuario,
                activo=True,
            ).exists()
        )

    def test_datos_e_historial_siguen_disponibles_tras_cierre(
        self,
    ):
        ActivityHistory.registrar(
            grupo=self.grupo_vencido,
            usuario=self.fernando,
            tipo_accion=(
                ActivityHistory.TIPO_ACTIVIDAD_CREADA
            ),
            descripcion="Evento previo al cierre.",
        )

        self.grupo_vencido.cerrar_automaticamente(
            momento=self.momento_base
        )

        detalle = self.client.get(
            f"/api/grupos/{self.grupo_vencido.id}/"
        )

        historial = self.client.get(
            (
                f"/api/grupos/"
                f"{self.grupo_vencido.id}/historial/"
            )
        )

        self.assertEqual(
            detalle.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            detalle.data["estado"],
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            historial.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            historial.data["estado_actividad"],
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            historial.data["total_eventos"],
            2,
        )


class GenerarSaldosPendientesSC58Test(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc58",
            email="fernando_sc58@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc58",
            email="carlita_sc58@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc58",
            email="damarys_sc58@example.com",
            password="Prueba123",
        )

        self.externo = User.objects.create_user(
            username="externo_sc58",
            email="externo_sc58@example.com",
            password="Prueba123",
        )

        self.momento_base = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad económica SC-58",
            descripcion="Generación de saldos al cierre",
            creador=self.fernando,
            fecha_inicio=(
                self.momento_base
                - timedelta(days=3)
            ),
            fecha_fin=(
                self.momento_base
                - timedelta(hours=1)
            ),
        )

        self.grupo.participantes.add(
            self.fernando,
            self.carlita,
            self.damarys,
        )

        self.membresia_fernando = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.fernando,
            )
        )

        self.membresia_carlita = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.carlita,
            )
        )

        self.membresia_damarys = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.damarys,
            )
        )

        self.gasto_uno = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Hospedaje SC-58",
            monto=Decimal("60.00"),
            fecha_gasto="2026-07-24",
            registrado_por=self.fernando,
        )
        self.gasto_uno.sincronizar_integrantes_activos()

        self.membresia_damarys.retirar()
        self.grupo.participantes.remove(
            self.damarys
        )

        self.gasto_dos = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Transporte SC-58",
            monto=Decimal("30.00"),
            fecha_gasto="2026-07-25",
            registrado_por=self.carlita,
        )
        self.gasto_dos.sincronizar_integrantes_activos()

        Payment.objects.create(
            grupo=self.grupo,
            pagador=self.fernando,
            monto=Decimal("25.00"),
            fecha_pago="2026-07-25",
            registrado_por=self.fernando,
        )

        Payment.objects.create(
            grupo=self.grupo,
            pagador=self.carlita,
            monto=Decimal("35.00"),
            fecha_pago="2026-07-25",
            registrado_por=self.carlita,
        )

        self.url = (
            f"/api/grupos/{self.grupo.id}/"
            "saldos-cierre/"
        )

        self.client.force_authenticate(
            user=self.fernando
        )

    def cerrar_actividad(self):
        resultado = self.grupo.cerrar_automaticamente(
            momento=self.momento_base
        )

        self.grupo.refresh_from_db()

        return resultado

    def saldos_por_usuario(self):
        return {
            saldo.participante_username: saldo
            for saldo in ClosingBalance.objects.filter(
                grupo=self.grupo
            )
        }

    def test_cierre_genera_saldos_y_deudas_automaticamente(
        self,
    ):
        resultado = self.cerrar_actividad()

        self.assertTrue(
            resultado
        )

        self.assertIsNotNone(
            self.grupo.fecha_cierre_automatico
        )

        self.assertIsNotNone(
            self.grupo.fecha_generacion_saldos
        )

        self.assertEqual(
            ClosingBalance.objects.filter(
                grupo=self.grupo
            ).count(),
            3,
        )

        self.assertEqual(
            Debt.objects.filter(
                grupo=self.grupo
            ).count(),
            2,
        )

        evento = ActivityHistory.objects.get(
            grupo=self.grupo,
            tipo_accion=(
                ActivityHistory
                .TIPO_ACTIVIDAD_CERRADA_AUTOMATICAMENTE
            ),
        )

        self.assertEqual(
            evento.datos["saldos_cierre"][
                "total_saldos"
            ],
            3,
        )

        self.assertEqual(
            evento.datos["saldos_cierre"][
                "total_deudas"
            ],
            2,
        )

    def test_calculo_usa_gastos_divisiones_y_pagos_previos(
        self,
    ):
        self.cerrar_actividad()

        saldos = self.saldos_por_usuario()

        saldo_fernando = saldos["fernando_sc58"]
        saldo_carlita = saldos["carlita_sc58"]
        saldo_damarys = saldos["damarys_sc58"]

        self.assertEqual(
            saldo_fernando.cuota_total,
            Decimal("35.00"),
        )
        self.assertEqual(
            saldo_fernando.total_pagado,
            Decimal("25.00"),
        )
        self.assertEqual(
            saldo_fernando.saldo_pendiente,
            Decimal("10.00"),
        )

        self.assertEqual(
            saldo_carlita.cuota_total,
            Decimal("35.00"),
        )
        self.assertEqual(
            saldo_carlita.total_pagado,
            Decimal("35.00"),
        )
        self.assertEqual(
            saldo_carlita.saldo_pendiente,
            Decimal("0.00"),
        )

        self.assertEqual(
            saldo_damarys.cuota_total,
            Decimal("20.00"),
        )
        self.assertEqual(
            saldo_damarys.total_pagado,
            Decimal("0.00"),
        )
        self.assertEqual(
            saldo_damarys.saldo_pendiente,
            Decimal("20.00"),
        )

    def test_participante_retirado_conserva_obligacion_historica(
        self,
    ):
        self.cerrar_actividad()

        saldo = ClosingBalance.objects.get(
            grupo=self.grupo,
            participante=self.damarys,
        )

        deuda = Debt.objects.get(
            grupo=self.grupo,
            participante=self.damarys,
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                grupo=self.grupo,
                usuario=self.damarys,
                activo=True,
            ).exists()
        )

        self.assertEqual(
            saldo.cuota_total,
            Decimal("20.00"),
        )

        self.assertEqual(
            saldo.saldo_pendiente,
            Decimal("20.00"),
        )

        self.assertEqual(
            deuda.saldo_pendiente,
            Decimal("20.00"),
        )

    def test_estado_saldado_y_deuda_solo_para_saldo_positivo(
        self,
    ):
        self.cerrar_actividad()

        saldo_carlita = ClosingBalance.objects.get(
            grupo=self.grupo,
            participante=self.carlita,
        )

        self.assertEqual(
            saldo_carlita.estado,
            ClosingBalance.ESTADO_SALDADO,
        )

        self.assertFalse(
            Debt.objects.filter(
                grupo=self.grupo,
                participante=self.carlita,
            ).exists()
        )

        for saldo in ClosingBalance.objects.filter(
            grupo=self.grupo
        ):
            self.assertGreaterEqual(
                saldo.saldo_pendiente,
                Decimal("0.00"),
            )

        for deuda in Debt.objects.filter(
            grupo=self.grupo
        ):
            self.assertGreater(
                deuda.monto_original,
                Decimal("0.00"),
            )

            self.assertGreaterEqual(
                deuda.saldo_pendiente,
                Decimal("0.00"),
            )

    def test_un_saldo_consolidado_por_participante_sin_duplicados(
        self,
    ):
        primer_resultado = self.cerrar_actividad()

        segundo_resultado = (
            self.grupo.cerrar_automaticamente(
                momento=(
                    self.momento_base
                    + timedelta(minutes=5)
                )
            )
        )

        resumen_repetido = (
            self.grupo.generar_saldos_cierre(
                momento=(
                    self.momento_base
                    + timedelta(minutes=10)
                )
            )
        )

        self.assertTrue(
            primer_resultado
        )

        self.assertFalse(
            segundo_resultado
        )

        self.assertFalse(
            resumen_repetido["generados"]
        )

        self.assertEqual(
            ClosingBalance.objects.filter(
                grupo=self.grupo
            ).count(),
            3,
        )

        self.assertEqual(
            Debt.objects.filter(
                grupo=self.grupo
            ).count(),
            2,
        )

        for usuario in [
            self.fernando,
            self.carlita,
            self.damarys,
        ]:
            self.assertEqual(
                ClosingBalance.objects.filter(
                    grupo=self.grupo,
                    participante=usuario,
                ).count(),
                1,
            )

    def test_suma_saldos_coincide_con_total_pendiente(
        self,
    ):
        self.cerrar_actividad()

        suma_saldos = sum(
            ClosingBalance.objects.filter(
                grupo=self.grupo
            ).values_list(
                "saldo_pendiente",
                flat=True,
            ),
            Decimal("0.00"),
        )

        suma_deudas = sum(
            Debt.objects.filter(
                grupo=self.grupo
            ).values_list(
                "saldo_pendiente",
                flat=True,
            ),
            Decimal("0.00"),
        )

        resumen = (
            self.grupo.obtener_resumen_saldos_cierre()
        )

        self.assertEqual(
            suma_saldos,
            Decimal("30.00"),
        )

        self.assertEqual(
            suma_deudas,
            Decimal("30.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_pendiente"]),
            Decimal("30.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_cuotas"]),
            Decimal("90.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_pagado"]),
            Decimal("60.00"),
        )

    def test_endpoint_muestra_valores_con_dos_decimales(
        self,
    ):
        self.cerrar_actividad()

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["estado_actividad"],
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            response.data["resumen"]["total_saldos"],
            3,
        )

        self.assertEqual(
            response.data["resumen"]["total_saldados"],
            1,
        )

        self.assertEqual(
            response.data["resumen"]["total_pendientes"],
            2,
        )

        self.assertEqual(
            response.data["resumen"]["total_deudas"],
            2,
        )

        self.assertEqual(
            response.data["resumen"]["total_pendiente"],
            "30.00",
        )

        for saldo in response.data["saldos"]:
            for campo in [
                "cuota_total",
                "total_pagado",
                "saldo_pendiente",
            ]:
                self.assertRegex(
                    saldo[campo],
                    r"^\d+\.\d{2}$",
                )

        for deuda in response.data["deudas"]:
            for campo in [
                "monto_original",
                "saldo_pendiente",
            ]:
                self.assertRegex(
                    deuda[campo],
                    r"^\d+\.\d{2}$",
                )

    def test_actividad_totalmente_pagada_no_genera_deudas(
        self,
    ):
        grupo_saldado = Group.objects.create(
            nombre="Actividad saldada SC-58",
            descripcion="Todos pagaron su cuota",
            creador=self.fernando,
            fecha_inicio=(
                self.momento_base
                - timedelta(days=2)
            ),
            fecha_fin=(
                self.momento_base
                - timedelta(minutes=30)
            ),
        )

        grupo_saldado.participantes.add(
            self.fernando,
            self.carlita,
        )

        for usuario in [
            self.fernando,
            self.carlita,
        ]:
            GroupMembership.objects.create(
                grupo=grupo_saldado,
                usuario=usuario,
            )

        gasto = Expense.objects.create(
            grupo=grupo_saldado,
            descripcion="Cena pagada",
            monto=Decimal("40.00"),
            fecha_gasto="2026-07-25",
            registrado_por=self.fernando,
        )
        gasto.sincronizar_integrantes_activos()

        for usuario in [
            self.fernando,
            self.carlita,
        ]:
            Payment.objects.create(
                grupo=grupo_saldado,
                pagador=usuario,
                monto=Decimal("20.00"),
                fecha_pago="2026-07-25",
                registrado_por=usuario,
            )

        grupo_saldado.cerrar_automaticamente(
            momento=self.momento_base
        )

        self.assertEqual(
            ClosingBalance.objects.filter(
                grupo=grupo_saldado,
                estado=ClosingBalance.ESTADO_SALDADO,
            ).count(),
            2,
        )

        self.assertEqual(
            Debt.objects.filter(
                grupo=grupo_saldado
            ).count(),
            0,
        )

        resumen = (
            grupo_saldado
            .obtener_resumen_saldos_cierre()
        )

        self.assertEqual(
            resumen["mensaje"],
            "Todos los participantes quedaron saldados.",
        )

        self.assertEqual(
            resumen["total_pendiente"],
            "0.00",
        )

    def test_actividad_sin_gastos_muestra_mensaje_informativo(
        self,
    ):
        grupo_vacio = Group.objects.create(
            nombre="Actividad vacía SC-58",
            descripcion="Sin gastos ni pagos",
            creador=self.fernando,
            fecha_inicio=(
                self.momento_base
                - timedelta(days=1)
            ),
            fecha_fin=(
                self.momento_base
                - timedelta(minutes=15)
            ),
        )

        grupo_vacio.participantes.add(
            self.fernando
        )

        GroupMembership.objects.create(
            grupo=grupo_vacio,
            usuario=self.fernando,
        )

        grupo_vacio.cerrar_automaticamente(
            momento=self.momento_base
        )

        response = self.client.get(
            (
                f"/api/grupos/{grupo_vacio.id}/"
                "saldos-cierre/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["mensaje"],
            (
                "La actividad cerró sin gastos, pagos "
                "ni saldos pendientes."
            ),
        )

        self.assertEqual(
            response.data["resumen"]["total_saldos"],
            0,
        )

        self.assertEqual(
            response.data["resumen"]["total_deudas"],
            0,
        )

        self.assertEqual(
            response.data["resumen"]["total_pendiente"],
            "0.00",
        )

        self.assertEqual(
            response.data["saldos"],
            [],
        )

        self.assertEqual(
            response.data["deudas"],
            [],
        )

    def test_snapshots_permanecen_tras_cambiar_datos_personales(
        self,
    ):
        self.cerrar_actividad()

        self.fernando.username = "fernando_modificado_sc58"
        self.fernando.save(
            update_fields=["username"]
        )

        self.grupo.nombre = "Actividad renombrada SC-58"
        self.grupo.save(
            update_fields=["nombre"]
        )

        saldo = ClosingBalance.objects.get(
            grupo=self.grupo,
            participante=self.fernando,
        )

        deuda = Debt.objects.get(
            grupo=self.grupo,
            participante=self.fernando,
        )

        self.assertEqual(
            saldo.participante_username,
            "fernando_sc58",
        )

        self.assertEqual(
            saldo.grupo_nombre,
            "Actividad económica SC-58",
        )

        self.assertEqual(
            deuda.participante_username,
            "fernando_sc58",
        )

        self.assertEqual(
            deuda.grupo_nombre,
            "Actividad económica SC-58",
        )

        response = self.client.get(
            self.url
        )

        saldo_response = next(
            item
            for item in response.data["saldos"]
            if item["participante_id"] == self.fernando.id
        )

        self.assertEqual(
            saldo_response["participante_username"],
            "fernando_sc58",
        )

        self.assertEqual(
            saldo_response["grupo_nombre"],
            "Actividad económica SC-58",
        )

    def test_saldos_no_cambian_si_se_modifican_datos_origen(
        self,
    ):
        self.cerrar_actividad()

        saldo_original = ClosingBalance.objects.get(
            grupo=self.grupo,
            participante=self.fernando,
        )

        valores_originales = (
            saldo_original.cuota_total,
            saldo_original.total_pagado,
            saldo_original.saldo_pendiente,
        )

        ExpenseDivision.objects.filter(
            gasto__grupo=self.grupo,
            participante=self.fernando,
        ).update(
            monto_asignado=Decimal("99.99")
        )

        Payment.objects.filter(
            grupo=self.grupo,
            pagador=self.fernando,
        ).update(
            monto=Decimal("1.00")
        )

        saldo_original.refresh_from_db()

        self.assertEqual(
            (
                saldo_original.cuota_total,
                saldo_original.total_pagado,
                saldo_original.saldo_pendiente,
            ),
            valores_originales,
        )

    def test_fallo_del_calculo_revierte_todo_el_cierre(
        self,
    ):
        with patch(
            "expenses.models.Debt.objects.create",
            side_effect=RuntimeError(
                "Fallo simulado al crear una deuda"
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.grupo.cerrar_automaticamente(
                    momento=self.momento_base
                )

        self.grupo.refresh_from_db()

        self.assertIsNone(
            self.grupo.fecha_cierre_automatico
        )

        self.assertIsNone(
            self.grupo.fecha_generacion_saldos
        )

        self.assertEqual(
            ClosingBalance.objects.filter(
                grupo=self.grupo
            ).count(),
            0,
        )

        self.assertEqual(
            Debt.objects.filter(
                grupo=self.grupo
            ).count(),
            0,
        )

        self.assertEqual(
            ActivityHistory.objects.filter(
                grupo=self.grupo,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_ACTIVIDAD_CERRADA_AUTOMATICAMENTE
                ),
            ).count(),
            0,
        )

    def test_no_permite_generar_saldos_sin_cierre_persistente(
        self,
    ):
        with self.assertRaises(ValidationError):
            self.grupo.generar_saldos_cierre(
                momento=self.momento_base
            )

        self.assertEqual(
            ClosingBalance.objects.filter(
                grupo=self.grupo
            ).count(),
            0,
        )

        self.assertEqual(
            Debt.objects.filter(
                grupo=self.grupo
            ).count(),
            0,
        )

    def test_endpoint_controla_estado_y_procesamiento_del_cierre(
        self,
    ):
        grupo_activo = Group.objects.create(
            nombre="Actividad activa consulta SC-58",
            descripcion="Aún no ha terminado",
            creador=self.fernando,
            fecha_inicio=(
                self.momento_base
                - timedelta(hours=1)
            ),
            fecha_fin=(
                self.momento_base
                + timedelta(hours=1)
            ),
        )

        grupo_activo.participantes.add(
            self.fernando
        )

        GroupMembership.objects.create(
            grupo=grupo_activo,
            usuario=self.fernando,
        )

        respuesta_activa = self.client.get(
            (
                f"/api/grupos/{grupo_activo.id}/"
                "saldos-cierre/"
            )
        )

        respuesta_no_procesada = self.client.get(
            self.url
        )

        self.assertEqual(
            respuesta_activa.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            respuesta_no_procesada.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_participante_activo_consulta_y_externo_no_accede(
        self,
    ):
        self.cerrar_actividad()

        self.client.force_authenticate(
            user=self.carlita
        )

        respuesta_participante = self.client.get(
            self.url
        )

        self.client.force_authenticate(
            user=self.externo
        )

        respuesta_externo = self.client.get(
            self.url
        )

        self.assertEqual(
            respuesta_participante.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            respuesta_externo.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_endpoint_saldos_es_solo_lectura(
        self,
    ):
        self.cerrar_actividad()

        respuestas = [
            self.client.post(
                self.url,
                {},
                format="json",
            ),
            self.client.patch(
                self.url,
                {
                    "saldo_pendiente": "0.00",
                },
                format="json",
            ),
            self.client.delete(
                self.url
            ),
        ]

        for response in respuestas:
            self.assertEqual(
                response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            )


class AsignarResponsableDeudasSC60Test(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc60",
            email="fernando_sc60@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc60",
            email="carlita_sc60@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc60",
            email="damarys_sc60@example.com",
            password="Prueba123",
        )

        self.retirado = User.objects.create_user(
            username="retirado_sc60",
            email="retirado_sc60@example.com",
            password="Prueba123",
        )

        self.externo = User.objects.create_user(
            username="externo_sc60",
            email="externo_sc60@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad SC-60",
            descripcion="Responsable para revisar deudas",
            creador=self.fernando,
            fecha_inicio=ahora - timedelta(hours=1),
            fecha_fin=ahora + timedelta(days=2),
        )

        self.grupo.participantes.add(
            self.fernando,
            self.carlita,
            self.damarys,
        )

        self.membresia_fernando = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.fernando,
            )
        )

        self.membresia_carlita = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.carlita,
            )
        )

        self.membresia_damarys = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.damarys,
            )
        )

        self.membresia_retirada = (
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=self.retirado,
            )
        )
        self.membresia_retirada.retirar()

        self.url = (
            f"/api/grupos/{self.grupo.id}/"
            "responsable-deudas/"
        )

        self.url_detalle = (
            f"/api/grupos/{self.grupo.id}/"
        )

        self.client.force_authenticate(
            user=self.fernando
        )

    def asignar(
        self,
        usuario,
        metodo="put",
    ):
        funcion = getattr(
            self.client,
            metodo,
        )

        return funcion(
            self.url,
            {
                "responsable_id": usuario.id,
            },
            format="json",
        )

    def obtener_asignacion_vigente(self):
        return DebtReviewAssignment.objects.get(
            grupo=self.grupo,
            vigente=True,
        )

    def test_sin_responsable_muestra_mensaje_informativo(
        self,
    ):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsNone(
            response.data["responsable"]
        )

        self.assertIsNone(
            response.data["asignacion_vigente"]
        )

        self.assertFalse(
            response.data["puede_revisar_solicitudes"]
        )

        self.assertEqual(
            response.data["total_asignaciones"],
            0,
        )

        self.assertEqual(
            response.data["historial_asignaciones"],
            [],
        )

        self.assertEqual(
            response.data["mensaje"],
            (
                "No existe un responsable asignado "
                "para revisar las deudas."
            ),
        )

        detalle = self.client.get(
            self.url_detalle
        )

        self.assertIsNone(
            detalle.data["responsable_deudas"]
        )

        self.assertIsNone(
            detalle.data[
                "asignacion_responsable_deudas"
            ]
        )

    def test_creador_asigna_participante_activo(
        self,
    ):
        response = self.asignar(
            self.carlita
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["mensaje"],
            (
                "Responsable de deudas asignado "
                "correctamente."
            ),
        )

        self.assertTrue(
            response.data["cambio_realizado"]
        )

        asignacion = self.obtener_asignacion_vigente()

        self.assertEqual(
            asignacion.responsable,
            self.carlita,
        )

        self.assertEqual(
            asignacion.asignado_por,
            self.fernando,
        )

        self.assertEqual(
            asignacion.responsable_username,
            "carlita_sc60",
        )

        self.assertEqual(
            asignacion.asignado_por_username,
            "fernando_sc60",
        )

        self.assertTrue(
            asignacion.vigente
        )

        self.assertIsNone(
            asignacion.fecha_fin
        )

        self.assertIsNotNone(
            asignacion.fecha_asignacion
        )

    def test_creador_puede_asignarse_a_si_mismo(
        self,
    ):
        response = self.asignar(
            self.fernando,
            metodo="patch",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        asignacion = self.obtener_asignacion_vigente()

        self.assertEqual(
            asignacion.responsable,
            self.fernando,
        )

        self.assertTrue(
            self.grupo.puede_revisar_solicitudes_deuda(
                self.fernando
            )
        )

    def test_responsable_se_muestra_en_informacion_actividad(
        self,
    ):
        self.asignar(
            self.carlita
        )

        response = self.client.get(
            self.url_detalle
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data[
                "responsable_deudas"
            ]["username"],
            "carlita_sc60",
        )

        asignacion = response.data[
            "asignacion_responsable_deudas"
        ]

        self.assertEqual(
            asignacion["responsable_username"],
            "carlita_sc60",
        )

        self.assertEqual(
            asignacion["asignado_por_username"],
            "fernando_sc60",
        )

        self.assertTrue(
            asignacion["vigente"]
        )

        self.assertEqual(
            asignacion["estado"],
            "vigente",
        )

        self.assertIsNotNone(
            asignacion["fecha_asignacion"]
        )

    def test_participante_activo_consulta_responsable(
        self,
    ):
        self.asignar(
            self.carlita
        )

        self.client.force_authenticate(
            user=self.damarys
        )

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["responsable"]["username"],
            "carlita_sc60",
        )

        self.assertFalse(
            response.data["puede_revisar_solicitudes"]
        )

    def test_usuario_externo_no_puede_ser_responsable(
        self,
    ):
        self.asignar(
            self.carlita
        )

        response = self.asignar(
            self.externo
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "responsable_id",
            response.data,
        )

        asignacion = self.obtener_asignacion_vigente()

        self.assertEqual(
            asignacion.responsable,
            self.carlita,
        )

        self.assertEqual(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo
            ).count(),
            1,
        )

    def test_participante_retirado_no_puede_ser_responsable(
        self,
    ):
        self.asignar(
            self.carlita
        )

        response = self.asignar(
            self.retirado
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "responsable_id",
            response.data,
        )

        asignacion = self.obtener_asignacion_vigente()

        self.assertEqual(
            asignacion.responsable,
            self.carlita,
        )

        self.assertEqual(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo
            ).count(),
            1,
        )

    def test_usuario_inexistente_no_modifica_responsable_actual(
        self,
    ):
        self.asignar(
            self.carlita
        )

        response = self.client.put(
            self.url,
            {
                "responsable_id": 999999,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        asignacion = self.obtener_asignacion_vigente()

        self.assertEqual(
            asignacion.responsable,
            self.carlita,
        )

        self.assertEqual(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo
            ).count(),
            1,
        )

    def test_solo_creador_puede_asignar_responsable(
        self,
    ):
        self.client.force_authenticate(
            user=self.carlita
        )

        response = self.asignar(
            self.damarys
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertFalse(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo
            ).exists()
        )

    def test_cambio_de_responsable_conserva_asignacion_anterior(
        self,
    ):
        primera = self.asignar(
            self.carlita
        )

        primera_id = primera.data[
            "asignacion_vigente"
        ]["id"]

        segunda = self.asignar(
            self.damarys
        )

        self.assertEqual(
            segunda.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            segunda.data["mensaje"],
            (
                "Responsable de deudas actualizado "
                "correctamente."
            ),
        )

        self.assertEqual(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo
            ).count(),
            2,
        )

        anterior = DebtReviewAssignment.objects.get(
            id=primera_id
        )

        actual = self.obtener_asignacion_vigente()

        self.assertFalse(
            anterior.vigente
        )

        self.assertIsNotNone(
            anterior.fecha_fin
        )

        self.assertEqual(
            anterior.responsable,
            self.carlita,
        )

        self.assertTrue(
            actual.vigente
        )

        self.assertEqual(
            actual.responsable,
            self.damarys,
        )

        self.assertEqual(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo,
                vigente=True,
            ).count(),
            1,
        )

    def test_historial_endpoint_conserva_responsables_anteriores(
        self,
    ):
        self.asignar(
            self.carlita
        )

        self.asignar(
            self.damarys
        )

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_asignaciones"],
            2,
        )

        historial = response.data[
            "historial_asignaciones"
        ]

        self.assertEqual(
            historial[0]["responsable_username"],
            "damarys_sc60",
        )

        self.assertEqual(
            historial[0]["estado"],
            "vigente",
        )

        self.assertEqual(
            historial[1]["responsable_username"],
            "carlita_sc60",
        )

        self.assertEqual(
            historial[1]["estado"],
            "anterior",
        )

        self.assertIsNotNone(
            historial[1]["fecha_fin"]
        )

    def test_asignacion_y_cambio_se_registran_en_historial(
        self,
    ):
        self.asignar(
            self.carlita
        )

        self.asignar(
            self.damarys
        )

        eventos = (
            ActivityHistory.objects
            .filter(grupo=self.grupo)
            .order_by("fecha_evento", "id")
        )

        self.assertEqual(
            eventos.count(),
            2,
        )

        evento_asignacion = eventos[0]
        evento_cambio = eventos[1]

        self.assertEqual(
            evento_asignacion.tipo_accion,
            (
                ActivityHistory
                .TIPO_RESPONSABLE_DEUDAS_ASIGNADO
            ),
        )

        self.assertEqual(
            evento_cambio.tipo_accion,
            (
                ActivityHistory
                .TIPO_RESPONSABLE_DEUDAS_CAMBIADO
            ),
        )

        for evento in eventos:
            self.assertEqual(
                evento.usuario,
                self.fernando,
            )

            self.assertEqual(
                evento.usuario_username,
                "fernando_sc60",
            )

            self.assertIsNotNone(
                evento.fecha_evento
            )

            self.assertEqual(
                evento.datos[
                    "asignado_por"
                ]["usuario_id"],
                self.fernando.id,
            )

            self.assertIsNotNone(
                evento.datos["fecha_asignacion"]
            )

        self.assertEqual(
            evento_cambio.datos[
                "responsable_anterior"
            ]["responsable_username"],
            "carlita_sc60",
        )

        self.assertEqual(
            evento_cambio.datos[
                "responsable_nuevo"
            ]["username"],
            "damarys_sc60",
        )

    def test_reasignar_mismo_usuario_no_duplica_registros(
        self,
    ):
        primera = self.asignar(
            self.carlita
        )

        segunda = self.asignar(
            self.carlita
        )

        self.assertEqual(
            primera.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            segunda.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            segunda.data["cambio_realizado"]
        )

        self.assertEqual(
            segunda.data["mensaje"],
            (
                "El usuario seleccionado ya es el "
                "responsable vigente de las deudas."
            ),
        )

        self.assertEqual(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo
            ).count(),
            1,
        )

        self.assertEqual(
            ActivityHistory.objects.filter(
                grupo=self.grupo,
                tipo_accion__in=[
                    ActivityHistory
                    .TIPO_RESPONSABLE_DEUDAS_ASIGNADO,
                    ActivityHistory
                    .TIPO_RESPONSABLE_DEUDAS_CAMBIADO,
                ],
            ).count(),
            1,
        )

    def test_solo_responsable_vigente_puede_revisar_solicitudes(
        self,
    ):
        self.asignar(
            self.carlita
        )

        self.assertTrue(
            self.grupo.puede_revisar_solicitudes_deuda(
                self.carlita
            )
        )

        self.assertFalse(
            self.grupo.puede_revisar_solicitudes_deuda(
                self.fernando
            )
        )

        self.assertFalse(
            self.grupo.puede_revisar_solicitudes_deuda(
                self.damarys
            )
        )

        self.client.force_authenticate(
            user=self.carlita
        )

        respuesta_responsable = self.client.get(
            self.url
        )

        self.client.force_authenticate(
            user=self.damarys
        )

        respuesta_otro = self.client.get(
            self.url
        )

        self.assertTrue(
            respuesta_responsable.data[
                "puede_revisar_solicitudes"
            ]
        )

        self.assertFalse(
            respuesta_otro.data[
                "puede_revisar_solicitudes"
            ]
        )

        self.client.force_authenticate(
            user=self.fernando
        )

        self.asignar(
            self.damarys
        )

        self.assertFalse(
            self.grupo.puede_revisar_solicitudes_deuda(
                self.carlita
            )
        )

        self.assertTrue(
            self.grupo.puede_revisar_solicitudes_deuda(
                self.damarys
            )
        )

    def test_no_se_puede_retirar_responsable_vigente(
        self,
    ):
        self.asignar(
            self.carlita
        )

        response = self.client.delete(
            (
                f"/api/grupos/{self.grupo.id}/"
                f"participantes/{self.carlita.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["error"],
            (
                "No puedes retirar al responsable "
                "vigente de las deudas. Primero debes "
                "asignar otro responsable."
            ),
        )

        self.membresia_carlita.refresh_from_db()

        self.assertTrue(
            self.membresia_carlita.activo
        )

        self.assertEqual(
            self.grupo.responsable_deudas,
            self.carlita,
        )

    def test_responsable_anterior_puede_retirarse_tras_cambio(
        self,
    ):
        self.asignar(
            self.carlita
        )

        self.asignar(
            self.damarys
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

        self.membresia_carlita.refresh_from_db()

        self.assertFalse(
            self.membresia_carlita.activo
        )

        self.assertEqual(
            self.grupo.responsable_deudas,
            self.damarys,
        )

    def test_snapshots_de_asignacion_permanecen_tras_cambio_nombre(
        self,
    ):
        self.asignar(
            self.carlita
        )

        asignacion = self.obtener_asignacion_vigente()

        self.carlita.username = "carlita_modificada_sc60"
        self.carlita.save(
            update_fields=["username"]
        )

        self.fernando.username = "fernando_modificado_sc60"
        self.fernando.save(
            update_fields=["username"]
        )

        asignacion.refresh_from_db()

        self.assertEqual(
            asignacion.responsable_username,
            "carlita_sc60",
        )

        self.assertEqual(
            asignacion.asignado_por_username,
            "fernando_sc60",
        )

        evento = ActivityHistory.objects.get(
            grupo=self.grupo,
            tipo_accion=(
                ActivityHistory
                .TIPO_RESPONSABLE_DEUDAS_ASIGNADO
            ),
        )

        self.assertEqual(
            evento.usuario_username,
            "fernando_sc60",
        )

        self.assertEqual(
            evento.datos[
                "responsable_nuevo"
            ]["username"],
            "carlita_sc60",
        )

    def test_fallo_del_historial_revierte_asignacion_y_cambio(
        self,
    ):
        with patch(
            "expenses.models.ActivityHistory.registrar",
            side_effect=RuntimeError(
                "Fallo simulado del historial"
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.grupo.asignar_responsable_deudas(
                    responsable=self.carlita,
                    asignado_por=self.fernando,
                )

        self.assertFalse(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo
            ).exists()
        )

        self.grupo.asignar_responsable_deudas(
            responsable=self.carlita,
            asignado_por=self.fernando,
        )

        with patch(
            "expenses.models.ActivityHistory.registrar",
            side_effect=RuntimeError(
                "Fallo simulado al cambiar responsable"
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.grupo.asignar_responsable_deudas(
                    responsable=self.damarys,
                    asignado_por=self.fernando,
                )

        asignacion = self.obtener_asignacion_vigente()

        self.assertEqual(
            asignacion.responsable,
            self.carlita,
        )

        self.assertEqual(
            DebtReviewAssignment.objects.filter(
                grupo=self.grupo
            ).count(),
            1,
        )

    def test_usuario_retirado_y_externo_no_pueden_consultar(
        self,
    ):
        self.asignar(
            self.carlita
        )

        for usuario in [
            self.retirado,
            self.externo,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            response = self.client.get(
                self.url
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_usuario_no_autenticado_no_puede_acceder(
        self,
    ):
        self.client.force_authenticate(
            user=None
        )

        respuestas = [
            self.client.get(
                self.url
            ),
            self.client.put(
                self.url,
                {
                    "responsable_id": self.carlita.id,
                },
                format="json",
            ),
            self.client.patch(
                self.url,
                {
                    "responsable_id": self.carlita.id,
                },
                format="json",
            ),
        ]

        for response in respuestas:
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )


class CasoExcepcionalTodosDebenSC61Test(APITestCase):

    def setUp(self):
        self.fernando = User.objects.create_user(
            username="fernando_sc61",
            email="fernando_sc61@example.com",
            password="Prueba123",
        )

        self.carlita = User.objects.create_user(
            username="carlita_sc61",
            email="carlita_sc61@example.com",
            password="Prueba123",
        )

        self.damarys = User.objects.create_user(
            username="damarys_sc61",
            email="damarys_sc61@example.com",
            password="Prueba123",
        )

        self.externo = User.objects.create_user(
            username="externo_sc61",
            email="externo_sc61@example.com",
            password="Prueba123",
        )

        self.momento_base = timezone.now()

        self.grupo = Group.objects.create(
            nombre="Actividad todos deben SC-61",
            descripcion=(
                "Caso excepcional con todos los "
                "participantes en deuda"
            ),
            creador=self.fernando,
            fecha_inicio=(
                self.momento_base
                - timedelta(days=3)
            ),
            fecha_fin=(
                self.momento_base
                - timedelta(hours=1)
            ),
        )

        self.grupo.participantes.add(
            self.fernando,
            self.carlita,
            self.damarys,
        )

        for usuario in [
            self.fernando,
            self.carlita,
            self.damarys,
        ]:
            GroupMembership.objects.create(
                grupo=self.grupo,
                usuario=usuario,
            )

        self.gasto = Expense.objects.create(
            grupo=self.grupo,
            descripcion="Gasto común SC-61",
            monto=Decimal("90.00"),
            fecha_gasto="2026-07-26",
            registrado_por=self.fernando,
        )
        self.gasto.sincronizar_integrantes_activos()

        Payment.objects.create(
            grupo=self.grupo,
            pagador=self.fernando,
            monto=Decimal("5.00"),
            fecha_pago="2026-07-26",
            registrado_por=self.fernando,
        )

        Payment.objects.create(
            grupo=self.grupo,
            pagador=self.carlita,
            monto=Decimal("10.00"),
            fecha_pago="2026-07-26",
            registrado_por=self.carlita,
        )

        self.grupo.asignar_responsable_deudas(
            responsable=self.carlita,
            asignado_por=self.fernando,
            momento=(
                self.momento_base
                - timedelta(hours=2)
            ),
        )

        self.url_saldos = (
            f"/api/grupos/{self.grupo.id}/"
            "saldos-cierre/"
        )

        self.url_deudas = (
            f"/api/grupos/{self.grupo.id}/"
            "deudas/"
        )

        self.url_mi_deuda = (
            f"/api/grupos/{self.grupo.id}/"
            "mi-deuda/"
        )

        self.url_revision = (
            f"/api/grupos/{self.grupo.id}/"
            "revision-deudas/"
        )

        self.url_historial = (
            f"/api/grupos/{self.grupo.id}/"
            "historial/"
        )

        self.client.force_authenticate(
            user=self.fernando
        )

    def cerrar_actividad(self):
        resultado = self.grupo.cerrar_automaticamente(
            momento=self.momento_base
        )

        self.grupo.refresh_from_db()

        return resultado

    def deudas_por_usuario(self):
        return {
            deuda.participante_username: deuda
            for deuda in Debt.objects.filter(
                grupo=self.grupo
            )
        }

    def test_detecta_caso_cuando_todos_los_obligados_deben(
        self,
    ):
        resultado = self.cerrar_actividad()

        self.assertTrue(
            resultado
        )

        self.assertTrue(
            self.grupo.caso_excepcional_todos_deben
        )

        self.assertIsNotNone(
            self.grupo.fecha_deteccion_todos_deben
        )

        resumen = (
            self.grupo.obtener_resumen_saldos_cierre()
        )

        self.assertTrue(
            resumen["caso_todos_deben"]
        )

        self.assertEqual(
            resumen[
                "total_participantes_con_obligacion"
            ],
            3,
        )

    def test_actividad_cierra_correctamente_aunque_todos_deban(
        self,
    ):
        resultado = self.cerrar_actividad()

        self.assertTrue(
            resultado
        )

        self.assertEqual(
            self.grupo.estado,
            Group.ESTADO_CERRADA,
        )

        self.assertIsNotNone(
            self.grupo.fecha_cierre_automatico
        )

        self.assertIsNotNone(
            self.grupo.fecha_generacion_saldos
        )

        self.assertEqual(
            ClosingBalance.objects.filter(
                grupo=self.grupo
            ).count(),
            3,
        )

        self.assertEqual(
            Debt.objects.filter(
                grupo=self.grupo
            ).count(),
            3,
        )

    def test_cada_deuda_pertenece_a_actividad_y_sin_acreedor(
        self,
    ):
        self.cerrar_actividad()

        response = self.client.get(
            self.url_deudas
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data[
                "caso_excepcional_todos_deben"
            ]
        )

        self.assertEqual(
            response.data["total_deudas"],
            3,
        )

        for deuda in response.data["deudas"]:
            self.assertEqual(
                deuda["grupo_id"],
                self.grupo.id,
            )

            self.assertTrue(
                deuda["asociada_a_actividad"]
            )

            self.assertIsNone(
                deuda["acreedor"]
            )

    def test_responsable_no_se_convierte_en_acreedor(
        self,
    ):
        self.cerrar_actividad()

        response = self.client.get(
            self.url_revision
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(
            user=self.carlita
        )

        response = self.client.get(
            self.url_revision
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["responsable"]["username"],
            "carlita_sc61",
        )

        for deuda in response.data["deudas"]:
            self.assertIsNone(
                deuda["acreedor"]
            )

        deuda_responsable = next(
            deuda
            for deuda in response.data["deudas"]
            if deuda["participante"]["username"]
            == "carlita_sc61"
        )

        self.assertTrue(
            deuda_responsable["es_deuda_propia"]
        )

    def test_cada_participante_conserva_su_saldo_correcto(
        self,
    ):
        self.cerrar_actividad()

        deudas = self.deudas_por_usuario()

        self.assertEqual(
            deudas["fernando_sc61"].saldo_pendiente,
            Decimal("25.00"),
        )

        self.assertEqual(
            deudas["carlita_sc61"].saldo_pendiente,
            Decimal("20.00"),
        )

        self.assertEqual(
            deudas["damarys_sc61"].saldo_pendiente,
            Decimal("30.00"),
        )

        for deuda in deudas.values():
            self.assertEqual(
                deuda.monto_original,
                deuda.saldo_pendiente,
            )

    def test_no_se_generan_deudas_duplicadas(
        self,
    ):
        primer_cierre = self.cerrar_actividad()

        segundo_cierre = (
            self.grupo.cerrar_automaticamente(
                momento=(
                    self.momento_base
                    + timedelta(minutes=5)
                )
            )
        )

        segundo_calculo = (
            self.grupo.generar_saldos_cierre(
                momento=(
                    self.momento_base
                    + timedelta(minutes=10)
                )
            )
        )

        self.assertTrue(
            primer_cierre
        )

        self.assertFalse(
            segundo_cierre
        )

        self.assertFalse(
            segundo_calculo["generados"]
        )

        self.assertEqual(
            Debt.objects.filter(
                grupo=self.grupo
            ).count(),
            3,
        )

        for usuario in [
            self.fernando,
            self.carlita,
            self.damarys,
        ]:
            self.assertEqual(
                Debt.objects.filter(
                    grupo=self.grupo,
                    participante=usuario,
                ).count(),
                1,
            )

    def test_suma_de_deudas_coincide_con_total_pendiente(
        self,
    ):
        self.cerrar_actividad()

        suma_deudas = sum(
            Debt.objects.filter(
                grupo=self.grupo
            ).values_list(
                "saldo_pendiente",
                flat=True,
            ),
            Decimal("0.00"),
        )

        suma_saldos = sum(
            ClosingBalance.objects.filter(
                grupo=self.grupo
            ).values_list(
                "saldo_pendiente",
                flat=True,
            ),
            Decimal("0.00"),
        )

        resumen = (
            self.grupo.obtener_resumen_saldos_cierre()
        )

        self.assertEqual(
            suma_deudas,
            Decimal("75.00"),
        )

        self.assertEqual(
            suma_saldos,
            Decimal("75.00"),
        )

        self.assertEqual(
            Decimal(resumen["total_pendiente"]),
            Decimal("75.00"),
        )

    def test_endpoint_muestra_mensaje_todos_deben(
        self,
    ):
        self.cerrar_actividad()

        response = self.client.get(
            self.url_saldos
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data[
                "caso_excepcional_todos_deben"
            ]
        )

        self.assertEqual(
            response.data["mensaje"],
            (
                "Todos los participantes con obligaciones "
                "mantienen saldos pendientes."
            ),
        )

        self.assertEqual(
            response.data["resumen"][
                "total_participantes_con_obligacion"
            ],
            3,
        )

        self.assertEqual(
            response.data["resumen"]["total_pendiente"],
            "75.00",
        )

    def test_cada_participante_consulta_su_deuda(
        self,
    ):
        self.cerrar_actividad()

        casos = [
            (
                self.fernando,
                "fernando_sc61",
                Decimal("25.00"),
            ),
            (
                self.carlita,
                "carlita_sc61",
                Decimal("20.00"),
            ),
            (
                self.damarys,
                "damarys_sc61",
                Decimal("30.00"),
            ),
        ]

        for usuario, username, monto in casos:
            self.client.force_authenticate(
                user=usuario
            )

            response = self.client.get(
                self.url_mi_deuda
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
            )

            self.assertTrue(
                response.data[
                    "caso_excepcional_todos_deben"
                ]
            )

            deuda = response.data["deuda"]

            self.assertEqual(
                deuda["participante"]["username"],
                username,
            )

            self.assertEqual(
                Decimal(deuda["saldo_pendiente"]),
                monto,
            )

            self.assertTrue(
                deuda["es_deuda_propia"]
            )

            self.assertIsNone(
                deuda["acreedor"]
            )

    def test_responsable_revisa_deudas_de_todos(
        self,
    ):
        self.cerrar_actividad()

        self.client.force_authenticate(
            user=self.carlita
        )

        response = self.client.get(
            self.url_revision
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_deudas"],
            3,
        )

        self.assertEqual(
            response.data["monto_total_pendiente"],
            "75.00",
        )

        participantes = {
            deuda["participante"]["username"]
            for deuda in response.data["deudas"]
        }

        self.assertSetEqual(
            participantes,
            {
                "fernando_sc61",
                "carlita_sc61",
                "damarys_sc61",
            },
        )

        for deuda in response.data["deudas"]:
            self.assertTrue(
                deuda["puede_revisar_solicitudes"]
            )

    def test_no_responsable_no_puede_revisar_deudas(
        self,
    ):
        self.cerrar_actividad()

        for usuario in [
            self.fernando,
            self.damarys,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            response = self.client.get(
                self.url_revision
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
            )

    def test_pagos_previos_al_cierre_se_descontaron(
        self,
    ):
        self.cerrar_actividad()

        saldos = {
            saldo.participante_username: saldo
            for saldo in ClosingBalance.objects.filter(
                grupo=self.grupo
            )
        }

        self.assertEqual(
            saldos["fernando_sc61"].cuota_total,
            Decimal("30.00"),
        )

        self.assertEqual(
            saldos["fernando_sc61"].total_pagado,
            Decimal("5.00"),
        )

        self.assertEqual(
            saldos["fernando_sc61"].saldo_pendiente,
            Decimal("25.00"),
        )

        self.assertEqual(
            saldos["carlita_sc61"].cuota_total,
            Decimal("30.00"),
        )

        self.assertEqual(
            saldos["carlita_sc61"].total_pagado,
            Decimal("10.00"),
        )

        self.assertEqual(
            saldos["carlita_sc61"].saldo_pendiente,
            Decimal("20.00"),
        )

    def test_saldo_cero_no_se_incluye_como_deudor(
        self,
    ):
        Payment.objects.create(
            grupo=self.grupo,
            pagador=self.damarys,
            monto=Decimal("30.00"),
            fecha_pago="2026-07-26",
            registrado_por=self.damarys,
        )

        self.cerrar_actividad()

        self.assertFalse(
            self.grupo.caso_excepcional_todos_deben
        )

        self.assertEqual(
            Debt.objects.filter(
                grupo=self.grupo
            ).count(),
            2,
        )

        self.assertFalse(
            Debt.objects.filter(
                grupo=self.grupo,
                participante=self.damarys,
            ).exists()
        )

        saldo_damarys = ClosingBalance.objects.get(
            grupo=self.grupo,
            participante=self.damarys,
        )

        self.assertEqual(
            saldo_damarys.saldo_pendiente,
            Decimal("0.00"),
        )

        self.assertEqual(
            saldo_damarys.estado,
            ClosingBalance.ESTADO_SALDADO,
        )

    def test_caso_excepcional_queda_en_historial(
        self,
    ):
        self.cerrar_actividad()

        evento = ActivityHistory.objects.get(
            grupo=self.grupo,
            tipo_accion=(
                ActivityHistory
                .TIPO_CASO_TODOS_DEBEN_DETECTADO
            ),
        )

        self.assertIsNone(
            evento.usuario
        )

        self.assertEqual(
            evento.usuario_username,
            "sistema",
        )

        self.assertTrue(
            evento.datos["caso_todos_deben"]
        )

        self.assertEqual(
            evento.datos[
                "total_participantes_con_obligacion"
            ],
            3,
        )

        self.assertEqual(
            evento.datos["total_deudores"],
            3,
        )

        self.assertEqual(
            evento.datos["total_pendiente"],
            "75.00",
        )

        self.assertFalse(
            evento.datos[
                "responsable_deudas"
            ]["es_acreedor_automatico"]
        )

        response = self.client.get(
            self.url_historial
        )

        tipos = {
            item["tipo_accion"]
            for item in response.data["eventos"]
        }

        self.assertIn(
            (
                ActivityHistory
                .TIPO_CASO_TODOS_DEBEN_DETECTADO
            ),
            tipos,
        )

    def test_fallo_del_calculo_no_deja_registros_parciales(
        self,
    ):
        with patch(
            "expenses.models.ActivityHistory.registrar",
            side_effect=RuntimeError(
                "Fallo simulado del caso todos deben"
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.grupo.cerrar_automaticamente(
                    momento=self.momento_base
                )

        self.grupo.refresh_from_db()

        self.assertIsNone(
            self.grupo.fecha_cierre_automatico
        )

        self.assertIsNone(
            self.grupo.fecha_generacion_saldos
        )

        self.assertFalse(
            self.grupo.caso_excepcional_todos_deben
        )

        self.assertIsNone(
            self.grupo.fecha_deteccion_todos_deben
        )

        self.assertFalse(
            ClosingBalance.objects.filter(
                grupo=self.grupo
            ).exists()
        )

        self.assertFalse(
            Debt.objects.filter(
                grupo=self.grupo
            ).exists()
        )

        self.assertFalse(
            ActivityHistory.objects.filter(
                grupo=self.grupo,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_CASO_TODOS_DEBEN_DETECTADO
                ),
            ).exists()
        )

    def test_informacion_permanece_disponible_despues_cierre(
        self,
    ):
        self.cerrar_actividad()

        respuestas = [
            self.client.get(
                self.url_saldos
            ),
            self.client.get(
                self.url_deudas
            ),
            self.client.get(
                self.url_mi_deuda
            ),
            self.client.get(
                self.url_historial
            ),
        ]

        for response in respuestas:
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
            )

        detalle = self.client.get(
            f"/api/grupos/{self.grupo.id}/"
        )

        self.assertEqual(
            detalle.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            detalle.data[
                "caso_excepcional_todos_deben"
            ]
        )

        self.assertIsNotNone(
            detalle.data[
                "fecha_deteccion_todos_deben"
            ]
        )

        self.assertEqual(
            detalle.data[
                "mensaje_caso_todos_deben"
            ],
            (
                "Todos los participantes con obligaciones "
                "mantienen saldos pendientes."
            ),
        )

    def test_externo_no_puede_consultar_deudas_del_caso(
        self,
    ):
        self.cerrar_actividad()

        self.client.force_authenticate(
            user=self.externo
        )

        for ruta in [
            self.url_saldos,
            self.url_deudas,
            self.url_mi_deuda,
            self.url_revision,
        ]:
            response = self.client.get(
                ruta
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_404_NOT_FOUND,
            )


class AdvertenciaParticipantesConDeudasSC62Test(
    APITestCase
):

    def setUp(self):
        self.creador = User.objects.create_user(
            username="creador_sc62",
            email="creador_sc62@example.com",
            password="Prueba123",
        )

        self.candidato = User.objects.create_user(
            username="candidato_sc62",
            email="candidato_sc62@example.com",
            password="Prueba123",
        )

        self.sin_deudas = User.objects.create_user(
            username="sin_deudas_sc62",
            email="sin_deudas_sc62@example.com",
            password="Prueba123",
        )

        self.solo_resueltas = User.objects.create_user(
            username="solo_resueltas_sc62",
            email="solo_resueltas_sc62@example.com",
            password="Prueba123",
        )

        self.externo = User.objects.create_user(
            username="externo_sc62",
            email="externo_sc62@example.com",
            password="Prueba123",
        )

        ahora = timezone.now()

        self.grupo_destino = Group.objects.create(
            nombre="Actividad destino SC-62",
            descripcion="Ingreso con advertencia de deudas",
            creador=self.creador,
            fecha_inicio=ahora - timedelta(hours=1),
            fecha_fin=ahora + timedelta(days=2),
        )

        self.grupo_destino.participantes.add(
            self.creador
        )

        GroupMembership.objects.create(
            grupo=self.grupo_destino,
            usuario=self.creador,
        )

        self.deuda_pendiente = self.crear_deuda(
            usuario=self.candidato,
            nombre_grupo="Deuda pendiente SC-62",
            monto_original=Decimal("25.00"),
            saldo_pendiente=Decimal("25.00"),
            estado=Debt.ESTADO_PENDIENTE,
        )

        self.deuda_revision = self.crear_deuda(
            usuario=self.candidato,
            nombre_grupo="Deuda en revisión SC-62",
            monto_original=Decimal("10.00"),
            saldo_pendiente=Decimal("10.00"),
            estado=Debt.ESTADO_EN_REVISION,
        )

        self.deuda_resuelta = self.crear_deuda(
            usuario=self.candidato,
            nombre_grupo="Deuda resuelta SC-62",
            monto_original=Decimal("20.00"),
            saldo_pendiente=Decimal("0.00"),
            estado=Debt.ESTADO_RESUELTA,
        )

        self.deuda_resuelta_otro_usuario = (
            self.crear_deuda(
                usuario=self.solo_resueltas,
                nombre_grupo=(
                    "Única deuda resuelta SC-62"
                ),
                monto_original=Decimal("15.00"),
                saldo_pendiente=Decimal("0.00"),
                estado=Debt.ESTADO_RESUELTA,
            )
        )

        self.url_agregar = (
            f"/api/grupos/{self.grupo_destino.id}/"
            "participantes/"
        )

        self.client.force_authenticate(
            user=self.creador
        )

    def crear_deuda(
        self,
        usuario,
        nombre_grupo,
        monto_original,
        saldo_pendiente,
        estado,
    ):
        ahora = timezone.now()

        grupo = Group.objects.create(
            nombre=nombre_grupo,
            descripcion="Actividad histórica con deuda",
            creador=self.creador,
            fecha_inicio=ahora - timedelta(days=5),
            fecha_fin=ahora - timedelta(days=3),
            fecha_cierre_automatico=(
                ahora - timedelta(days=3)
            ),
            fecha_generacion_saldos=(
                ahora - timedelta(days=3)
            ),
        )

        saldo = ClosingBalance.objects.create(
            grupo=grupo,
            grupo_nombre=grupo.nombre,
            participante=usuario,
            participante_username=usuario.username,
            cuota_total=monto_original,
            total_pagado=(
                monto_original - saldo_pendiente
            ),
            saldo_pendiente=saldo_pendiente,
            estado=(
                ClosingBalance.ESTADO_PENDIENTE
                if saldo_pendiente > Decimal("0.00")
                else ClosingBalance.ESTADO_SALDADO
            ),
        )

        return Debt.objects.create(
            grupo=grupo,
            grupo_nombre=grupo.nombre,
            saldo_cierre=saldo,
            participante=usuario,
            participante_username=usuario.username,
            monto_original=monto_original,
            saldo_pendiente=saldo_pendiente,
            estado=estado,
            fecha_resolucion=(
                ahora
                if estado == Debt.ESTADO_RESUELTA
                else None
            ),
        )

    def url_advertencia(self, usuario):
        return (
            f"/api/grupos/{self.grupo_destino.id}/"
            f"participantes/{usuario.id}/"
            "advertencia-deudas/"
        )

    def test_consulta_deudas_activas_del_usuario_seleccionado(
        self,
    ):
        response = self.client.get(
            self.url_advertencia(
                self.candidato
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["tiene_deudas_pendientes"]
        )

        self.assertTrue(
            response.data["requiere_confirmacion"]
        )

        self.assertEqual(
            response.data[
                "cantidad_deudas_pendientes"
            ],
            2,
        )

        self.assertEqual(
            response.data["monto_total_pendiente"],
            "35.00",
        )

    def test_deudas_resueltas_y_saldadas_no_advierten(
        self,
    ):
        response = self.client.get(
            self.url_advertencia(
                self.solo_resueltas
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            response.data["tiene_deudas_pendientes"]
        )

        self.assertFalse(
            response.data["requiere_confirmacion"]
        )

        self.assertEqual(
            response.data[
                "cantidad_deudas_pendientes"
            ],
            0,
        )

        self.assertEqual(
            response.data["monto_total_pendiente"],
            "0.00",
        )

    def test_advertencia_identifica_obligaciones_pendientes(
        self,
    ):
        response = self.client.get(
            self.url_advertencia(
                self.candidato
            )
        )

        mensaje = response.data["mensaje"]

        self.assertIn(
            "candidato_sc62",
            mensaje,
        )

        self.assertIn(
            "obligación(es) pendiente(s)",
            mensaje,
        )

        self.assertIn(
            "$35.00",
            mensaje,
        )

        self.assertIn(
            "confirmar",
            mensaje.lower(),
        )

    def test_advertencia_no_expone_detalles_de_terceros(
        self,
    ):
        response = self.client.get(
            self.url_advertencia(
                self.candidato
            )
        )

        self.assertSetEqual(
            set(response.data.keys()),
            {
                "usuario",
                "tiene_deudas_pendientes",
                "requiere_confirmacion",
                "cantidad_deudas_pendientes",
                "monto_total_pendiente",
                "mensaje",
            },
        )

        self.assertNotIn(
            "deudas",
            response.data,
        )

        self.assertNotIn(
            "participantes",
            response.data,
        )

        self.assertNotIn(
            "grupo_nombre",
            response.data,
        )

    def test_consultar_advertencia_no_agrega_participante(
        self,
    ):
        response = self.client.get(
            self.url_advertencia(
                self.candidato
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                grupo=self.grupo_destino,
                usuario=self.candidato,
                activo=True,
            ).exists()
        )

        self.assertFalse(
            self.grupo_destino.participantes.filter(
                id=self.candidato.id
            ).exists()
        )

    def test_ingreso_con_deuda_exige_confirmacion(
        self,
    ):
        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.candidato.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertFalse(
            response.data["incorporado"]
        )

        self.assertTrue(
            response.data["requiere_confirmacion"]
        )

        self.assertTrue(
            response.data["advertencia"][
                "tiene_deudas_pendientes"
            ]
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                grupo=self.grupo_destino,
                usuario=self.candidato,
                activo=True,
            ).exists()
        )

    def test_cancelar_no_crea_membresia_ni_historial(
        self,
    ):
        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.candidato.id,
                "confirmar_deudas": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                grupo=self.grupo_destino,
                usuario=self.candidato,
            ).exists()
        )

        self.assertFalse(
            ActivityHistory.objects.filter(
                grupo=self.grupo_destino,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_PARTICIPANTE_INGRESO
                ),
            ).exists()
        )

    def test_creador_confirma_y_puede_continuar_ingreso(
        self,
    ):
        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.candidato.id,
                "confirmar_deudas": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["incorporado"]
        )

        self.assertFalse(
            response.data["requiere_confirmacion"]
        )

        self.assertTrue(
            response.data["advertencia"][
                "tiene_deudas_pendientes"
            ]
        )

        self.assertTrue(
            GroupMembership.objects.filter(
                grupo=self.grupo_destino,
                usuario=self.candidato,
                activo=True,
            ).exists()
        )

        self.assertTrue(
            self.grupo_destino.participantes.filter(
                id=self.candidato.id
            ).exists()
        )

    def test_usuario_sin_deudas_sigue_flujo_normal(
        self,
    ):
        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.sin_deudas.id,
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

        self.assertTrue(
            response.data["incorporado"]
        )

        self.assertFalse(
            response.data["advertencia"][
                "tiene_deudas_pendientes"
            ]
        )

        self.assertTrue(
            GroupMembership.objects.filter(
                grupo=self.grupo_destino,
                usuario=self.sin_deudas,
                activo=True,
            ).exists()
        )

    def test_sistema_revalida_deudas_al_confirmar(
        self,
    ):
        primera_consulta = self.client.get(
            self.url_advertencia(
                self.sin_deudas
            )
        )

        self.assertFalse(
            primera_consulta.data[
                "tiene_deudas_pendientes"
            ]
        )

        deuda_nueva = self.crear_deuda(
            usuario=self.sin_deudas,
            nombre_grupo="Deuda nueva SC-62",
            monto_original=Decimal("18.50"),
            saldo_pendiente=Decimal("18.50"),
            estado=Debt.ESTADO_PENDIENTE,
        )

        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.sin_deudas.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertEqual(
            response.data["advertencia"][
                "cantidad_deudas_pendientes"
            ],
            1,
        )

        self.assertEqual(
            response.data["advertencia"][
                "monto_total_pendiente"
            ],
            "18.50",
        )

        self.assertTrue(
            Debt.objects.filter(
                id=deuda_nueva.id
            ).exists()
        )

        self.assertFalse(
            GroupMembership.objects.filter(
                grupo=self.grupo_destino,
                usuario=self.sin_deudas,
                activo=True,
            ).exists()
        )

    def test_confirmacion_usa_valores_actualizados(
        self,
    ):
        consulta = self.client.get(
            self.url_advertencia(
                self.candidato
            )
        )

        self.assertEqual(
            consulta.data["monto_total_pendiente"],
            "35.00",
        )

        self.deuda_pendiente.saldo_pendiente = (
            Decimal("12.00")
        )
        self.deuda_pendiente.save(
            update_fields=[
                "saldo_pendiente",
                "fecha_actualizacion",
            ]
        )

        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.candidato.id,
                "confirmar_deudas": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["advertencia"][
                "monto_total_pendiente"
            ],
            "22.00",
        )

        evento = ActivityHistory.objects.get(
            grupo=self.grupo_destino,
            tipo_accion=(
                ActivityHistory
                .TIPO_PARTICIPANTE_INGRESO
            ),
        )

        self.assertEqual(
            evento.datos[
                "monto_total_pendiente"
            ],
            "22.00",
        )

        self.assertTrue(
            evento.datos[
                "confirmacion_del_creador"
            ]
        )

    def test_ingreso_exitoso_se_registra_en_historial(
        self,
    ):
        response = self.client.post(
            self.url_agregar,
            {
                "usuario_id": self.candidato.id,
                "confirmar_deudas": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        evento = ActivityHistory.objects.get(
            grupo=self.grupo_destino,
            tipo_accion=(
                ActivityHistory
                .TIPO_PARTICIPANTE_INGRESO
            ),
        )

        self.assertEqual(
            evento.usuario,
            self.creador,
        )

        self.assertEqual(
            evento.datos[
                "participante_username"
            ],
            "candidato_sc62",
        )

        self.assertTrue(
            evento.datos[
                "tenia_deudas_pendientes"
            ]
        )

        self.assertEqual(
            evento.datos[
                "cantidad_deudas_pendientes"
            ],
            2,
        )

    def test_usuarios_no_autorizados_no_consultan_deudas_ajenas(
        self,
    ):
        for usuario in [
            self.externo,
            self.candidato,
        ]:
            self.client.force_authenticate(
                user=usuario
            )

            response = self.client.get(
                self.url_advertencia(
                    self.candidato
                )
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_404_NOT_FOUND,
            )

    def test_usuario_no_autenticado_no_puede_consultar(
        self,
    ):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            self.url_advertencia(
                self.candidato
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class ConsultaDeudasPropiasSolicitudesSC63Test(
    APITestCase
):

    def setUp(self):
        self.media_temporal = TemporaryDirectory()
        self.override_media = override_settings(
            MEDIA_ROOT=self.media_temporal.name
        )
        self.override_media.enable()
        self.addCleanup(
            self.override_media.disable
        )
        self.addCleanup(
            self.media_temporal.cleanup
        )

        self.usuario = User.objects.create_user(
            username="usuario_sc63",
            email="usuario_sc63@example.com",
            password="Prueba123",
        )

        self.otro_usuario = User.objects.create_user(
            username="otro_sc63",
            email="otro_sc63@example.com",
            password="Prueba123",
        )

        self.revisor = User.objects.create_user(
            username="revisor_sc63",
            email="revisor_sc63@example.com",
            password="Prueba123",
        )

        self.momento_base = timezone.now()

        self.deuda_reciente = self.crear_deuda(
            usuario=self.usuario,
            nombre_grupo="Actividad reciente SC-63",
            monto_original=Decimal("40.00"),
            saldo_pendiente=Decimal("40.00"),
            estado=Debt.ESTADO_EN_REVISION,
            fecha_generacion=(
                self.momento_base
                - timedelta(hours=1)
            ),
            retirar_usuario=True,
        )

        self.deuda_antigua = self.crear_deuda(
            usuario=self.usuario,
            nombre_grupo="Actividad antigua SC-63",
            monto_original=Decimal("20.00"),
            saldo_pendiente=Decimal("0.00"),
            estado=Debt.ESTADO_RESUELTA,
            fecha_generacion=(
                self.momento_base
                - timedelta(days=2)
            ),
            retirar_usuario=False,
        )

        self.deuda_ajena = self.crear_deuda(
            usuario=self.otro_usuario,
            nombre_grupo="Actividad ajena SC-63",
            monto_original=Decimal("99.00"),
            saldo_pendiente=Decimal("99.00"),
            estado=Debt.ESTADO_PENDIENTE,
            fecha_generacion=(
                self.momento_base
                - timedelta(minutes=30)
            ),
            retirar_usuario=False,
        )

        self.solicitud_rechazada = (
            DebtResolutionRequest.objects.create(
                deuda=self.deuda_reciente,
                grupo=self.deuda_reciente.grupo,
                grupo_nombre=(
                    self.deuda_reciente.grupo_nombre
                ),
                solicitante=self.usuario,
                solicitante_username=(
                    self.usuario.username
                ),
                descripcion=(
                    "Solicitud revisada y rechazada."
                ),
                evidencia=self.archivo_prueba(
                    "evidencia_rechazada.pdf"
                ),
                evidencia_nombre_original=(
                    "evidencia_rechazada.pdf"
                ),
                estado=(
                    DebtResolutionRequest
                    .ESTADO_RECHAZADA
                ),
                decision=(
                    DebtResolutionRequest
                    .DECISION_RECHAZADA
                ),
                observacion_revision=(
                    "La evidencia no demuestra el pago."
                ),
                revisado_por=self.revisor,
                revisado_por_username=(
                    self.revisor.username
                ),
                fecha_envio=(
                    self.momento_base
                    - timedelta(hours=4)
                ),
                fecha_revision=(
                    self.momento_base
                    - timedelta(hours=3)
                ),
            )
        )

        self.solicitud_pendiente = (
            DebtResolutionRequest.objects.create(
                deuda=self.deuda_reciente,
                grupo=self.deuda_reciente.grupo,
                grupo_nombre=(
                    self.deuda_reciente.grupo_nombre
                ),
                solicitante=self.usuario,
                solicitante_username=(
                    self.usuario.username
                ),
                descripcion=(
                    "Nueva evidencia pendiente de revisión."
                ),
                evidencia=self.archivo_prueba(
                    "evidencia_pendiente.png",
                    contenido=b"imagen-prueba",
                    content_type="image/png",
                ),
                evidencia_nombre_original=(
                    "evidencia_pendiente.png"
                ),
                estado=(
                    DebtResolutionRequest
                    .ESTADO_PENDIENTE_REVISION
                ),
                fecha_envio=(
                    self.momento_base
                    - timedelta(hours=2)
                ),
            )
        )

        self.client.force_authenticate(
            user=self.usuario
        )

        self.url_listado = "/api/mis-deudas/"

    def archivo_prueba(
        self,
        nombre,
        contenido=b"%PDF-1.4 archivo de prueba",
        content_type="application/pdf",
    ):
        return SimpleUploadedFile(
            nombre,
            contenido,
            content_type=content_type,
        )

    def crear_deuda(
        self,
        usuario,
        nombre_grupo,
        monto_original,
        saldo_pendiente,
        estado,
        fecha_generacion,
        retirar_usuario,
    ):
        grupo = Group.objects.create(
            nombre=nombre_grupo,
            descripcion="Actividad cerrada con deuda",
            creador=self.revisor,
            fecha_inicio=(
                self.momento_base
                - timedelta(days=5)
            ),
            fecha_fin=(
                self.momento_base
                - timedelta(days=3)
            ),
            fecha_cierre_automatico=(
                self.momento_base
                - timedelta(days=3)
            ),
            fecha_generacion_saldos=(
                self.momento_base
                - timedelta(days=3)
            ),
        )

        grupo.participantes.add(
            self.revisor,
            usuario,
        )

        GroupMembership.objects.create(
            grupo=grupo,
            usuario=self.revisor,
        )

        membresia = GroupMembership.objects.create(
            grupo=grupo,
            usuario=usuario,
        )

        if retirar_usuario:
            membresia.retirar()
            grupo.participantes.remove(
                usuario
            )

        saldo = ClosingBalance.objects.create(
            grupo=grupo,
            grupo_nombre=grupo.nombre,
            participante=usuario,
            participante_username=usuario.username,
            cuota_total=monto_original,
            total_pagado=(
                monto_original - saldo_pendiente
            ),
            saldo_pendiente=saldo_pendiente,
            estado=(
                ClosingBalance.ESTADO_PENDIENTE
                if saldo_pendiente > Decimal("0.00")
                else ClosingBalance.ESTADO_SALDADO
            ),
        )

        deuda = Debt.objects.create(
            grupo=grupo,
            grupo_nombre=grupo.nombre,
            saldo_cierre=saldo,
            participante=usuario,
            participante_username=usuario.username,
            monto_original=monto_original,
            saldo_pendiente=saldo_pendiente,
            estado=estado,
            fecha_resolucion=(
                self.momento_base
                if estado == Debt.ESTADO_RESUELTA
                else None
            ),
        )

        Debt.objects.filter(
            id=deuda.id
        ).update(
            fecha_generacion=fecha_generacion
        )

        deuda.refresh_from_db()

        return deuda

    def test_usuario_consulta_unicamente_sus_deudas(
        self,
    ):
        response = self.client.get(
            self.url_listado
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_deudas"],
            2,
        )

        ids = {
            deuda["id"]
            for deuda in response.data["deudas"]
        }

        self.assertSetEqual(
            ids,
            {
                self.deuda_reciente.id,
                self.deuda_antigua.id,
            },
        )

        self.assertNotIn(
            self.deuda_ajena.id,
            ids,
        )

    def test_deuda_muestra_actividad_montos_estado_y_fecha(
        self,
    ):
        response = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_reciente.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        deuda = response.data["deuda"]

        self.assertEqual(
            deuda["actividad"]["id"],
            self.deuda_reciente.grupo_id,
        )

        self.assertEqual(
            deuda["actividad"]["nombre"],
            "Actividad reciente SC-63",
        )

        self.assertEqual(
            deuda["actividad"]["estado"],
            Group.ESTADO_CERRADA,
        )

        self.assertEqual(
            deuda["monto_original"],
            "40.00",
        )

        self.assertEqual(
            deuda["saldo_pendiente"],
            "40.00",
        )

        self.assertEqual(
            deuda["estado"],
            Debt.ESTADO_EN_REVISION,
        )

        self.assertEqual(
            deuda["estado_display"],
            "En revisión",
        )

        self.assertIsNotNone(
            deuda["fecha_generacion"]
        )

    def test_usuario_retirado_conserva_acceso_a_su_deuda(
        self,
    ):
        self.assertFalse(
            GroupMembership.objects.filter(
                grupo=self.deuda_reciente.grupo,
                usuario=self.usuario,
                activo=True,
            ).exists()
        )

        response = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_reciente.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["deuda"]["id"],
            self.deuda_reciente.id,
        )

    def test_actividades_cerradas_siguen_mostrando_deudas(
        self,
    ):
        response = self.client.get(
            self.url_listado
        )

        estados = {
            deuda["actividad"]["estado"]
            for deuda in response.data["deudas"]
        }

        self.assertSetEqual(
            estados,
            {
                Group.ESTADO_CERRADA,
            },
        )

    def test_cada_deuda_incluye_solicitudes_de_resolucion(
        self,
    ):
        response = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_reciente.id}/"
            )
        )

        deuda = response.data["deuda"]

        self.assertEqual(
            deuda["cantidad_solicitudes"],
            2,
        )

        self.assertEqual(
            len(deuda["solicitudes"]),
            2,
        )

        for solicitud in deuda["solicitudes"]:
            self.assertIn(
                "fecha_envio",
                solicitud,
            )

            self.assertIn(
                "descripcion",
                solicitud,
            )

            self.assertIn(
                "evidencia",
                solicitud,
            )

            self.assertIn(
                "estado",
                solicitud,
            )

    def test_solicitud_revisada_muestra_decision_y_observacion(
        self,
    ):
        response = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_reciente.id}/"
            )
        )

        rechazada = next(
            solicitud
            for solicitud in (
                response.data[
                    "deuda"
                ]["solicitudes"]
            )
            if solicitud["id"]
            == self.solicitud_rechazada.id
        )

        self.assertEqual(
            rechazada["estado"],
            (
                DebtResolutionRequest
                .ESTADO_RECHAZADA
            ),
        )

        self.assertEqual(
            rechazada["decision"],
            (
                DebtResolutionRequest
                .DECISION_RECHAZADA
            ),
        )

        self.assertEqual(
            rechazada["decision_display"],
            "Rechazada",
        )

        self.assertEqual(
            rechazada["observacion_revision"],
            "La evidencia no demuestra el pago.",
        )

        self.assertEqual(
            rechazada["revisado_por"]["username"],
            "revisor_sc63",
        )

        self.assertIsNotNone(
            rechazada["fecha_revision"]
        )

    def test_deudas_y_solicitudes_se_ordenan_mas_recientes(
        self,
    ):
        response = self.client.get(
            self.url_listado
        )

        self.assertEqual(
            response.data["deudas"][0]["id"],
            self.deuda_reciente.id,
        )

        self.assertEqual(
            response.data["deudas"][1]["id"],
            self.deuda_antigua.id,
        )

        solicitudes = response.data[
            "deudas"
        ][0]["solicitudes"]

        self.assertEqual(
            solicitudes[0]["id"],
            self.solicitud_pendiente.id,
        )

        self.assertEqual(
            solicitudes[1]["id"],
            self.solicitud_rechazada.id,
        )

    def test_usuario_identifica_solicitud_pendiente(
        self,
    ):
        response = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_reciente.id}/"
            )
        )

        deuda = response.data["deuda"]

        self.assertTrue(
            deuda["tiene_solicitud_pendiente"]
        )

        pendiente = next(
            solicitud
            for solicitud in deuda["solicitudes"]
            if solicitud["id"]
            == self.solicitud_pendiente.id
        )

        self.assertTrue(
            pendiente["pendiente_revision"]
        )

        self.assertTrue(
            pendiente["puede_editarse"]
        )

    def test_evidencia_permanece_disponible_en_consulta(
        self,
    ):
        response = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_reciente.id}/"
            )
        )

        solicitudes = response.data[
            "deuda"
        ]["solicitudes"]

        for solicitud in solicitudes:
            self.assertTrue(
                solicitud["evidencia"]
            )

            self.assertTrue(
                solicitud[
                    "evidencia_nombre_original"
                ]
            )

    def test_usuario_sin_deudas_recibe_mensaje_informativo(
        self,
    ):
        usuario_sin_deudas = User.objects.create_user(
            username="vacio_sc63",
            email="vacio_sc63@example.com",
            password="Prueba123",
        )

        self.client.force_authenticate(
            user=usuario_sin_deudas
        )

        response = self.client.get(
            self.url_listado
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_deudas"],
            0,
        )

        self.assertEqual(
            response.data["monto_total_pendiente"],
            "0.00",
        )

        self.assertEqual(
            response.data["deudas"],
            [],
        )

        self.assertEqual(
            response.data["mensaje"],
            "No tienes deudas registradas.",
        )

    def test_deuda_sin_solicitudes_muestra_mensaje(
        self,
    ):
        response = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_antigua.id}/"
            )
        )

        deuda = response.data["deuda"]

        self.assertEqual(
            deuda["cantidad_solicitudes"],
            0,
        )

        self.assertEqual(
            deuda["solicitudes"],
            [],
        )

        self.assertFalse(
            deuda["tiene_solicitud_pendiente"]
        )

        self.assertEqual(
            deuda["mensaje_solicitudes"],
            (
                "Esta deuda todavía no tiene "
                "solicitudes de resolución."
            ),
        )

    def test_usuario_no_puede_consultar_deuda_ajena(
        self,
    ):
        detalle = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_ajena.id}/"
            )
        )

        solicitudes = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_ajena.id}/solicitudes/"
            )
        )

        self.assertEqual(
            detalle.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            solicitudes.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_detalle_de_solicitud_es_privado(
        self,
    ):
        response = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_reciente.id}/solicitudes/"
                f"{self.solicitud_pendiente.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["solicitud"]["id"],
            self.solicitud_pendiente.id,
        )

        self.client.force_authenticate(
            user=self.otro_usuario
        )

        response_ajena = self.client.get(
            (
                f"/api/mis-deudas/"
                f"{self.deuda_reciente.id}/solicitudes/"
                f"{self.solicitud_pendiente.id}/"
            )
        )

        self.assertEqual(
            response_ajena.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_usuario_no_autenticado_no_accede(
        self,
    ):
        self.client.force_authenticate(
            user=None
        )

        respuestas = [
            self.client.get(
                self.url_listado
            ),
            self.client.get(
                (
                    f"/api/mis-deudas/"
                    f"{self.deuda_reciente.id}/"
                )
            ),
            self.client.get(
                (
                    f"/api/mis-deudas/"
                    f"{self.deuda_reciente.id}/"
                    "solicitudes/"
                )
            ),
        ]

        for response in respuestas:
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
            )


class EnviarSolicitudResolucionEvidenciaSC64Test(
    APITestCase
):

    def setUp(self):
        self.media_temporal = TemporaryDirectory()
        self.override_media = override_settings(
            MEDIA_ROOT=self.media_temporal.name
        )
        self.override_media.enable()
        self.addCleanup(
            self.override_media.disable
        )
        self.addCleanup(
            self.media_temporal.cleanup
        )

        self.usuario = User.objects.create_user(
            username="usuario_sc64",
            email="usuario_sc64@example.com",
            password="Prueba123",
        )

        self.otro_usuario = User.objects.create_user(
            username="otro_sc64",
            email="otro_sc64@example.com",
            password="Prueba123",
        )

        self.revisor = User.objects.create_user(
            username="revisor_sc64",
            email="revisor_sc64@example.com",
            password="Prueba123",
        )

        self.momento_base = timezone.now()

        self.deuda = self.crear_deuda(
            usuario=self.usuario,
            nombre_grupo="Actividad pendiente SC-64",
            monto_original=Decimal("50.00"),
            saldo_pendiente=Decimal("35.00"),
            estado=Debt.ESTADO_PENDIENTE,
        )

        self.deuda_resuelta = self.crear_deuda(
            usuario=self.usuario,
            nombre_grupo="Actividad resuelta SC-64",
            monto_original=Decimal("20.00"),
            saldo_pendiente=Decimal("0.00"),
            estado=Debt.ESTADO_RESUELTA,
        )

        self.deuda_en_revision = self.crear_deuda(
            usuario=self.usuario,
            nombre_grupo="Actividad revisión SC-64",
            monto_original=Decimal("18.00"),
            saldo_pendiente=Decimal("18.00"),
            estado=Debt.ESTADO_EN_REVISION,
        )

        self.deuda_ajena = self.crear_deuda(
            usuario=self.otro_usuario,
            nombre_grupo="Actividad ajena SC-64",
            monto_original=Decimal("30.00"),
            saldo_pendiente=Decimal("30.00"),
            estado=Debt.ESTADO_PENDIENTE,
        )

        self.url = (
            f"/api/mis-deudas/{self.deuda.id}/"
            "solicitudes/"
        )

        self.client.force_authenticate(
            user=self.usuario
        )

    def crear_deuda(
        self,
        usuario,
        nombre_grupo,
        monto_original,
        saldo_pendiente,
        estado,
    ):
        grupo = Group.objects.create(
            nombre=nombre_grupo,
            descripcion="Actividad cerrada para solicitudes",
            creador=self.revisor,
            fecha_inicio=(
                self.momento_base
                - timedelta(days=5)
            ),
            fecha_fin=(
                self.momento_base
                - timedelta(days=2)
            ),
            fecha_cierre_automatico=(
                self.momento_base
                - timedelta(days=2)
            ),
            fecha_generacion_saldos=(
                self.momento_base
                - timedelta(days=2)
            ),
        )

        saldo = ClosingBalance.objects.create(
            grupo=grupo,
            grupo_nombre=grupo.nombre,
            participante=usuario,
            participante_username=usuario.username,
            cuota_total=monto_original,
            total_pagado=(
                monto_original - saldo_pendiente
            ),
            saldo_pendiente=saldo_pendiente,
            estado=(
                ClosingBalance.ESTADO_PENDIENTE
                if saldo_pendiente > Decimal("0.00")
                else ClosingBalance.ESTADO_SALDADO
            ),
        )

        return Debt.objects.create(
            grupo=grupo,
            grupo_nombre=grupo.nombre,
            saldo_cierre=saldo,
            participante=usuario,
            participante_username=usuario.username,
            monto_original=monto_original,
            saldo_pendiente=saldo_pendiente,
            estado=estado,
            fecha_resolucion=(
                self.momento_base
                if estado == Debt.ESTADO_RESUELTA
                else None
            ),
        )

    def archivo(
        self,
        nombre="comprobante.pdf",
        contenido=b"%PDF-1.4 evidencia valida",
        content_type="application/pdf",
    ):
        return SimpleUploadedFile(
            nombre,
            contenido,
            content_type=content_type,
        )

    def enviar(
        self,
        descripcion="Adjunto comprobante del pago realizado.",
        evidencia=None,
        url=None,
    ):
        if evidencia is None:
            evidencia = self.archivo()

        return self.client.post(
            url or self.url,
            {
                "descripcion": descripcion,
                "evidencia": evidencia,
            },
            format="multipart",
        )

    def test_usuario_envia_solicitud_sobre_deuda_propia(
        self,
    ):
        response = self.enviar()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        solicitud = DebtResolutionRequest.objects.get()

        self.assertEqual(
            solicitud.deuda,
            self.deuda,
        )

        self.assertEqual(
            solicitud.grupo,
            self.deuda.grupo,
        )

        self.assertEqual(
            solicitud.solicitante,
            self.usuario,
        )

        self.assertEqual(
            response.data["solicitud"]["deuda_id"],
            self.deuda.id,
        )

    def test_deuda_ajena_no_permite_enviar_solicitud(
        self,
    ):
        url_ajena = (
            f"/api/mis-deudas/{self.deuda_ajena.id}/"
            "solicitudes/"
        )

        response = self.enviar(
            url=url_ajena
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

    def test_deuda_debe_estar_pendiente(
        self,
    ):
        for deuda in [
            self.deuda_resuelta,
            self.deuda_en_revision,
        ]:
            response = self.enviar(
                url=(
                    f"/api/mis-deudas/{deuda.id}/"
                    "solicitudes/"
                )
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
            )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

    def test_descripcion_es_obligatoria(
        self,
    ):
        response = self.client.post(
            self.url,
            {
                "evidencia": self.archivo(),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "descripcion",
            response.data,
        )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

    def test_descripcion_vacia_no_se_guarda(
        self,
    ):
        response = self.enviar(
            descripcion="   "
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "descripcion",
            response.data,
        )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

    def test_evidencia_es_obligatoria(
        self,
    ):
        response = self.client.post(
            self.url,
            {
                "descripcion": (
                    "Pago realizado mediante transferencia."
                ),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "evidencia",
            response.data,
        )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

    def test_formato_de_evidencia_debe_ser_admitido(
        self,
    ):
        response = self.enviar(
            evidencia=self.archivo(
                nombre="archivo.exe",
                contenido=b"archivo no permitido",
                content_type=(
                    "application/octet-stream"
                ),
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "evidencia",
            response.data,
        )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

    def test_formatos_pdf_jpg_jpeg_y_png_son_admitidos(
        self,
    ):
        casos = [
            (
                "comprobante.pdf",
                "application/pdf",
            ),
            (
                "captura.jpg",
                "image/jpeg",
            ),
            (
                "captura.jpeg",
                "image/jpeg",
            ),
            (
                "captura.png",
                "image/png",
            ),
        ]

        for indice, (nombre, content_type) in enumerate(
            casos
        ):
            deuda = self.crear_deuda(
                usuario=self.usuario,
                nombre_grupo=(
                    f"Formato permitido {indice} SC-64"
                ),
                monto_original=Decimal("10.00"),
                saldo_pendiente=Decimal("10.00"),
                estado=Debt.ESTADO_PENDIENTE,
            )

            response = self.enviar(
                evidencia=self.archivo(
                    nombre=nombre,
                    contenido=b"contenido evidencia",
                    content_type=content_type,
                ),
                url=(
                    f"/api/mis-deudas/{deuda.id}/"
                    "solicitudes/"
                ),
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
            )

        self.assertEqual(
            DebtResolutionRequest.objects.count(),
            4,
        )

    def test_solicitud_incompleta_no_se_guarda(
        self,
    ):
        respuestas = [
            self.client.post(
                self.url,
                {},
                format="multipart",
            ),
            self.client.post(
                self.url,
                {
                    "descripcion": "",
                    "evidencia": self.archivo(
                        nombre="vacio.png",
                        contenido=b"imagen",
                        content_type="image/png",
                    ),
                },
                format="multipart",
            ),
        ]

        for response in respuestas:
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
            )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

    def test_solicitud_queda_pendiente_de_revision(
        self,
    ):
        response = self.enviar()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        solicitud = DebtResolutionRequest.objects.get()

        self.assertEqual(
            solicitud.estado,
            (
                DebtResolutionRequest
                .ESTADO_PENDIENTE_REVISION
            ),
        )

        self.assertIsNone(
            solicitud.decision
        )

        self.assertIsNone(
            solicitud.revisado_por
        )

        self.assertIsNone(
            solicitud.fecha_revision
        )

        self.assertTrue(
            response.data["solicitud"][
                "pendiente_revision"
            ]
        )

    def test_guarda_usuario_deuda_actividad_y_fecha_exacta(
        self,
    ):
        antes = timezone.now()

        response = self.enviar()

        despues = timezone.now()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        solicitud = DebtResolutionRequest.objects.get()

        self.assertEqual(
            solicitud.solicitante,
            self.usuario,
        )

        self.assertEqual(
            solicitud.solicitante_username,
            "usuario_sc64",
        )

        self.assertEqual(
            solicitud.deuda,
            self.deuda,
        )

        self.assertEqual(
            solicitud.grupo,
            self.deuda.grupo,
        )

        self.assertEqual(
            solicitud.grupo_nombre,
            "Actividad pendiente SC-64",
        )

        self.assertGreaterEqual(
            solicitud.fecha_envio,
            antes,
        )

        self.assertLessEqual(
            solicitud.fecha_envio,
            despues,
        )

        self.assertTrue(
            timezone.is_aware(
                solicitud.fecha_envio
            )
        )

    def test_evidencia_queda_asociada_permanentemente(
        self,
    ):
        response = self.enviar(
            evidencia=self.archivo(
                nombre="pago_transferencia.png",
                contenido=b"imagen del comprobante",
                content_type="image/png",
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        solicitud = DebtResolutionRequest.objects.get()

        self.assertEqual(
            solicitud.evidencia_nombre_original,
            "pago_transferencia.png",
        )

        self.assertTrue(
            solicitud.evidencia.name.startswith(
                (
                    "evidencias_resolucion/"
                    f"grupo_{self.deuda.grupo_id}/"
                    f"deuda_{self.deuda.id}/"
                )
            )
        )

        self.assertTrue(
            solicitud.evidencia.storage.exists(
                solicitud.evidencia.name
            )
        )

        solicitud.refresh_from_db()

        self.assertTrue(
            solicitud.evidencia
        )

    def test_solo_una_solicitud_pendiente_por_deuda(
        self,
    ):
        primera = self.enviar(
            descripcion="Primera solicitud."
        )

        segunda = self.enviar(
            descripcion="Segunda solicitud."
        )

        self.assertEqual(
            primera.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            segunda.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "deuda",
            segunda.data,
        )

        self.assertEqual(
            DebtResolutionRequest.objects.filter(
                deuda=self.deuda
            ).count(),
            1,
        )

    def test_solicitud_se_consulta_inmediatamente(
        self,
    ):
        creacion = self.enviar()

        solicitud_id = creacion.data[
            "solicitud"
        ]["id"]

        listado = self.client.get(
            self.url
        )

        detalle = self.client.get(
            (
                f"/api/mis-deudas/{self.deuda.id}/"
                f"solicitudes/{solicitud_id}/"
            )
        )

        self.assertEqual(
            listado.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            detalle.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            listado.data["total_solicitudes"],
            1,
        )

        self.assertTrue(
            listado.data[
                "tiene_solicitud_pendiente"
            ]
        )

        self.assertEqual(
            detalle.data["solicitud"]["id"],
            solicitud_id,
        )

    def test_envio_no_modifica_automaticamente_deuda(
        self,
    ):
        estado_original = self.deuda.estado
        monto_original = self.deuda.monto_original
        saldo_original = self.deuda.saldo_pendiente

        response = self.enviar()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.deuda.refresh_from_db()

        self.assertEqual(
            self.deuda.estado,
            estado_original,
        )

        self.assertEqual(
            self.deuda.monto_original,
            monto_original,
        )

        self.assertEqual(
            self.deuda.saldo_pendiente,
            saldo_original,
        )

        self.assertIsNone(
            self.deuda.fecha_resolucion
        )

    def test_fallo_de_carga_no_crea_solicitud(
        self,
    ):
        almacenamiento = (
            DebtResolutionRequest
            ._meta.get_field(
                "evidencia"
            )
            .storage
        )

        with patch.object(
            almacenamiento,
            "save",
            side_effect=RuntimeError(
                "Fallo simulado al guardar evidencia"
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.enviar()

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

        self.assertFalse(
            ActivityHistory.objects.filter(
                grupo=self.deuda.grupo,
                tipo_accion=(
                    ActivityHistory
                    .TIPO_SOLICITUD_RESOLUCION_CREADA
                ),
            ).exists()
        )

    def test_fallo_del_historial_revierte_y_elimina_evidencia(
        self,
    ):
        with patch(
            "expenses.models.ActivityHistory.registrar",
            side_effect=RuntimeError(
                "Fallo simulado del historial"
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.enviar(
                    evidencia=self.archivo(
                        nombre="rollback.pdf"
                    )
                )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

        almacenamiento = (
            DebtResolutionRequest
            ._meta.get_field(
                "evidencia"
            )
            .storage
        )

        directorio = (
            "evidencias_resolucion/"
            f"grupo_{self.deuda.grupo_id}/"
            f"deuda_{self.deuda.id}"
        )

        try:
            carpetas, archivos = (
                almacenamiento.listdir(
                    directorio
                )
            )
        except FileNotFoundError:
            carpetas, archivos = [], []

        self.assertEqual(
            carpetas,
            [],
        )

        self.assertEqual(
            archivos,
            [],
        )

    def test_creacion_se_registra_para_trazabilidad(
        self,
    ):
        response = self.enviar(
            descripcion=(
                "Pago realizado desde la cuenta bancaria."
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        solicitud = DebtResolutionRequest.objects.get()

        evento = ActivityHistory.objects.get(
            grupo=self.deuda.grupo,
            tipo_accion=(
                ActivityHistory
                .TIPO_SOLICITUD_RESOLUCION_CREADA
            ),
        )

        self.assertEqual(
            evento.usuario,
            self.usuario,
        )

        self.assertEqual(
            evento.usuario_username,
            "usuario_sc64",
        )

        self.assertEqual(
            evento.datos["solicitud_id"],
            solicitud.id,
        )

        self.assertEqual(
            evento.datos["deuda_id"],
            self.deuda.id,
        )

        self.assertEqual(
            evento.datos["estado"],
            (
                DebtResolutionRequest
                .ESTADO_PENDIENTE_REVISION
            ),
        )

        self.assertEqual(
            evento.datos[
                "evidencia_nombre_original"
            ],
            "comprobante.pdf",
        )

    def test_solicitud_revisada_no_puede_editarse(
        self,
    ):
        creacion = self.enviar(
            descripcion="Descripción original."
        )

        solicitud = DebtResolutionRequest.objects.get(
            id=creacion.data["solicitud"]["id"]
        )

        solicitud.estado = (
            DebtResolutionRequest.ESTADO_APROBADA
        )
        solicitud.decision = (
            DebtResolutionRequest.DECISION_APROBADA
        )
        solicitud.observacion_revision = (
            "Evidencia aceptada."
        )
        solicitud.revisado_por = self.revisor
        solicitud.revisado_por_username = (
            self.revisor.username
        )
        solicitud.fecha_revision = timezone.now()
        solicitud.save()

        url_detalle = (
            f"/api/mis-deudas/{self.deuda.id}/"
            f"solicitudes/{solicitud.id}/"
        )

        response_patch = self.client.patch(
            url_detalle,
            {
                "descripcion": (
                    "Intento de modificación."
                )
            },
            format="json",
        )

        self.assertEqual(
            response_patch.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        solicitud.refresh_from_db()

        self.assertEqual(
            solicitud.descripcion,
            "Descripción original.",
        )

        detalle = self.client.get(
            url_detalle
        )

        self.assertFalse(
            detalle.data["solicitud"][
                "puede_editarse"
            ]
        )

        self.assertEqual(
            detalle.data["solicitud"][
                "observacion_revision"
            ],
            "Evidencia aceptada.",
        )

        self.assertTrue(
            solicitud.evidencia.storage.exists(
                solicitud.evidencia.name
            )
        )

    def test_usuario_no_autenticado_no_puede_enviar(
        self,
    ):
        self.client.force_authenticate(
            user=None
        )

        response = self.enviar()

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertFalse(
            DebtResolutionRequest.objects.exists()
        )

