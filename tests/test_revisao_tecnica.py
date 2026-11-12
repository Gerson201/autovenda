"""Testes de regressão da revisão técnica de código.

Cada teste deste arquivo reproduz um achado registrado em
`docs/situacao-3/06-revisao-tecnica-codigo.md` e falha se o defeito voltar.
O identificador no nome do teste (C-01, S-03, U-02...) é o mesmo usado na
tabela de achados, para dar rastreabilidade entre crítica, correção e teste.
"""

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.config import SECRET_KEY_DESENVOLVIMENTO, TestConfig
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

from .conftest import CPF_VALIDO, DADOS_CLIENTE, OUTRO_CPF_VALIDO, SENHA_ADMIN

DADOS_OUTRO_CLIENTE = {
    "nome": "Joao Pereira",
    "email": "joao@exemplo.com",
    "telefone": "(11) 91111-2222",
}


def _proposta_aceita(veiculo, dados=DADOS_CLIENTE, valor="70000"):
    proposta = Proposta.criar(veiculo, {**dados, "valor_ofertado": valor})
    db.session.commit()
    proposta.aceitar()
    db.session.commit()
    return proposta


# --------------------------------------------------------------------------
# C-02 — venda vinculada à proposta de um cliente e registrada para outro
# --------------------------------------------------------------------------

def test_c02_venda_recusa_proposta_de_outro_cliente(app, admin, veiculo):
    proposta = _proposta_aceita(veiculo)

    with pytest.raises(ErroValidacao) as erro:
        Venda.registrar(
            {
                **DADOS_OUTRO_CLIENTE,
                "cpf": CPF_VALIDO,
                "veiculo_id": veiculo.id,
                "proposta_id": proposta.id,
                "valor_final": "70000",
                "forma_pagamento": "A_VISTA",
            },
            admin,
        )

    assert "proposta_id" in erro.value.erros
    assert "Maria Souza" in erro.value.erros["proposta_id"]


def test_c02_venda_aceita_proposta_do_proprio_comprador(app, admin, veiculo):
    proposta = _proposta_aceita(veiculo)

    venda = Venda.registrar(
        {
            **DADOS_CLIENTE,
            "cpf": CPF_VALIDO,
            "veiculo_id": veiculo.id,
            "proposta_id": proposta.id,
            "valor_final": "70000",
            "forma_pagamento": "A_VISTA",
        },
        admin,
    )
    db.session.commit()

    assert venda.cliente.id == proposta.cliente.id
    assert veiculo.status == "VENDIDO"


# --------------------------------------------------------------------------
# C-03 — veículo reservado vendido a terceiro recusava a proposta em silêncio
# --------------------------------------------------------------------------

def test_c03_veiculo_reservado_nao_e_vendido_a_terceiro_em_silencio(app, admin, veiculo):
    proposta = _proposta_aceita(veiculo)
    assert veiculo.status == "RESERVADO"

    with pytest.raises(ErroValidacao) as erro:
        Venda.registrar(
            {
                **DADOS_OUTRO_CLIENTE,
                "cpf": OUTRO_CPF_VALIDO,
                "veiculo_id": veiculo.id,
                "valor_final": "68000",
                "forma_pagamento": "A_VISTA",
            },
            admin,
        )

    assert "veiculo_id" in erro.value.erros
    assert "reservado" in erro.value.erros["veiculo_id"].lower()
    db.session.rollback()
    assert proposta.status == "ACEITA"
    assert veiculo.status == "RESERVADO"


def test_c03_apos_recusar_a_reserva_a_venda_a_terceiro_e_liberada(app, admin, veiculo):
    proposta = _proposta_aceita(veiculo)
    proposta.recusar()
    db.session.commit()

    venda = Venda.registrar(
        {
            **DADOS_OUTRO_CLIENTE,
            "cpf": OUTRO_CPF_VALIDO,
            "veiculo_id": veiculo.id,
            "valor_final": "68000",
            "forma_pagamento": "A_VISTA",
        },
        admin,
    )
    db.session.commit()

    assert venda.cliente.email == DADOS_OUTRO_CLIENTE["email"]
    assert veiculo.status == "VENDIDO"


# --------------------------------------------------------------------------
# C-04 — placa fora do formato derrubava a listagem do painel
# --------------------------------------------------------------------------

def test_c04_placa_curta_nao_quebra_a_formatacao(app, marca):
    veiculo = Veiculo(
        marca_id=marca.id,
        modelo="Importado por carga SQL",
        ano_fabricacao=2020,
        ano_modelo=2020,
        cor="Azul",
        quilometragem=0,
        combustivel="FLEX",
        cambio="MANUAL",
        preco=50000,
        placa="ABC1",
        status="DISPONIVEL",
    )
    db.session.add(veiculo)
    db.session.commit()

    assert veiculo.placa_formatada == "ABC1"
    assert veiculo.placa_mascarada == "***-**C1"


