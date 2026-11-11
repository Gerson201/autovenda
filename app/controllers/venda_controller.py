from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..models import FORMAS_PAGAMENTO, ErroValidacao, Proposta, Veiculo, Venda
from ..seguranca import exigir_login

bp = Blueprint("vendas", __name__, url_prefix="/admin/vendas")
bp.before_request(exigir_login)


def _formulario(dados, erros, status=200):
    veiculos = (
        Veiculo.query.filter(Veiculo.status != "VENDIDO").order_by(Veiculo.modelo).all()
    )
    return (
        render_template(
            "vendas/form.html",
            dados=dados,
            erros=erros,
            veiculos=veiculos,
            formas_pagamento=FORMAS_PAGAMENTO,
        ),
        status,
    )


@bp.get("/")
def lista():
    paginacao = Venda.query.order_by(Venda.data_venda.desc()).paginate(
        page=request.args.get("pagina", 1, type=int),
        per_page=current_app.config["ITENS_POR_PAGINA_ADMIN"],
        error_out=False,
    )
    return render_template(
        "vendas/lista.html", paginacao=paginacao, faturamento=Venda.faturamento_total()
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    if request.method == "POST":
        try:
            venda = Venda.registrar(request.form, g.usuario)
            db.session.commit()
        except ErroValidacao as erro:
            db.session.rollback()
            flash("Não foi possível registrar a venda. Corrija os campos destacados.", "erro")
            return _formulario(request.form, erro.erros, 422)
        flash(f"Venda do veículo {venda.veiculo.titulo} registrada com sucesso.", "sucesso")
        return redirect(url_for(".lista"))

    dados = {"veiculo_id": request.args.get("veiculo_id", "")}
    proposta_id = request.args.get("proposta_id", type=int)
    proposta = db.session.get(Proposta, proposta_id) if proposta_id else None
    if proposta is not None and proposta.status != "RECUSADA":
        dados.update(
            {
                "veiculo_id": proposta.veiculo_id,
                "proposta_id": proposta.id,
                "nome": proposta.cliente.nome,
                "email": proposta.cliente.email,
                "telefone": proposta.cliente.telefone,
                "cpf": proposta.cliente.cpf or "",
                "valor_final": f"{proposta.valor_ofertado:.2f}",
            }
        )
    return _formulario(dados, {})
