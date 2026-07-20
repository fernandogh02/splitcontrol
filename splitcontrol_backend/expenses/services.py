from decimal import Decimal

from django.db.models import Sum

from .models import Expense, ExpenseDivision


CERO = Decimal("0.00")


def calcular_balances_grupo(grupo):
    pagos_agrupados = (
        Expense.objects
        .filter(grupo=grupo)
        .values("pagado_por_id")
        .annotate(total=Sum("monto"))
    )

    valores_asignados = (
        ExpenseDivision.objects
        .filter(gasto__grupo=grupo)
        .values("participante_id")
        .annotate(total=Sum("monto_asignado"))
    )

    pagos_por_participante = {
        item["pagado_por_id"]: item["total"] or CERO
        for item in pagos_agrupados
    }

    asignado_por_participante = {
        item["participante_id"]: item["total"] or CERO
        for item in valores_asignados
    }

    balances = []

    participantes = (
        grupo.participantes
        .all()
        .order_by("id")
    )

    for participante in participantes:
        total_pagado = pagos_por_participante.get(
            participante.id,
            CERO,
        )

        total_correspondiente = asignado_por_participante.get(
            participante.id,
            CERO,
        )

        balance = (
            total_pagado - total_correspondiente
        ).quantize(Decimal("0.01"))

        balances.append({
            "participante": participante,
            "total_pagado": total_pagado,
            "total_correspondiente": total_correspondiente,
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
        ).quantize(Decimal("0.01"))

        if monto > CERO:
            deudas.append({
                "deudor": deudor["participante"],
                "acreedor": acreedor["participante"],
                "monto": monto,
            })

        deudor["saldo"] = (
            deudor["saldo"] - monto
        ).quantize(Decimal("0.01"))

        acreedor["saldo"] = (
            acreedor["saldo"] - monto
        ).quantize(Decimal("0.01"))

        if deudor["saldo"] == CERO:
            indice_deudor += 1

        if acreedor["saldo"] == CERO:
            indice_acreedor += 1

    return deudas