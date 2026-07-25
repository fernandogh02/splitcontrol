from django.db import migrations


def migrar_participantes_a_membresias(apps, schema_editor):
    Group = apps.get_model(
        "expenses",
        "Group",
    )

    GroupMembership = apps.get_model(
        "expenses",
        "GroupMembership",
    )

    for grupo in Group.objects.all():
        participantes_ids = set(
            grupo.participantes.values_list(
                "id",
                flat=True,
            )
        )

        participantes_ids.add(
            grupo.creador_id
        )

        for usuario_id in participantes_ids:
            GroupMembership.objects.get_or_create(
                grupo_id=grupo.id,
                usuario_id=usuario_id,
                activo=True,
                defaults={
                    "fecha_ingreso": grupo.fecha_creacion,
                    "fecha_salida": None,
                },
            )


def revertir_membresias(apps, schema_editor):
    GroupMembership = apps.get_model(
        "expenses",
        "GroupMembership",
    )

    GroupMembership.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "expenses",
            "0007_groupmembership",
        ),
    ]

    operations = [
        migrations.RunPython(
            migrar_participantes_a_membresias,
            revertir_membresias,
        ),
    ]