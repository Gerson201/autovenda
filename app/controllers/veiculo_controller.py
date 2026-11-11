from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    CAMBIOS,
    COMBUSTIVEIS,
    STATUS_VEICULO,
    ErroRegraNegocio,
    ErroValidacao,
    Marca,
    Veiculo,
)
from ..seguranca import exigir_login, somente_admin
from ..servicos.armazenamento import remover_imagem, salvar_imagem, validar_imagem

bp = Blueprint("veiculos", __name__, url_prefix="/admin/veiculos")
bp.before_request(exigir_login)


def _obter(veiculo_id):
    veiculo = db.session.get(Veiculo, veiculo_id)
    if veiculo is None:
        abort(404)
    return veiculo


def _formulario(veiculo, dados, erros, status=200):
    return (
        render_template(
            "veiculos/form.html",
            veiculo=veiculo,
            dados=dados,
            erros=erros,
            marcas=Marca.listar(),
            combustiveis=COMBUSTIVEIS,
            cambios=CAMBIOS,
        ),
        status,
    )


def _salvar(veiculo, mensagem_sucesso):
    """Fluxo comum de cadastro/edição: valida tudo, grava a foto e faz o commit."""
    erros = {}
    try:
        veiculo.preencher(request.form)
    except ErroValidacao as erro:
        erros.update(erro.erros)

    arquivo = request.files.get("imagem")
    tem_arquivo = arquivo is not None and arquivo.filename
    if tem_arquivo:
        erro_imagem = validar_imagem(arquivo)
        if erro_imagem:
            erros["imagem"] = erro_imagem

    if erros:
        db.session.rollback()
        flash("Não foi possível salvar o veículo. Corrija os campos destacados.", "erro")
        return _formulario(veiculo if veiculo.id else None, request.form, erros, 422)

    imagem_antiga = veiculo.imagem
    imagem_nova = salvar_imagem(arquivo) if tem_arquivo else None
    if imagem_nova:
        veiculo.imagem = imagem_nova

    try:
        db.session.add(veiculo)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        remover_imagem(imagem_nova)
        current_app.logger.exception("Falha de integridade ao salvar veículo")
        flash("Não foi possível salvar: os dados conflitam com outro registro (ex.: placa).", "erro")
        return _formulario(veiculo if veiculo.id else None, request.form, {}, 409)

    if imagem_nova and imagem_antiga:
        remover_imagem(imagem_antiga)
    flash(mensagem_sucesso, "sucesso")
    return redirect(url_for(".lista"))


@bp.get("/")
def lista():
    status = request.args.get("status", "")
    termo = request.args.get("q", "").strip()
    paginacao = Veiculo.buscar_admin(status, termo).paginate(
        page=request.args.get("pagina", 1, type=int),
        per_page=current_app.config["ITENS_POR_PAGINA_ADMIN"],
        error_out=False,
    )
    return render_template(
        "veiculos/lista.html",
        paginacao=paginacao,
        status=status,
        termo=termo,
        status_opcoes=STATUS_VEICULO,
    )


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    if not Marca.query.first():
        flash("Cadastre ao menos uma marca antes de cadastrar veículos.", "aviso")
        return redirect(url_for("marcas.lista"))
    if request.method == "POST":
        return _salvar(Veiculo(), "Veículo cadastrado com sucesso.")
    return _formulario(None, {}, {})


@bp.route("/<int:veiculo_id>/editar", methods=["GET", "POST"])
def editar(veiculo_id):
    veiculo = _obter(veiculo_id)
    if veiculo.status == "VENDIDO":
        flash("Veículos vendidos não podem ser alterados.", "aviso")
        return redirect(url_for(".lista"))
    if request.method == "POST":
        return _salvar(veiculo, "Veículo atualizado com sucesso.")
    return _formulario(veiculo, veiculo.como_formulario(), {})


@bp.post("/<int:veiculo_id>/excluir")
@somente_admin
def excluir(veiculo_id):
    veiculo = _obter(veiculo_id)
    imagem = veiculo.imagem
    try:
        veiculo.excluir()
        db.session.commit()
    except ErroRegraNegocio as erro:
        db.session.rollback()
        flash(str(erro), "erro")
        return redirect(url_for(".lista"))
    remover_imagem(imagem)
    flash("Veículo excluído.", "sucesso")
    return redirect(url_for(".lista"))