def test_c04_listagem_do_painel_responde_com_placa_fora_do_formato(client_admin, marca):
    db.session.add(
        Veiculo(
            marca_id=marca.id,
            modelo="Importado",
            ano_fabricacao=2020,
            ano_modelo=2020,
            cor="Azul",
            quilometragem=0,
            combustivel="FLEX",
            cambio="MANUAL",
            preco=50000,
            placa="ABC1",
            status="DISPONIVEL",
        )
    )
    db.session.commit()

    resposta = client_admin.get("/admin/veiculos/")
    assert resposta.status_code == 200
    assert "Importado" in resposta.get_data(as_text=True)


# --------------------------------------------------------------------------
# C-05 — propostas ilimitadas pelo formulário público
# --------------------------------------------------------------------------

def test_c05_uma_proposta_pendente_por_pessoa_e_veiculo(app, veiculo):
    Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": "70000"})
    db.session.commit()

    with pytest.raises(ErroRegraNegocio) as erro:
        Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": "71000"})

    assert "em análise" in str(erro.value)
    db.session.rollback()
    assert Proposta.query.filter_by(veiculo_id=veiculo.id).count() == 1


def test_c05_nova_proposta_liberada_depois_de_recusada(app, veiculo):
    primeira = Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": "70000"})
    db.session.commit()
    primeira.recusar()
    db.session.commit()

    Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": "72000"})
    db.session.commit()

    assert Proposta.query.filter_by(veiculo_id=veiculo.id).count() == 2


def test_c05_proposta_duplicada_exibe_aviso_na_vitrine(client, veiculo):
    dados = {
        "nome": DADOS_CLIENTE["nome"],
        "email": DADOS_CLIENTE["email"],
        "telefone": DADOS_CLIENTE["telefone"],
        "valor_ofertado": "70000",
    }
    client.post(f"/veiculos/{veiculo.id}/propostas", data=dados)
    resposta = client.post(
        f"/veiculos/{veiculo.id}/propostas", data=dados, follow_redirects=True
    )

    assert resposta.status_code == 200
    assert "já tem uma proposta em análise" in resposta.get_data(as_text=True)


def test_c05_pessoas_diferentes_propoem_no_mesmo_veiculo(app, veiculo):
    Proposta.criar(veiculo, {**DADOS_CLIENTE, "valor_ofertado": "70000"})
    Proposta.criar(veiculo, {**DADOS_OUTRO_CLIENTE, "valor_ofertado": "69000"})
    db.session.commit()

    assert Proposta.query.filter_by(veiculo_id=veiculo.id).count() == 2


# --------------------------------------------------------------------------
# C-06 — colisão de integridade na venda não pode virar página 500
# --------------------------------------------------------------------------

