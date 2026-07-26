from django.core.management.base import BaseCommand
from django.utils import timezone

from expenses.models import Group


class Command(BaseCommand):
    help = (
        "Cierra automáticamente las actividades cuya "
        "fecha de finalización ya fue alcanzada."
    )

    def handle(self, *args, **options):
        momento = timezone.now()

        cantidad_cerrada = (
            Group.cerrar_actividades_vencidas(
                momento=momento
            )
        )

        if cantidad_cerrada == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No existen actividades pendientes de cierre."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"{cantidad_cerrada} actividad(es) "
                    "cerrada(s) automáticamente."
                )
            )
        )