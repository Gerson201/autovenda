from flask import Blueprint, render_template
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Proposta, Veiculo, Venda
from ..seguranca import exigir_login

bp = Blueprint("painel", __name__, url_prefix="/admin")
bp.before_request(exigir_login)


@bp.get("/")
def index():
    contagem = dict(
        db.session.query(Veiculo.status, db.func.count(Veiculo.id)).group_by(Veiculo.status).all()
    )
    resumo = {
        "disponiveis": contagem.get("DISPONIVEL", 0),
        "reservados": contagem.get("RESERVADO", 0),
        "vendidos": contagem.get("VENDIDO", 0),
        "propostas_pendentes": Proposta.query.filter_by(status="PENDENTE").count(),
        "faturamento": Venda.faturamento_total(),
    }
    ultimas_propostas = (
        Proposta.query.options(
            joinedload(Proposta.cliente),
            joinedload(Proposta.veiculo).joinedload(Veiculo.marca),
        )
        .filter_by(status="PENDENTE")
        .order_by(Proposta.criado_em.desc())
        .limit(5)
        .all()
    )
    ultimas_vendas = (
        Venda.query.options(
            joinedload(Venda.veiculo).joinedload(Veiculo.marca),
            joinedload(Venda.vendedor),
        )
        .order_by(Venda.data_venda.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "painel/index.html",
        resumo=resumo,
        ultimas_propostas=ultimas_propostas,
        ultimas_vendas=ultimas_vendas,
    )