def test_c06_colisao_de_integridade_na_venda_mostra_aviso(client_admin, veiculo, monkeypatch):
    """Simula o envio simultâneo do formulário: a restrição uq_venda_veiculo
    estoura no commit, depois de a validação ter passado."""
    original = db.session.commit
    estado = {"commits": 0}

    def commit_com_colisao():
        estado["commits"] += 1
        if estado["commits"] == 1:
            raise IntegrityError(
                "INSERT INTO venda ...", {}, Exception("UNIQUE constraint failed: venda.veiculo_id")
            )
        return original()

    monkeypatch.setattr(db.session, "commit", commit_com_colisao)

    resposta = client_admin.post(
        "/admin/vendas/nova",
        data={
            **DADOS_CLIENTE,
            "cpf": CPF_VALIDO,
            "veiculo_id": veiculo.id,
            "valor_final": "70000",
            "forma_pagamento": "A_VISTA",
        },
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    assert "já havia sido registrada" in resposta.get_data(as_text=True)


# --------------------------------------------------------------------------
# S-01 / S-02 — chave de sessão e cookie
# --------------------------------------------------------------------------

def test_s01_producao_recusa_a_chave_de_desenvolvimento():
    class ConfigProducao(TestConfig):
        AMBIENTE = "producao"
        SECRET_KEY = SECRET_KEY_DESENVOLVIMENTO

    with pytest.raises(RuntimeError) as erro:
        create_app(ConfigProducao)

    assert "SECRET_KEY" in str(erro.value)


def test_s01_producao_sobe_com_chave_propria():
    class ConfigProducao(TestConfig):
        AMBIENTE = "producao"
        SECRET_KEY = "chave-de-producao-para-teste-0123456789"

    app = create_app(ConfigProducao)
    assert app.config["SECRET_KEY"] != SECRET_KEY_DESENVOLVIMENTO
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_s02_cookie_de_sessao_tem_protecoes(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["PERMANENT_SESSION_LIFETIME"].total_seconds() > 0


def test_s02_sessao_do_login_tem_prazo(client, admin):
    resposta = client.post("/login", data={"email": admin.email, "senha": SENHA_ADMIN})
    assert resposta.status_code == 302
    with client.session_transaction() as sessao:
        assert sessao.permanent is True


# --------------------------------------------------------------------------
# S-03 — força bruta no login
# --------------------------------------------------------------------------

@pytest.fixture
def app_com_limite():
    class ConfigLimite(TestConfig):
        LOGIN_MAX_TENTATIVAS = 3
        LOGIN_JANELA_MINUTOS = 10
        LOGIN_BLOQUEIO_MINUTOS = 15

    app = create_app(ConfigLimite)
    with app.app_context():
        Usuario.criar("Ana Admin", "admin@teste.com", SENHA_ADMIN, "ADMIN")
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


def test_s03_login_bloqueia_apos_tentativas_falhas(app_com_limite):
    cliente = app_com_limite.test_client()
    dados_errados = {"email": "admin@teste.com", "senha": "senha-errada"}

    assert cliente.post("/login", data=dados_errados).status_code == 401
    assert cliente.post("/login", data=dados_errados).status_code == 401

    terceira = cliente.post("/login", data=dados_errados)
    assert terceira.status_code == 429
    assert "bloqueadas" in terceira.get_data(as_text=True)

    # Com o bloqueio ativo, nem a senha correta passa.
    correta = cliente.post("/login", data={"email": "admin@teste.com", "senha": SENHA_ADMIN})
    assert correta.status_code == 429


def test_s03_login_correto_zera_o_contador(app_com_limite):
    cliente = app_com_limite.test_client()
    cliente.post("/login", data={"email": "admin@teste.com", "senha": "errada"})
    cliente.post("/login", data={"email": "admin@teste.com", "senha": SENHA_ADMIN})
    cliente.post("/logout")

    # Se o contador não tivesse sido zerado, duas falhas bastariam para bloquear.
    assert cliente.post("/login", data={"email": "admin@teste.com", "senha": "errada"}).status_code == 401
    assert cliente.post("/login", data={"email": "admin@teste.com", "senha": "errada"}).status_code == 401


# --------------------------------------------------------------------------
# U-01 / U-02 / U-03 — filtros do catálogo
# --------------------------------------------------------------------------

def test_u01_faixa_de_preco_invertida_explica_o_motivo(client, criar_veiculo):
    criar_veiculo(placa="AAA1111", preco="50000.00")

    resposta = client.get("/?preco_min=200000&preco_max=10000")
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "O preço máximo deve ser maior que o mínimo" in corpo
    # O filtro inválido é descartado em vez de devolver uma lista vazia sem motivo.
    assert "AAA1111" in corpo or "1 veículo encontrado" in corpo


def test_u01_faixa_de_ano_invertida_explica_o_motivo(client, criar_veiculo):
    criar_veiculo(placa="AAA1111")

    resposta = client.get("/?ano_min=2024&ano_max=2000")
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "O ano final deve ser maior que o inicial" in corpo


def test_u01_faixa_valida_continua_filtrando(client, criar_veiculo):
    criar_veiculo(placa="AAA1111", preco="40000.00")
    criar_veiculo(placa="BBB2222", preco="90000.00")

    corpo = client.get("/?preco_min=30000&preco_max=50000").get_data(as_text=True)
    assert "1 veículo encontrado" in corpo


def test_u02_busca_preserva_os_filtros_ativos(client, criar_veiculo, marca):
    criar_veiculo(placa="AAA1111")

    corpo = client.get(f"/?marca={marca.id}&combustivel=FLEX&ordem=menor_preco").get_data(
        as_text=True
    )

    # O formulário de busca leva os filtros em campos ocultos.
    assert f'<input type="hidden" name="marca" value="{marca.id}">' in corpo
    assert '<input type="hidden" name="combustivel" value="FLEX">' in corpo


def test_u03_filtro_de_ano_maximo(client, criar_veiculo):
    criar_veiculo(placa="AAA1111", ano_fabricacao="2015", ano_modelo="2015")
    criar_veiculo(placa="BBB2222", ano_fabricacao="2023", ano_modelo="2023")

    corpo = client.get("/?ano_max=2016").get_data(as_text=True)
    assert "AAA1111" in corpo or "1 veículo encontrado" in corpo
    assert "2023/2023" not in corpo


# --------------------------------------------------------------------------
# A-01 — erros de campo anunciáveis por leitor de tela
# --------------------------------------------------------------------------

def test_a01_erros_de_campo_tem_aria_live(client, veiculo):
    corpo = client.get(f"/veiculos/{veiculo.id}").get_data(as_text=True)
    assert 'class="erro-campo" id="erro-email" aria-live="polite"' in corpo


# --------------------------------------------------------------------------
# D-01 — N+1 nas listas do painel
# --------------------------------------------------------------------------

def _contar_consultas(app, acao):
    consultas = []

    def registrar(_conexao, _cursor, instrucao, *_resto):
        if instrucao.lstrip().upper().startswith("SELECT"):
            consultas.append(instrucao)

    event.listen(db.engine, "before_cursor_execute", registrar)
    try:
        acao()
    finally:
        event.remove(db.engine, "before_cursor_execute", registrar)
    return len(consultas)


def test_d01_lista_de_propostas_nao_cresce_em_consultas(app, client_admin, criar_veiculo):
    def criar_propostas(quantidade, inicio):
        for i in range(inicio, inicio + quantidade):
            v = criar_veiculo(placa=f"AAA{1000 + i}")
            Proposta.criar(
                v,
                {
                    "nome": f"Cliente {i}",
                    "email": f"cliente{i}@exemplo.com",
                    "telefone": "11988887777",
                    "valor_ofertado": "50000",
                },
            )
        db.session.commit()

    criar_propostas(3, 0)
    db.session.expire_all()
    com_3 = _contar_consultas(app, lambda: client_admin.get("/admin/propostas/"))

    criar_propostas(6, 100)
    db.session.expire_all()
    com_9 = _contar_consultas(app, lambda: client_admin.get("/admin/propostas/"))

    assert com_9 == com_3, (
        f"O número de consultas cresceu com as linhas ({com_3} -> {com_9}): "
        "o carregamento antecipado de cliente/veículo/marca foi perdido."
    )


def test_d01_lista_de_veiculos_do_painel_nao_consulta_marca_por_linha(
    app, client_admin, criar_veiculo
):
    """Cada veículo recebe uma marca diferente de propósito.

    Com uma única marca compartilhada, o mapa de identidade do SQLAlchemy
    responderia o acesso a `v.marca` sem ir ao banco e o teste passaria mesmo
    com o N+1 presente. É também por isso que o catálogo público não sofria do
    problema: o controller já carrega todas as marcas para o filtro lateral.
    """
    def veiculo_de_marca_nova(indice):
        marca = Marca.criar(f"Marca {indice}")
        db.session.commit()
        return criar_veiculo(placa=f"AAA{1000 + indice}", marca_id=marca.id)

    veiculo_de_marca_nova(1)
    db.session.expire_all()
    com_1 = _contar_consultas(app, lambda: client_admin.get("/admin/veiculos/"))

    for i in range(2, 6):
        veiculo_de_marca_nova(i)
    db.session.expire_all()
    com_5 = _contar_consultas(app, lambda: client_admin.get("/admin/veiculos/"))

    assert com_5 == com_1, (
        f"A listagem passou a consultar a marca por linha ({com_1} -> {com_5})."
    )


# --------------------------------------------------------------------------
# Controle de tentativas (unidade)
# --------------------------------------------------------------------------

def test_controle_de_tentativas_libera_depois_do_prazo():
    from datetime import datetime, timedelta

    from app.servicos.limites import ControleTentativas

    controle = ControleTentativas(maximo=2, janela_minutos=10, bloqueio_minutos=15)
    assert controle.registrar_falha("a") is False
    assert controle.registrar_falha("a") is True
    assert controle.bloqueada("a") is True

    # Avança o relógio do controle para além do bloqueio.
    controle._agora = lambda: datetime.now() + timedelta(minutes=16)
    assert controle.bloqueada("a") is False


def test_controle_de_tentativas_separa_as_chaves():
    from app.servicos.limites import ControleTentativas

    controle = ControleTentativas(maximo=2)
    controle.registrar_falha("a")
    controle.registrar_falha("a")
    assert controle.bloqueada("a") is True
    assert controle.bloqueada("b") is False


def test_marca_e_cliente_seguem_funcionando(app):
    """Guarda-corpo: as correções não mexeram nas regras já existentes."""
    Marca.criar("Fiat")
    db.session.commit()
    cliente = Cliente.obter_ou_criar({**DADOS_CLIENTE, "cpf": CPF_VALIDO})
    db.session.commit()
    assert cliente.cpf_formatado == "529.982.247-25"
