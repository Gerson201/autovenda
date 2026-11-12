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
        normalizados, erros = Cliente.validar_dados(dados, cpf_obrigatorio=True)

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
            elif proposta.cliente.email != normalizados["email"]:
                # Sem esta conferência a venda sairia vinculada à proposta de uma
                # pessoa e registrada no nome de outra, e o histórico da loja
                # passaria a dizer duas coisas diferentes sobre o mesmo negócio.
                erros["proposta_id"] = (
                    f"A proposta selecionada é de {proposta.cliente.nome} "
                    f"({proposta.cliente.email}). Para vender a outro comprador, "
                    "recuse essa proposta antes ou corrija os dados do comprador."
                )

        # Um veículo reservado está prometido a quem teve a proposta aceita.
        # Vender para outra pessoa sem recusar a proposta antes é possível na
        # prática, mas não pode acontecer em silêncio: antes, a proposta aceita
        # era rebaixada para RECUSADA sem o vendedor sequer ser avisado.
        if veiculo is not None and veiculo.status == "RESERVADO" and "veiculo_id" not in erros:
            aceita = next((p for p in veiculo.propostas if p.status == "ACEITA"), None)
            if aceita is not None and (proposta is None or aceita.id != proposta.id):
                erros["veiculo_id"] = (
                    f"Este veículo está reservado para {aceita.cliente.nome} "
                    f"({aceita.cliente.email}), que teve a proposta aceita. "
                    "Recuse essa proposta antes de vender para outro comprador."
                )

        if erros:
            raise ErroValidacao(erros)

        cliente = Cliente.obter_ou_criar(dados, cpf_obrigatorio=True, atualizar_cadastro=True)
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
