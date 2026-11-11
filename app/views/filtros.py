"""Filtros Jinja usados pelos templates para formatar dados no padrão brasileiro."""

from decimal import Decimal

from flask import url_for


def moeda(valor):
    if valor is None:
        return "—"
    numero = f"{Decimal(valor):,.2f}"
    return "R$ " + numero.replace(",", "X").replace(".", ",").replace("X", ".")


def milhar(valor):
    if valor is None:
        return "—"
    return f"{int(valor):,}".replace(",", ".")


def data_hora(valor):
    return valor.strftime("%d/%m/%Y %H:%M") if valor else "—"


def data(valor):
    return valor.strftime("%d/%m/%Y") if valor else "—"


def imagem_veiculo(veiculo):
    if veiculo.imagem:
        return url_for("static", filename=f"uploads/{veiculo.imagem}")
    return url_for("static", filename="img/sem-foto.svg")


def registrar(app):
    app.add_template_filter(moeda, "moeda")
    app.add_template_filter(milhar, "milhar")
    app.add_template_filter(data_hora, "data_hora")
    app.add_template_filter(data, "data")
    app.add_template_global(imagem_veiculo, "imagem_veiculo")
