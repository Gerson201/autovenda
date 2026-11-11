from ..extensions import db
from .erros import ErroValidacao
from .util import EMAIL_RE, agora, somente_digitos, texto, validar_cpf


class Cliente(db.Model):
    """Pessoa interessada em comprar um veículo. Identificada pelo e-mail."""

    __tablename__ = "cliente"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    telefone = db.Column(db.String(11), nullable=False)
    cpf = db.Column(db.String(11), unique=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora)

    propostas = db.relationship("Proposta", back_populates="cliente")
    compras = db.relationship("Venda", back_populates="cliente")

    @classmethod
    def validar_dados(cls, dados, cpf_obrigatorio=False):
        """Retorna (dados_normalizados, erros) sem gravar nada."""
        nome = texto(dados.get("nome"))
        email = texto(dados.get("email")).lower()
        telefone = somente_digitos(dados.get("telefone"))
        cpf = somente_digitos(dados.get("cpf")) or None
        erros = {}

        if len(nome) < 3:
            erros["nome"] = "Informe seu nome completo (mínimo 3 caracteres)."
        elif len(nome) > 100:
            erros["nome"] = "O nome deve ter no máximo 100 caracteres."

        if not EMAIL_RE.match(email) or len(email) > 120:
            erros["email"] = "Informe um e-mail válido (ex.: nome@dominio.com)."

        if len(telefone) not in (10, 11):
            erros["telefone"] = "Informe o telefone com DDD (ex.: (11) 91234-5678)."

        if cpf is None:
            if cpf_obrigatorio:
                erros["cpf"] = "Informe o CPF do comprador."
        elif not validar_cpf(cpf):
            erros["cpf"] = "CPF inválido. Confira os números digitados."

        if cpf and "cpf" not in erros and "email" not in erros:
            outro = cls.query.filter_by(cpf=cpf).first()
            if outro and outro.email != email:
                erros["cpf"] = "Este CPF já está cadastrado para outro cliente."
            mesmo_email = cls.query.filter_by(email=email).first()
            if mesmo_email and mesmo_email.cpf and mesmo_email.cpf != cpf:
                erros["email"] = "Este e-mail já está vinculado a outro CPF."

        normalizados = {"nome": nome, "email": email, "telefone": telefone, "cpf": cpf}
        return normalizados, erros

    @classmethod
    def obter_ou_criar(cls, dados, cpf_obrigatorio=False):
        normalizados, erros = cls.validar_dados(dados, cpf_obrigatorio)
        if erros:
            raise ErroValidacao(erros)

        cliente = cls.query.filter_by(email=normalizados["email"]).first()
        if cliente is None:
            cliente = cls(email=normalizados["email"])
            db.session.add(cliente)
        cliente.nome = normalizados["nome"]
        cliente.telefone = normalizados["telefone"]
        if normalizados["cpf"]:
            cliente.cpf = normalizados["cpf"]
        return cliente

    @property
    def telefone_formatado(self):
        t = self.telefone or ""
        if len(t) == 11:
            return f"({t[:2]}) {t[2:7]}-{t[7:]}"
        if len(t) == 10:
            return f"({t[:2]}) {t[2:6]}-{t[6:]}"
        return t

    @property
    def cpf_formatado(self):
        c = self.cpf or ""
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if len(c) == 11 else c
