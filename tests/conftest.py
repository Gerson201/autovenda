import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Marca, Usuario, Veiculo

SENHA_ADMIN = "Admin@123"
SENHA_VENDEDOR = "Vende@123"

DADOS_VEICULO = {
    "modelo": "Onix",
    "versao": "1.0 LT",
    "ano_fabricacao": "2021",
    "ano_modelo": "2022",
    "cor": "Prata",
    "quilometragem": "35000",
    "combustivel": "FLEX",
    "cambio": "MANUAL",
    "preco": "72900.00",
    "placa": "ABC1D23",
    "descricao": "Único dono.",
}

DADOS_CLIENTE = {
    "nome": "Maria Souza",
    "email": "maria@exemplo.com",
    "telefone": "(11) 98765-4321",
}

CPF_VALIDO = "529.982.247-25"
OUTRO_CPF_VALIDO = "111.444.777-35"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(app):
    usuario = Usuario.criar("Ana Admin", "admin@teste.com", SENHA_ADMIN, "ADMIN")
    db.session.commit()
    return usuario


@pytest.fixture
def vendedor(app):
    usuario = Usuario.criar("Victor Vendedor", "vendedor@teste.com", SENHA_VENDEDOR, "VENDEDOR")
    db.session.commit()
    return usuario


@pytest.fixture
def marca(app):
    m = Marca.criar("Chevrolet")
    db.session.commit()
    return m


@pytest.fixture
def criar_veiculo(marca):
    def _criar(**alteracoes):
        dados = {**DADOS_VEICULO, "marca_id": marca.id, **alteracoes}
        veiculo = Veiculo()
        veiculo.preencher(dados)
        db.session.add(veiculo)
        db.session.commit()
        return veiculo

    return _criar


@pytest.fixture
def veiculo(criar_veiculo):
    return criar_veiculo()


def fazer_login(client, email, senha):
    return client.post("/login", data={"email": email, "senha": senha})


@pytest.fixture
def client_admin(client, admin):
    fazer_login(client, admin.email, SENHA_ADMIN)
    return client


@pytest.fixture
def client_vendedor(client, vendedor):
    fazer_login(client, vendedor.email, SENHA_VENDEDOR)
    return client
