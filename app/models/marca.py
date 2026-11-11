from ..extensions import db
from .erros import ErroRegraNegocio, ErroValidacao
from .util import texto


class Marca(db.Model):
    """Fabricante do veículo (Chevrolet, Fiat, Toyota...)."""

    __tablename__ = "marca"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)

    veiculos = db.relationship("Veiculo", back_populates="marca")

    @classmethod
    def listar(cls):
        return cls.query.order_by(db.func.lower(cls.nome)).all()

    @classmethod
    def criar(cls, nome):
        nome = texto(nome)
        if not nome:
            raise ErroValidacao({"nome": "Informe o nome da marca."})
        if len(nome) > 50:
            raise ErroValidacao({"nome": "O nome da marca deve ter no máximo 50 caracteres."})
        if cls.query.filter(db.func.lower(cls.nome) == nome.lower()).first():
            raise ErroValidacao({"nome": f'A marca "{nome}" já está cadastrada.'})
        marca = cls(nome=nome)
        db.session.add(marca)
        return marca

    def excluir(self):
        if self.veiculos:
            raise ErroRegraNegocio(
                f'A marca "{self.nome}" possui veículos cadastrados e não pode ser excluída.'
            )
        db.session.delete(self)
