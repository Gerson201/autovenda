from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from ..extensions import db
from ..models import (
    CAMBIOS,
    COMBUSTIVEIS,
    ORDENACOES,
    ErroRegraNegocio,
    ErroValidacao,
    Marca,
    Proposta,
    Veiculo,
)

bp = Blueprint("catalogo", __name__)

CAMPOS_FILTRO = (
    "q",
    "marca",
    "preco_min",
    "preco_max",
    "ano_min",
    "ano_max",
    "combustivel",
    "cambio",
    "ordem",
)

# Quando uma faixa vem invertida, ela é descartada e o visitante recebe a
# explicação no campo, em vez de uma lista vazia sem motivo aparente.
CAMPOS_IGNORADOS_POR_ERRO = {
    "preco_max": ("preco_min", "preco_max"),
    "ano_max": ("ano_min", "ano_max"),
}


def _veiculo_publico(veiculo_id):
    veiculo = db.session.get(Veiculo, veiculo_id)
    if veiculo is None or veiculo.status == "VENDIDO":
        abort(404)
    return veiculo


@bp.get("/")
def index():
    filtros = {campo: request.args.get(campo, "").strip() for campo in CAMPOS_FILTRO}

    erros_filtro = Veiculo.validar_faixas(filtros)
    filtros_consulta = dict(filtros)
    for campo in erros_filtro:
        for ignorado in CAMPOS_IGNORADOS_POR_ERRO.get(campo, ()):
            filtros_consulta[ignorado] = ""

    pagina = request.args.get("pagina", 1, type=int)
    paginacao = Veiculo.buscar_catalogo(filtros_consulta).paginate(
        page=pagina,
        per_page=current_app.config["ITENS_POR_PAGINA_CATALOGO"],
        error_out=False,
    )
    return render_template(
        "catalogo/index.html",
        paginacao=paginacao,
        filtros=filtros,
        erros_filtro=erros_filtro,
        filtros_ativos=any(v for k, v in filtros.items() if k != "ordem"),
        marcas=Marca.listar(),
        combustiveis=COMBUSTIVEIS,
        cambios=CAMBIOS,
        ordenacoes=ORDENACOES,
    )


@bp.get("/veiculos/<int:veiculo_id>")
def detalhe(veiculo_id):
    veiculo = _veiculo_publico(veiculo_id)
    return render_template("catalogo/detalhe.html", veiculo=veiculo, dados={}, erros={})


@bp.post("/veiculos/<int:veiculo_id>/propostas")
def enviar_proposta(veiculo_id):
    veiculo = _veiculo_publico(veiculo_id)
    try:
        Proposta.criar(veiculo, request.form)
        db.session.commit()
    except ErroValidacao as erro:
        db.session.rollback()
        flash("Não foi possível enviar a proposta. Corrija os campos destacados.", "erro")
        return (
            render_template(
                "catalogo/detalhe.html", veiculo=veiculo, dados=request.form, erros=erro.erros
            ),
            422,
        )
    except ErroRegraNegocio as erro:
        db.session.rollback()
        flash(str(erro), "erro")
        return redirect(url_for(".detalhe", veiculo_id=veiculo_id))

    flash("Proposta enviada com sucesso! Um vendedor entrará em contato em breve.", "sucesso")
    return redirect(url_for(".detalhe", veiculo_id=veiculo_id))
