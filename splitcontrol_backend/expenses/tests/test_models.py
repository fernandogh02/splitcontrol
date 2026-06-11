from django.test import TestCase


class PruebaInicialBackendTest(TestCase):

    def test_prueba_inicial(self):
        self.assertEqual(1 + 1, 2)