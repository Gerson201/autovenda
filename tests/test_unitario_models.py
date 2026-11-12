"""Testes unitários das regras de negócio da camada Model."""

from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import (
    Cliente,
    ErroRegraNegocio,
    ErroValidacao,
    Marca,
    Proposta,
    Usuario,
    Veiculo,
    Venda,
)

from .conftest import CPF_VALIDO, DADOS_CLIENTE, DADOS_VEICULO, OUTRO_CPF_VALIDO


# ---------------- Usuário ----------------

def test_usuario_senha_e_armazenada_com_hash(admin):
    assert admin.senha_hash != "Admin@123"
    assert Usuario.autenticar("ADMIN@teste.com", "Admin@123") == admin


def test_usuario_autenticacao_falha_com_senha_errada(admin):
    assert Usuario.autenticar(admin.email, "errada123") is None


def test_usuario_inativo_nao_autentica(admin):
    admin.ativo = False
    db.session.commit()
    assert Usuario.autenticar(admin.email, "Admin@123") is None


def test_usuario_validacoes(app):
    with pytest.raises(ErroValidacao) as erro:
        Usuario.criar("Al", "email-invalido", "123", "GERENTE")
    assert set(erro.value.erros) == {"nome", "email", "senha", "perfil"}


def test_usuario_email_duplicado(admin):
    with pytest.raises(ErroValidacao) as erro:
        Usuario.criar("Outra Pessoa", "admin@teste.com", "12345678")
    assert "email" in erro.value.erros


# ---------------- Marca ----------------

def test_marca_duplicada_ignora_maiusculas(marca):
    with pytest.raises(ErroValidacao):
        Marca.criar("chevrolet")


def test_marca_vazia(app):
    with pytest.raises(ErroValidacao):
        Marca.criar("   ")


def test_marca_com_veiculo_nao_pode_ser_excluida(veiculo):
    with pytest.raises(ErroRegraNegocio):
        veiculo.marca.excluir()


def test_marca_sem_veiculo_pode_ser_excluida(marca):
    marca.excluir()
    db.session.commit()
    assert Marca.query.count() == 0


# ---------------- Veículo ----------------

def test_veiculo_cadastrado_fica_disponivel_e_placa_normalizada(criar_veiculo):
    v = criar_veiculo(placa="abc-1d23")
    assert v.status == "DISPONIVEL"
    assert v.placa == "ABC1D23"
    assert v.preco == Decimal("72900.00")
    assert v.titulo == "Chevrolet Onix 1.0 LT"


@pytest.mark.parametrize("placa", ["ABC1234", "ABC-1234", "abc1d23"])
def test_veiculo_aceita_placas_antiga_e_mercosul(criar_veiculo, placa):
    assert criar_veiculo(placa=placa).placa == Veiculo.normalizar_placa(placa)


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("placa", "AB12345"),
        ("placa", "ABCD123"),
        ("preco", "0"),
        ("preco", "-10"),
        ("preco", "abc"),
        ("quilometragem", "-1"),
        ("ano_fabricacao", "1940"),
        ("ano_fabricacao", str(date.today().year + 2)),
        ("combustivel", "QUEROSENE"),
        ("cambio", "CVT"),
        ("modelo", ""),
        ("cor", ""),
        ("marca_id", "999"),
    ],
)
def test_veiculo_rejeita_dados_invalidos(marca, campo, valor):
    dados = {**DADOS_VEICULO, "marca_id": marca.id, campo: valor}
    with pytest.raises(ErroValidacao) as erro:
        Veiculo().preencher(dados)
    assert campo in erro.value.erros


@pytest.mark.parametrize("ano_modelo, valido", [("2021", True), ("2022", True), ("2023", False), ("2020", False)])
def test_veiculo_ano_modelo_coerente(marca, ano_modelo, valido):
    dados = {**DADOS_VEICULO, "marca_id": marca.id, "ano_fabricacao": "2021", "ano_modelo": ano_modelo}
    v = Veiculo()
    if valido:
        v.preencher(dados)
        assert v.ano_modelo == int(ano_modelo)
    else:
        with pytest.raises(ErroValidacao) as erro:
            v.preencher(dados)
        assert "ano_modelo" in erro.value.erros


def test_veiculo_placa_duplicada(criar_veiculo, marca):
    criar_veiculo()
    with pytest.raises(ErroValidacao) as erro:
        Veiculo().preencher({**DADOS_VEICULO, "marca_id": marca.id})
    assert "placa" in erro.value.erros


def test_veiculo_edicao_mantem_a_propria_placa(veiculo):
    veiculo.preencher({**veiculo.como_formulario(), "preco": "70000"})
    assert veiculo.preco == Decimal("70000.00")


