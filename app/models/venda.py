from ..extensions import db
from .cliente import Cliente
from .erros import ErroValidacao
from .proposta import Proposta
from .util import PRECO_MAXIMO, agora, converter_decimal, converter_inteiro, texto
from .veiculo import Veiculo

FORMAS_PAGAMENTO = {
    "A_VISTA": "À vista",
    "FINANCIAMENTO": "Financiamento",
    "CONSORCIO": "Consórcio",
}


class Venda(db.Model):
    """Fechamento do negócio: um veículo só pode ser vendido uma vez."""

    __tablename__ = "venda"
    __table_args__ = (
        db.CheckConstraint("valor_final > 0", name="ck_venda_valor"),
        db.CheckConstraint(
            "forma_pagamento IN ('A_VISTA','FINANCIAMENTO','CONSORCIO')",
            name="ck_venda_forma_pagamento",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(db.Integer, db.ForeignKey("veiculo.id"), nullable=False, unique=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False, index=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False, index=True)
    proposta_id = db.Column(db.Integer, db.ForeignKey("proposta.id"), unique=True)
    valor_final = db.Column(db.Numeric(12, 2), nullable=False)
    forma_pagamento = db.Column(db.String(15), nullable=False)
    data_venda = db.Column(db.DateTime, nullable=False, default=agora)

    veiculo = db.relationship("Veiculo", back_populates="venda")
    cliente = db.relationship("Cliente", back_populates="compras")
    vendedor = db.relationship("Usuario", back_populates="vendas")
    proposta = db.relationship("Proposta")

    @property
    def forma_pagamento_rotulo(self):
        return FORMAS_PAGAMENTO.get(self.forma_pagamento, self.forma_pagamento)

    @classmethod
    def registrar(cls, dados, vendedor):
        _, erros = Cliente.validar_dados(dados, cpf_obrigatorio=True)

        veiculo_id = converter_inteiro(dados.get("veiculo_id"))
        veiculo = db.session.get(Veiculo, veiculo_id) if veiculo_id else None
        if veiculo is None:
            erros["veiculo_id"] = "Selecione o veículo vendido."
        elif veiculo.status == "VENDIDO":
            erros["veiculo_id"] = "Este veículo já foi vendido."

        valor = converter_decimal(dados.get("valor_final"))
        if valor is None or valor <= 0 or valor > PRECO_MAXIMO:
            erros["valor_final"] = "Informe o valor final da venda (maior que zero)."

        forma = texto(dados.get("forma_pagamento")).upper()
        if forma not in FORMAS_PAGAMENTO:
            erros["forma_pagamento"] = "Selecione a forma de pagamento."

        proposta = None
        proposta_id = converter_inteiro(dados.get("proposta_id"))
        if proposta_id:
            proposta = db.session.get(Proposta, proposta_id)
            if (
                proposta is None
                or proposta.status == "RECUSADA"
                or (veiculo is not None and proposta.veiculo_id != veiculo.id)
            ):
                erros["proposta_id"] = "A proposta informada não é válida para este veículo."

        if erros:
            raise ErroValidacao(erros)

        cliente = Cliente.obter_ou_criar(dados, cpf_obrigatorio=True)
        venda = cls(
            veiculo=veiculo,
            cliente=cliente,
            vendedor=vendedor,
            proposta=proposta,
            valor_final=valor,
            forma_pagamento=forma,
        )
        db.session.add(venda)
        veiculo.status = "VENDIDO"
        for outra in veiculo.propostas:
            if outra is proposta:
                outra.status = "ACEITA"
            elif outra.status != "RECUSADA":
                outra.status = "RECUSADA"
        return venda

    @classmethod
    def faturamento_total(cls):
        return db.session.query(db.func.coalesce(db.func.sum(cls.valor_final), 0)).scalar()
