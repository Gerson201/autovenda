from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .erros import ErroValidacao
from .util import EMAIL_RE, agora, texto

PERFIS = {"ADMIN": "Administrador", "VENDEDOR": "Vendedor"}
TAMANHO_MINIMO_SENHA = 8


class Usuario(db.Model):
    """Funcionário da loja que acessa o painel administrativo."""

    __tablename__ = "usuario"
    __table_args__ = (
        db.CheckConstraint("perfil IN ('ADMIN','VENDEDOR')", name="ck_usuario_perfil"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(10), nullable=False, default="VENDEDOR")
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora)

    vendas = db.relationship("Venda", back_populates="vendedor")

    @property
    def eh_admin(self):
        return self.perfil == "ADMIN"

    @property
    def perfil_rotulo(self):
        return PERFIS.get(self.perfil, self.perfil)

    @classmethod
    def criar(cls, nome, email, senha, perfil="VENDEDOR"):
        nome = texto(nome)
        email = texto(email).lower()
        erros = {}
        if len(nome) < 3:
            erros["nome"] = "Informe o nome com pelo menos 3 caracteres."
        if not EMAIL_RE.match(email):
            erros["email"] = "Informe um e-mail válido."
        elif cls.query.filter_by(email=email).first():
            erros["email"] = "Já existe um usuário com este e-mail."
        if perfil not in PERFIS:
            erros["perfil"] = "Perfil inválido."
        if len(senha or "") < TAMANHO_MINIMO_SENHA:
            erros["senha"] = f"A senha deve ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres."
        if erros:
            raise ErroValidacao(erros)

        usuario = cls(nome=nome, email=email, perfil=perfil)
        usuario.senha_hash = generate_password_hash(senha)
        db.session.add(usuario)
        return usuario

    @classmethod
    def autenticar(cls, email, senha):
        usuario = cls.query.filter_by(email=texto(email).lower()).first()
        if usuario and usuario.ativo and check_password_hash(usuario.senha_hash, senha or ""):
            return usuario
        return None