def test_veiculo_invalido_nao_altera_objeto(veiculo):
    with pytest.raises(ErroValidacao):
        veiculo.preencher({**veiculo.como_formulario(), "modelo": "Cruze", "preco": "0"})
    assert veiculo.modelo == "Onix"


def test_veiculo_vendido_nao_pode_ser_editado_nem_excluido(veiculo):
    veiculo.status = "VENDIDO"
    with pytest.raises(ErroRegraNegocio):
        veiculo.preencher(veiculo.como_formulario())
    with pytest.raises(ErroRegraNegocio):
        veiculo.excluir()


def test_veiculo_excluido_remove_propostas(veiculo):
    Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": "70000"})
    db.session.commit()
    veiculo.excluir()
    db.session.commit()
    assert Proposta.query.count() == 0


def test_catalogo_nao_exibe_vendidos(criar_veiculo):
    criar_veiculo(placa="AAA1111")
    vendido = criar_veiculo(placa="BBB2222")
    vendido.status = "VENDIDO"
    db.session.commit()
    placas = [v.placa for v in Veiculo.buscar_catalogo({}).all()]
    assert placas == ["AAA1111"]


def test_catalogo_filtros_combinados(criar_veiculo):
    criar_veiculo(placa="AAA1111", preco="50000", combustivel="FLEX", cambio="MANUAL")
    criar_veiculo(placa="BBB2222", preco="90000", combustivel="DIESEL", cambio="AUTOMATICO", modelo="S10")
    criar_veiculo(placa="CCC3333", preco="120000", combustivel="FLEX", cambio="AUTOMATICO", modelo="Tracker")

    def placas(**filtros):
        return {v.placa for v in Veiculo.buscar_catalogo(filtros).all()}

    assert placas(preco_min="60000") == {"BBB2222", "CCC3333"}
    assert placas(preco_max="100.000") == {"AAA1111", "BBB2222"}
    assert placas(combustivel="flex", cambio="AUTOMATICO") == {"CCC3333"}
    assert placas(q="tracker") == {"CCC3333"}
    assert placas(q="chevrolet") == {"AAA1111", "BBB2222", "CCC3333"}


def test_catalogo_ordenacao_por_preco(criar_veiculo):
    criar_veiculo(placa="AAA1111", preco="50000")
    criar_veiculo(placa="BBB2222", preco="90000")
    menor = [v.placa for v in Veiculo.buscar_catalogo({"ordem": "menor_preco"})]
    maior = [v.placa for v in Veiculo.buscar_catalogo({"ordem": "maior_preco"})]
    assert menor == ["AAA1111", "BBB2222"]
    assert maior == ["BBB2222", "AAA1111"]


# ---------------- Cliente ----------------

def test_cliente_reaproveitado_pelo_email(app):
    """O e-mail identifica o cliente, inclusive com diferença de maiúsculas."""
    c1 = Cliente.obter_ou_criar(DADOS_CLIENTE)
    db.session.commit()
    c2 = Cliente.obter_ou_criar({**DADOS_CLIENTE, "email": "MARIA@exemplo.com", "telefone": "1133334444"})
    assert c1.id == c2.id


def test_cliente_existente_nao_e_reescrito_pela_vitrine(app):
    """C-01: o fluxo público não altera o cadastro de quem já existe."""
    cliente = Cliente.obter_ou_criar(DADOS_CLIENTE)
    db.session.commit()

    Cliente.obter_ou_criar(
        {**DADOS_CLIENTE, "nome": "Outra Pessoa", "telefone": "1133334444"}
    )
    db.session.commit()

    assert cliente.nome == DADOS_CLIENTE["nome"]
    assert cliente.telefone == "11987654321"


def test_cliente_existente_e_atualizado_pelo_painel(app):
    """O funcionário autenticado confere os dados e pode corrigir o cadastro."""
    cliente = Cliente.obter_ou_criar(DADOS_CLIENTE)
    db.session.commit()

    Cliente.obter_ou_criar(
        {**DADOS_CLIENTE, "nome": "Maria Souza Lima", "telefone": "1133334444"},
        atualizar_cadastro=True,
    )
    db.session.commit()

    assert cliente.nome == "Maria Souza Lima"
    assert cliente.telefone == "1133334444"


def test_cliente_validacoes(app):
    with pytest.raises(ErroValidacao) as erro:
        Cliente.obter_ou_criar({"nome": "M", "email": "x", "telefone": "123", "cpf": "111"})
    assert set(erro.value.erros) == {"nome", "email", "telefone", "cpf"}


def test_cliente_cpf_de_outra_pessoa(app):
    Cliente.obter_ou_criar({**DADOS_CLIENTE, "cpf": CPF_VALIDO})
    db.session.commit()
    with pytest.raises(ErroValidacao) as erro:
        Cliente.obter_ou_criar({**DADOS_CLIENTE, "email": "joao@exemplo.com", "cpf": CPF_VALIDO})
    assert "cpf" in erro.value.erros


