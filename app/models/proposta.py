from ..extensions import db
from .cliente import Cliente
from .erros import ErroRegraNegocio, ErroValidacao
from .util import PRECO_MAXIMO, agora, converter_decimal, texto

STATUS_PROPOSTA = {"PENDENTE": "Pendente", "ACEITA": "Aceita", "RECUSADA": "Recusada"}


class Proposta(db.Model):
    """Oferta de compra enviada por um cliente pela vitrine."""

    __tablename__ = "proposta"
    __table_args__ = (
        db.CheckConstraint("valor_ofertado > 0", name="ck_proposta_valor"),
        db.CheckConstraint(
            "status IN ('PENDENTE','ACEITA','RECUSADA')", name="ck_proposta_status"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(
        db.Integer, db.ForeignKey("veiculo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False, index=True)
    valor_ofertado = db.Column(db.Numeric(12, 2), nullable=False)
    mensagem = db.Column(db.String(500))
    status = db.Column(db.String(10), nullable=False, default="PENDENTE", index=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora)

    veiculo = db.relationship("Veiculo", back_populates="propostas")
    cliente = db.relationship("Cliente", back_populates="propostas")

    @property
    def status_rotulo(self):
        return STATUS_PROPOSTA.get(self.status, self.status)

    @classmethod
    def criar(cls, veiculo, dados):
        if veiculo.status == "VENDIDO":
            raise ErroRegraNegocio("Este veículo já foi vendido e não recebe novas propostas.")

        _, erros = Cliente.validar_dados(dados)

        valor = converter_decimal(dados.get("valor_ofertado"))
        if valor is None or valor <= 0 or valor > PRECO_MAXIMO:
            erros["valor_ofertado"] = "Informe um valor de proposta maior que zero."

        mensagem = texto(dados.get("mensagem"))
        if len(mensagem) > 500:
            erros["mensagem"] = "A mensagem deve ter no máximo 500 caracteres."

        if erros:
            raise ErroValidacao(erros)

        cliente = Cliente.obter_ou_criar(dados)
        # Uma proposta em análise por vez, por pessoa e por veículo. Sem isso o
        # formulário público aceita envios ilimitados: a fila do vendedor enche
        # de duplicatas e um robô consegue inundar a tabela de propostas.
        if cliente.id is not None:
            pendente = cls.query.filter_by(
                veiculo_id=veiculo.id, cliente_id=cliente.id, status="PENDENTE"
            ).first()
            if pendente is not None:
                raise ErroRegraNegocio(
                    "Você já tem uma proposta em análise para este veículo. "
                    "Aguarde o contato do vendedor antes de enviar outra."
                )
        proposta = cls(
            veiculo=veiculo, cliente=cliente, valor_ofertado=valor, mensagem=mensagem or None
        )
        db.session.add(proposta)
        return proposta

    def aceitar(self):
        if self.status != "PENDENTE":
            raise ErroRegraNegocio("Apenas propostas pendentes podem ser aceitas.")
        if self.veiculo.status == "VENDIDO":
            raise ErroRegraNegocio("Este veículo já foi vendido.")
        outra = Proposta.query.filter(
            Proposta.veiculo_id == self.veiculo_id,
            Proposta.status == "ACEITA",
            Proposta.id != self.id,
        ).first()
        if outra:
            raise ErroRegraNegocio(
                "Já existe uma proposta aceita para este veículo. Recuse-a antes de aceitar outra."
            )
        self.status = "ACEITA"
        self.veiculo.status = "RESERVADO"

    def recusar(self):
        if self.status == "RECUSADA":
            raise ErroRegraNegocio("Esta proposta já foi recusada.")
        if self.veiculo.status == "VENDIDO":
            raise ErroRegraNegocio("O veículo já foi vendido; a proposta não pode mais ser alterada.")
        era_aceita = self.status == "ACEITA"
        self.status = "RECUSADA"
        if era_aceita and self.veiculo.status == "RESERVADO":
            self.veiculo.status = "DISPONIVEL"
