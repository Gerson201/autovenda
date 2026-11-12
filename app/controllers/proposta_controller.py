from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import STATUS_PROPOSTA, ErroRegraNegocio, Proposta, Veiculo
from ..seguranca import exigir_login

bp = Blueprint("propostas", __name__, url_prefix="/admin/propostas")
bp.before_request(exigir_login)


def _obter(proposta_id):
    proposta = db.session.get(Proposta, proposta_id)
    if proposta is None:
        abort(404)
    return proposta


@bp.get("/")
def lista():
    status = request.args.get("status", "PENDENTE")
    # Cada linha da tabela mostra cliente, veículo e marca: sem o joinedload
    # são três consultas por proposta listada (N+1).
    consulta = Proposta.query.options(
        joinedload(Proposta.cliente),
        joinedload(Proposta.veiculo).joinedload(Veiculo.marca),
    )
    if status in STATUS_PROPOSTA:
        consulta = consulta.filter_by(status=status)
    paginacao = consulta.order_by(Proposta.criado_em.desc()).paginate(
        page=request.args.get("pagina", 1, type=int),
        per_page=current_app.config["ITENS_POR_PAGINA_ADMIN"],
        error_out=False,
    )
    return render_template(
        "propostas/lista.html", paginacao=paginacao, status=status, status_opcoes=STATUS_PROPOSTA
    )


@bp.post("/<int:proposta_id>/aceitar")
def aceitar(proposta_id):
    proposta = _obter(proposta_id)
    try:
        proposta.aceitar()
        db.session.commit()
    except ErroRegraNegocio as erro:
        db.session.rollback()
        flash(str(erro), "erro")
        return redirect(url_for(".lista"))
    flash(
        f"Proposta aceita. O veículo {proposta.veiculo.titulo} foi reservado. "
        "Registre a venda quando o negócio for fechado.",
        "sucesso",
    )
    return redirect(url_for(".lista", status="ACEITA"))


@bp.post("/<int:proposta_id>/recusar")
def recusar(proposta_id):
    proposta = _obter(proposta_id)
    try:
        proposta.recusar()
        db.session.commit()
    except ErroRegraNegocio as erro:
        db.session.rollback()
        flash(str(erro), "erro")
        return redirect(url_for(".lista"))
    flash("Proposta recusada.", "info")
    return redirect(url_for(".lista"))