def test_cliente_email_vinculado_a_outro_cpf(app):
    Cliente.obter_ou_criar({**DADOS_CLIENTE, "cpf": CPF_VALIDO})
    db.session.commit()
    with pytest.raises(ErroValidacao) as erro:
        Cliente.obter_ou_criar({**DADOS_CLIENTE, "cpf": OUTRO_CPF_VALIDO})
    assert "email" in erro.value.erros


# ---------------- Proposta ----------------

def _proposta(veiculo, valor="70000", **extra):
    p = Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": valor, **extra})
    db.session.commit()
    return p


def test_proposta_criada_como_pendente(veiculo):
    p = _proposta(veiculo, "70.000,00")
    assert p.status == "PENDENTE"
    assert p.valor_ofertado == Decimal("70000.00")
    assert p.cliente.email == "maria@exemplo.com"


def test_proposta_valor_invalido_nao_cria_cliente(veiculo):
    with pytest.raises(ErroValidacao) as erro:
        Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": "0"})
    assert "valor_ofertado" in erro.value.erros
    db.session.rollback()
    assert Cliente.query.count() == 0


def test_proposta_para_veiculo_vendido(veiculo):
    veiculo.status = "VENDIDO"
    with pytest.raises(ErroRegraNegocio):
        Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": "70000"})


def test_aceitar_proposta_reserva_veiculo(veiculo):
    p = _proposta(veiculo)
    p.aceitar()
    assert p.status == "ACEITA"
    assert veiculo.status == "RESERVADO"


def test_somente_uma_proposta_aceita_por_veiculo(veiculo):
    p1 = _proposta(veiculo)
    p2 = _proposta(veiculo, "71000", email="joao@exemplo.com")
    p1.aceitar()
    db.session.commit()
    with pytest.raises(ErroRegraNegocio):
        p2.aceitar()


def test_recusar_proposta_aceita_libera_veiculo(veiculo):
    p = _proposta(veiculo)
    p.aceitar()
    p.recusar()
    assert p.status == "RECUSADA"
    assert veiculo.status == "DISPONIVEL"


def test_proposta_recusada_nao_pode_ser_aceita(veiculo):
    p = _proposta(veiculo)
    p.recusar()
    with pytest.raises(ErroRegraNegocio):
        p.aceitar()
    with pytest.raises(ErroRegraNegocio):
        p.recusar()


# ---------------- Venda ----------------

def _dados_venda(veiculo, **extra):
    return {
        **DADOS_CLIENTE,
        "cpf": CPF_VALIDO,
        "veiculo_id": veiculo.id,
        "valor_final": "71000",
        "forma_pagamento": "A_VISTA",
        **extra,
    }


def test_venda_marca_veiculo_como_vendido_e_recusa_outras_propostas(veiculo, vendedor):
    aceita = _proposta(veiculo)
    outra = _proposta(veiculo, "65000", email="joao@exemplo.com")
    aceita.aceitar()
    db.session.commit()

    venda = Venda.registrar(_dados_venda(veiculo, proposta_id=aceita.id), vendedor)
    db.session.commit()

    assert veiculo.status == "VENDIDO"
    assert aceita.status == "ACEITA"
    assert outra.status == "RECUSADA"
    assert venda.cliente.cpf == "52998224725"
    assert Venda.faturamento_total() == Decimal("71000.00")


def test_venda_exige_cpf_valido(veiculo, vendedor):
    with pytest.raises(ErroValidacao) as erro:
        Venda.registrar(_dados_venda(veiculo, cpf=""), vendedor)
    assert "cpf" in erro.value.erros


def test_veiculo_nao_pode_ser_vendido_duas_vezes(veiculo, vendedor):
    Venda.registrar(_dados_venda(veiculo), vendedor)
    db.session.commit()
    with pytest.raises(ErroValidacao) as erro:
        Venda.registrar(_dados_venda(veiculo, email="outro@exemplo.com", cpf=OUTRO_CPF_VALIDO), vendedor)
    assert "veiculo_id" in erro.value.erros


def test_venda_com_proposta_de_outro_veiculo(criar_veiculo, vendedor):
    v1 = criar_veiculo(placa="AAA1111")
    v2 = criar_veiculo(placa="BBB2222")
    p = _proposta(v1)
    with pytest.raises(ErroValidacao) as erro:
        Venda.registrar(_dados_venda(v2, proposta_id=p.id), vendedor)
    assert "proposta_id" in erro.value.erros


def test_venda_valida_forma_pagamento_e_valor(veiculo, vendedor):
    with pytest.raises(ErroValidacao) as erro:
        Venda.registrar(_dados_venda(veiculo, forma_pagamento="PIX_PARCELADO", valor_final="-1"), vendedor)
    assert {"forma_pagamento", "valor_final"} <= set(erro.value.erros)
