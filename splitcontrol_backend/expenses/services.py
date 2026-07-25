from decimal import Decimal

from django.db.models import Sum

from .models import ExpenseDivision, Payment


CERO = Decimal("0.00")
DOS_DECIMALES = Decimal("0.01")


def calcular_balances_grupo(grupo):
    valores_asignados = (
        ExpenseDivision.objects
        .filter(gasto__grupo=grupo)
        .values("participante_id")
        .annotate(total=Sum("monto_asignado"))
    )

    pagos_realizados_agrupados = (
        Payment.objects
        .filter(grupo=grupo)
        .values("pagador_id")
        .annotate(total=Sum("monto"))
    )

    pagos_recibidos_agrupados = (
        Payment.objects
        .filter(grupo=grupo)
        .values("receptor_id")
        .annotate(total=Sum("monto"))
    )

    asignado_por_participante = {
        item["participante_id"]: item["total"] or CERO
        for item in valores_asignados
    }

    pagos_realizados_por_participante = {
        item["pagador_id"]: item["total"] or CERO
        for item in pagos_realizados_agrupados
    }

    pagos_recibidos_por_participante = {
        item["receptor_id"]: item["total"] or CERO
        for item in pagos_recibidos_agrupados
    }

    balances = []

    participantes = (
        grupo.participantes
        .all()
        .order_by("id")
    )

    for participante in participantes:
        total_pagado = CERO

        total_correspondiente = asignado_por_participante.get(
            participante.id,
            CERO,
        ).quantize(DOS_DECIMALES)

        pagos_realizados = pagos_realizados_por_participante.get(
            participante.id,
            CERO,
        ).quantize(DOS_DECIMALES)

        pagos_recibidos = pagos_recibidos_por_participante.get(
            participante.id,
            CERO,
        ).quantize(DOS_DECIMALES)

        balance = (
            -total_correspondiente
            + pagos_realizados
            - pagos_recibidos
        ).quantize(DOS_DECIMALES)

        balances.append({
            "participante": participante,
            "total_pagado": total_pagado,
            "total_correspondiente": total_correspondiente,
            "pagos_realizados": pagos_realizados,
            "pagos_recibidos": pagos_recibidos,
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