from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..extensions import db
from ..models import ErroRegraNegocio, ErroValidacao, Marca, Veiculo
from ..seguranca import exigir_login, somente_admin

bp = Blueprint("marcas", __name__, url_prefix="/admin/marcas")
bp.before_request(exigir_login)


def _render_lista(dados=None, erros=None, status=200):
    totais = dict(
        db.session.query(Veiculo.marca_id, db.func.count(Veiculo.id)).group_by(Veiculo.marca_id).all()
    )
    return (
        render_template(
            "marcas/lista.html",
            marcas=Marca.listar(),
            totais=totais,
            dados=dados or {},
            erros=erros or {},
        ),
        status,
    )


@bp.get("/")
def lista():
    return _render_lista()


@bp.post("/")
@somente_admin
def criar():
    try:
        marca = Marca.criar(request.form.get("nome"))
        db.session.commit()
    except ErroValidacao as erro:
        db.session.rollback()
        return _render_lista(request.form, erro.erros, 422)
    flash(f'Marca "{marca.nome}" cadastrada.', "sucesso")
    return redirect(url_for(".lista"))


@bp.post("/<int:marca_id>/excluir")
@somente_admin
def excluir(marca_id):
    marca = db.session.get(Marca, marca_id)
    if marca is None:
        abort(404)
    try:
        marca.excluir()
        db.session.commit()
    except ErroRegraNegocio as erro:
        db.session.rollback()
        flash(str(erro), "erro")
        return redirect(url_for(".lista"))
    flash("Marca excluída.", "sucesso")
    return redirect(url_for(".lista"))
