"""Testes dos Controllers + Views: rotas HTTP, autenticação, permissões e mensagens."""

import io

from app.extensions import db
from app.models import Marca, Proposta, Veiculo, Venda

from .conftest import CPF_VALIDO, DADOS_CLIENTE, DADOS_VEICULO, fazer_login

PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00"
    b"\x00\x00\x00IEND\xaeB`\x82"
)


def html(resposta):
    return resposta.get_data(as_text=True)


# ---------------- Catálogo público ----------------

def test_catalogo_vazio_exibe_mensagem(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Nenhum veículo encontrado" in html(resposta)


def test_catalogo_lista_veiculo_com_preco_formatado(client, veiculo):
    pagina = html(client.get("/"))
    assert "Chevrolet Onix" in pagina
    assert "R$ 72.900,00" in pagina
    assert "35.000 km" in pagina


def test_catalogo_filtro_por_texto(client, criar_veiculo):
    criar_veiculo(placa="AAA1111", modelo="Onix")
    criar_veiculo(placa="BBB2222", modelo="Tracker")
    pagina = html(client.get("/?q=tracker"))
    assert "Tracker" in pagina and "Onix" not in pagina


def test_catalogo_parametros_invalidos_nao_quebram(client, veiculo):
    resposta = client.get("/?preco_min=abc&ano_min=xyz&pagina=999&ordem=hack")
    assert resposta.status_code == 200


def test_detalhe_do_veiculo_oculta_placa(client, veiculo):
    pagina = html(client.get(f"/veiculos/{veiculo.id}"))
    assert "Fazer uma proposta" in pagina
    assert "ABC1D23" not in pagina
    assert "***-**23" in pagina


def test_detalhe_inexistente_ou_vendido_retorna_404(client, veiculo):
    assert client.get("/veiculos/999").status_code == 404
    veiculo.status = "VENDIDO"
    db.session.commit()
    resposta = client.get(f"/veiculos/{veiculo.id}")
    assert resposta.status_code == 404
    assert "Página não encontrada" in html(resposta)


def test_enviar_proposta_valida(client, veiculo):
    resposta = client.post(
        f"/veiculos/{veiculo.id}/propostas",
        data={**DADOS_CLIENTE, "valor_ofertado": "70000", "mensagem": "Aceita troca?"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert "Proposta enviada com sucesso" in html(resposta)
    assert Proposta.query.count() == 1


def test_enviar_proposta_invalida_mostra_erros_e_mantem_dados(client, veiculo):
    resposta = client.post(
        f"/veiculos/{veiculo.id}/propostas",
        data={"nome": "Maria Souza", "email": "invalido", "telefone": "123", "valor_ofertado": ""},
    )
    pagina = html(resposta)
    assert resposta.status_code == 422
    assert "Informe um e-mail válido" in pagina
    assert "Informe o telefone com DDD" in pagina
    assert 'value="Maria Souza"' in pagina
    assert Proposta.query.count() == 0


# ---------------- Autenticação e permissões ----------------

def test_painel_exige_login(client):
    resposta = client.get("/admin/veiculos/")
    assert resposta.status_code == 302
    assert "/login" in resposta.headers["Location"]


def test_login_invalido(client, admin):
    resposta = fazer_login(client, admin.email, "senhaerrada")
    assert resposta.status_code == 401
    assert "E-mail ou senha incorretos" in html(resposta)


def test_login_redireciona_para_destino_interno(client, admin):
    resposta = client.post(
        "/login?proximo=/admin/vendas/", data={"email": admin.email, "senha": "Admin@123"}
    )
    assert resposta.headers["Location"].endswith("/admin/vendas/")


def test_login_ignora_redirecionamento_externo(client, admin):
    resposta = client.post(
        "/login?proximo=//site-malicioso.com", data={"email": admin.email, "senha": "Admin@123"}
    )
    assert "site-malicioso" not in resposta.headers["Location"]


def test_logout(client_admin):
    client_admin.post("/logout")
    assert client_admin.get("/admin/").status_code == 302


def test_painel_mostra_indicadores(client_admin, veiculo):
    pagina = html(client_admin.get("/admin/"))
    assert "Disponíveis" in pagina
    assert "Propostas pendentes" in pagina


# ---------------- CRUD de veículos ----------------

def test_cadastrar_veiculo_com_foto(client_admin, marca, app):
    dados = {**DADOS_VEICULO, "marca_id": str(marca.id), "imagem": (io.BytesIO(PNG_1PX), "carro.png")}
    resposta = client_admin.post(
        "/admin/veiculos/novo", data=dados, content_type="multipart/form-data", follow_redirects=True
    )
    assert "Veículo cadastrado com sucesso" in html(resposta)
    veiculo = Veiculo.query.one()
    assert veiculo.imagem.endswith(".png")


def test_cadastrar_veiculo_invalido_retorna_422(client_admin, marca):
    dados = {**DADOS_VEICULO, "marca_id": str(marca.id), "placa": "XX", "preco": "0"}
    resposta = client_admin.post("/admin/veiculos/novo", data=dados)
    pagina = html(resposta)
    assert resposta.status_code == 422
    assert "Placa inválida" in pagina
    assert "Informe um preço maior que zero" in pagina
    assert Veiculo.query.count() == 0


def test_cadastrar_veiculo_rejeita_arquivo_que_nao_e_imagem(client_admin, marca):
    dados = {
        **DADOS_VEICULO,
        "marca_id": str(marca.id),
        "imagem": (io.BytesIO(b"<?php echo 'x'; ?>"), "foto.png"),
    }
    resposta = client_admin.post("/admin/veiculos/novo", data=dados, content_type="multipart/form-data")
    assert resposta.status_code == 422
    assert "não é uma imagem válida" in html(resposta)


def test_cadastrar_veiculo_rejeita_extensao(client_admin, marca):
    dados = {**DADOS_VEICULO, "marca_id": str(marca.id), "imagem": (io.BytesIO(b"x"), "virus.exe")}
    resposta = client_admin.post("/admin/veiculos/novo", data=dados, content_type="multipart/form-data")
    assert "Formato de imagem não permitido" in html(resposta)


def test_cadastro_sem_marcas_redireciona(client_admin):
    resposta = client_admin.get("/admin/veiculos/novo", follow_redirects=True)
    assert "Cadastre ao menos uma marca" in html(resposta)


def test_editar_veiculo(client_admin, veiculo):
    dados = {**veiculo.como_formulario(), "preco": "69900", "cor": "Preto"}
    resposta = client_admin.post(f"/admin/veiculos/{veiculo.id}/editar", data=dados, follow_redirects=True)
    assert "Veículo atualizado com sucesso" in html(resposta)
    assert veiculo.cor == "Preto"


def test_editar_veiculo_vendido_bloqueado(client_admin, veiculo):
    veiculo.status = "VENDIDO"
    db.session.commit()
    resposta = client_admin.get(f"/admin/veiculos/{veiculo.id}/editar", follow_redirects=True)
    assert "Veículos vendidos não podem ser alterados" in html(resposta)


def test_lista_veiculos_filtra_por_placa(client_admin, criar_veiculo):
    criar_veiculo(placa="AAA1111", modelo="Onix")
    criar_veiculo(placa="BBB2222", modelo="Tracker")
    pagina = html(client_admin.get("/admin/veiculos/?q=bbb-2222"))
    assert "Tracker" in pagina and "Onix" not in pagina


def test_vendedor_nao_pode_excluir_veiculo(client_vendedor, veiculo):
    resposta = client_vendedor.post(f"/admin/veiculos/{veiculo.id}/excluir")
    assert resposta.status_code == 403
    assert Veiculo.query.count() == 1


def test_admin_exclui_veiculo(client_admin, veiculo):
    resposta = client_admin.post(f"/admin/veiculos/{veiculo.id}/excluir", follow_redirects=True)
    assert "Veículo excluído" in html(resposta)
    assert Veiculo.query.count() == 0


# ---------------- Marcas ----------------

def test_admin_cadastra_marca(client_admin):
    resposta = client_admin.post("/admin/marcas/", data={"nome": "Peugeot"}, follow_redirects=True)
    assert "Marca &#34;Peugeot&#34; cadastrada" in html(resposta)
    assert Marca.query.filter_by(nome="Peugeot").count() == 1


def test_marca_duplicada_mostra_erro(client_admin, marca):
    resposta = client_admin.post("/admin/marcas/", data={"nome": "CHEVROLET"})
    assert resposta.status_code == 422
    assert "já está cadastrada" in html(resposta)


def test_vendedor_nao_cadastra_marca(client_vendedor):
    assert client_vendedor.post("/admin/marcas/", data={"nome": "Kia"}).status_code == 403


def test_excluir_marca_em_uso(client_admin, veiculo):
    resposta = client_admin.post(f"/admin/marcas/{veiculo.marca_id}/excluir", follow_redirects=True)
    assert "não pode ser excluída" in html(resposta)
    assert Marca.query.count() == 1


# ---------------- Propostas e vendas ----------------

def _criar_proposta(veiculo, email="maria@exemplo.com"):
    proposta = Proposta.criar(veiculo, {**DADOS_CLIENTE, "email": email, "valor_ofertado": "70000"})
    db.session.commit()
    return proposta


def test_aceitar_e_recusar_proposta_pelo_painel(client_vendedor, veiculo):
    proposta = _criar_proposta(veiculo)
    resposta = client_vendedor.post(f"/admin/propostas/{proposta.id}/aceitar", follow_redirects=True)
    assert "foi reservado" in html(resposta)
    assert veiculo.status == "RESERVADO"

    resposta = client_vendedor.post(f"/admin/propostas/{proposta.id}/recusar", follow_redirects=True)
    assert "Proposta recusada" in html(resposta)
    assert veiculo.status == "DISPONIVEL"


def test_aceitar_segunda_proposta_mostra_erro(client_vendedor, veiculo):
    p1 = _criar_proposta(veiculo)
    p2 = _criar_proposta(veiculo, "joao@exemplo.com")
    client_vendedor.post(f"/admin/propostas/{p1.id}/aceitar")
    resposta = client_vendedor.post(f"/admin/propostas/{p2.id}/aceitar", follow_redirects=True)
    assert "Já existe uma proposta aceita" in html(resposta)


def test_formulario_de_venda_preenchido_pela_proposta(client_vendedor, veiculo):
    proposta = _criar_proposta(veiculo)
    pagina = html(client_vendedor.get(f"/admin/vendas/nova?proposta_id={proposta.id}"))
    assert 'value="maria@exemplo.com"' in pagina
    assert 'value="70000.00"' in pagina


def test_registrar_venda_pelo_painel(client_vendedor, veiculo, vendedor):
    dados = {
        **DADOS_CLIENTE,
        "cpf": CPF_VALIDO,
        "veiculo_id": str(veiculo.id),
        "valor_final": "71000",
        "forma_pagamento": "FINANCIAMENTO",
    }
    resposta = client_vendedor.post("/admin/vendas/nova", data=dados, follow_redirects=True)
    pagina = html(resposta)
    assert "registrada com sucesso" in pagina
    assert "R$ 71.000,00" in pagina
    assert Venda.query.one().vendedor_id == vendedor.id


def test_registrar_venda_invalida(client_vendedor, veiculo):
    resposta = client_vendedor.post("/admin/vendas/nova", data={"veiculo_id": str(veiculo.id)})
    assert resposta.status_code == 422
    assert "Informe o CPF do comprador" in html(resposta)
    assert veiculo.status == "DISPONIVEL"


# ---------------- Erros e segurança ----------------

def test_pagina_404_amigavel(client):
    resposta = client.get("/nao-existe")
    assert resposta.status_code == 404
    assert "Ir para o catálogo" in html(resposta)


def test_metodo_nao_permitido(client_admin, veiculo):
    assert client_admin.get(f"/admin/veiculos/{veiculo.id}/excluir").status_code == 405


def test_cabecalhos_de_seguranca(client):
    resposta = client.get("/")
    assert resposta.headers["X-Frame-Options"] == "DENY"
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"


def test_csrf_bloqueia_post_sem_token(app, veiculo):
    app.config["CSRF_ENABLED"] = True
    client = app.test_client()
    resposta = client.post(f"/veiculos/{veiculo.id}/propostas", data={**DADOS_CLIENTE, "valor_ofertado": "1"})
    assert resposta.status_code == 400
    assert "Sua sessão expirou" in html(resposta)


def test_csrf_aceita_post_com_token(app, veiculo):
    app.config["CSRF_ENABLED"] = True
    client = app.test_client()
    client.get(f"/veiculos/{veiculo.id}")
    with client.session_transaction() as sessao:
        token = sessao["_csrf"]
    resposta = client.post(
        f"/veiculos/{veiculo.id}/propostas",
        data={**DADOS_CLIENTE, "valor_ofertado": "70000", "csrf_token": token},
    )
    assert resposta.status_code == 302


def test_campos_sao_escapados_contra_xss(client_admin, veiculo):
    Proposta.criar(
        veiculo,
        {**DADOS_CLIENTE, "nome": "<script>alert(1)</script>", "valor_ofertado": "70000"},
    )
    db.session.commit()
    pagina = html(client_admin.get("/admin/propostas/"))
    assert "<script>alert(1)</script>" not in pagina
    assert "&lt;script&gt;" in pagina
