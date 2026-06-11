from django.test import TestCase


def dividir_gasto(monto_total, numero_participantes):
    if numero_participantes <= 0:
        raise ValueError("El número de participantes debe ser mayor a cero")
    return monto_total / numero_participantes


class CalculoGastosTest(TestCase):

    def test_dividir_gasto_entre_participantes(self):
        resultado = dividir_gasto(60, 3)
        self.assertEqual(resultado, 20)

    def test_no_permitir_cero_participantes(self):
        with self.assertRaises(ValueError):
            dividir_gasto(60, 0)