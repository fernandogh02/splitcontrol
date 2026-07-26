from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from expenses.models import (
    Expense,
    ExpenseDivision,
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

