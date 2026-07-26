from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Sum

from .models import (
    Expense,
    ExpenseDivision,
    GroupMembership,
    Payment,
)


CERO = Decimal("0.00")
DOS_DECIMALES = Decimal("0.01")


def calcular_balances_grupo(grupo):
    valores_asignados = (
        ExpenseDivision.objects
        .filter(gasto__grupo=grupo)
        .values("participante_id")
        .annotate(total=Sum("monto_asignado"))
    )

    aportes_agrupados = (
        Payment.objects
        .filter(grupo=grupo)
        .values("pagador_id")
        .annotate(total=Sum("monto"))
    )

    asignado_por_participante = {
        item["participante_id"]: (
            item["total"] or CERO
        ).quantize(DOS_DECIMALES)
        for item in valores_asignados
    }

    aportado_por_participante = {
        item["pagador_id"]: (
            item["total"] or CERO
        ).quantize(DOS_DECIMALES)
        for item in aportes_agrupados
    }

    participantes_ids = set(
        grupo.participantes.values_list(
            "id",
            flat=True,
        )
    )

    participantes_ids.update(
        asignado_por_participante.keys()
    )

    participantes_ids.update(
        aportado_por_participante.keys()
    )

    participantes = (
        User.objects
        .filter(id__in=participantes_ids)
        .order_by("id")
    )

    balances = []

    for participante in participantes:
        total_correspondiente = (
            asignado_por_participante.get(
                participante.id,
                CERO,
            )
        ).quantize(DOS_DECIMALES)

        total_aportado = (
            aportado_por_participante.get(
                participante.id,
                CERO,
            )
        ).quantize(DOS_DECIMALES)

        balance = (
            total_aportado
            - total_correspondiente
        ).quantize(DOS_DECIMALES)

        balances.append({
            "participante": participante,
            "total_pagado": total_aportado,
            "total_correspondiente": total_correspondiente,
            "pagos_realizados": total_aportado,
            "pagos_recibidos": CERO,
            "balance": balance,
        })

    return balances


def calcular_deudas_grupo(grupo):
    balances = calcular_balances_grupo(grupo)

    acreedores = []
    deudores = []

    for item in balances:
        balance = item["balance"]

        if balance > CERO:
            acreedores.append({
                "participante": item["participante"],
                "saldo": balance,
            })

        elif balance < CERO:
            deudores.append({
                "participante": item["participante"],
                "saldo": abs(balance),
            })

    deudas = []

    indice_deudor = 0
    indice_acreedor = 0

    while (
        indice_deudor < len(deudores)
        and indice_acreedor < len(acreedores)
    ):
        deudor = deudores[indice_deudor]
        acreedor = acreedores[indice_acreedor]

        monto = min(
            deudor["saldo"],
            acreedor["saldo"],
        ).quantize(DOS_DECIMALES)

        if monto > CERO:
            deudas.append({
                "deudor": deudor["participante"],
                "acreedor": acreedor["participante"],
                "monto": monto,
            })

        deudor["saldo"] = (
            deudor["saldo"] - monto
        ).quantize(DOS_DECIMALES)

        acreedor["saldo"] = (
            acreedor["saldo"] - monto
        ).quantize(DOS_DECIMALES)

        if deudor["saldo"] == CERO:
            indice_deudor += 1

        if acreedor["saldo"] == CERO:
            indice_acreedor += 1

    return deudas


def calcular_resumen_economico_grupo(grupo):
    gastos = Expense.objects.filter(
        grupo=grupo
    )

    total_gastos = (
        gastos.aggregate(
            total=Sum("monto")
        )["total"]
        or CERO
    ).quantize(DOS_DECIMALES)

    cantidad_gastos = gastos.count()

    cuotas_agrupadas = (
        ExpenseDivision.objects
        .filter(gasto__grupo=grupo)
        .values("participante_id")
        .annotate(total=Sum("monto_asignado"))
    )

    aportes_agrupados = (
        Payment.objects
        .filter(grupo=grupo)
        .values("pagador_id")
        .annotate(total=Sum("monto"))
    )

    cuota_por_participante = {
        item["participante_id"]: (
            item["total"] or CERO
        ).quantize(DOS_DECIMALES)
        for item in cuotas_agrupadas
    }

    aporte_por_participante = {
        item["pagador_id"]: (
            item["total"] or CERO
        ).quantize(DOS_DECIMALES)
        for item in aportes_agrupados
    }

    participantes_ids = set(
        grupo.participantes.values_list(
            "id",
            flat=True,
        )
    )

    participantes_ids.update(
        cuota_por_participante.keys()
    )

    participantes_ids.update(
        aporte_por_participante.keys()
    )

    participantes_activos_ids = set(
        GroupMembership.objects
        .filter(
            grupo=grupo,
            activo=True,
        )
        .values_list(
            "usuario_id",
            flat=True,
        )
    )

    participantes_activos_ids.update(
        grupo.participantes.values_list(
            "id",
            flat=True,
        )
    )

    participantes = (
        User.objects
        .filter(id__in=participantes_ids)
        .order_by("id")
    )

    cuotas = []
    total_cuotas = CERO
    total_aportado = CERO
    total_pendiente = CERO

    for participante in participantes:
        cuota_total = cuota_por_participante.get(
            participante.id,
            CERO,
        ).quantize(DOS_DECIMALES)

        aporte_total = aporte_por_participante.get(
            participante.id,
            CERO,
        ).quantize(DOS_DECIMALES)

        saldo_pendiente = max(
            cuota_total - aporte_total,
            CERO,
        ).quantize(DOS_DECIMALES)

        total_cuotas += cuota_total
        total_aportado += aporte_total
        total_pendiente += saldo_pendiente

        cuotas.append({
            "participante": participante,
            "activo": (
                participante.id
                in participantes_activos_ids
            ),
            "cuota_total": cuota_total,
            "total_aportado": aporte_total,
            "saldo_pendiente": saldo_pendiente,
            "estado": (
                "saldado"
                if saldo_pendiente == CERO
                else "pendiente"
            ),
        })

    return {
        "total_gastos": total_gastos,
        "cantidad_gastos": cantidad_gastos,
        "total_cuotas": total_cuotas.quantize(
            DOS_DECIMALES
        ),
        "total_aportado": total_aportado.quantize(
            DOS_DECIMALES
        ),
        "total_pendiente": total_pendiente.quantize(
            DOS_DECIMALES
        ),
        "cuotas": cuotas,
    }