"""Testes de integração/sistema: fluxos completos atravessando Controller, Model e banco."""

from app.models import Cliente, Marca, Proposta, Veiculo, Venda

from .conftest import CPF_VALIDO, DADOS_VEICULO, SENHA_ADMIN, fazer_login


def test_fluxo_completo_cadastro_proposta_venda(client, admin):
    """Admin cadastra marca e veículo → cliente faz proposta → vendedor aceita e vende."""
    # 1. Login do administrador
    fazer_login(client, admin.email, SENHA_ADMIN)

    # 2. Cadastro da marca e do veículo
    client.post("/admin/marcas/", data={"nome": "Toyota"})
    marca_id = Marca.query.filter_by(nome="Toyota").one().id
    client.post(
        "/admin/veiculos/novo",
        data={**DADOS_VEICULO, "marca_id": str(marca_id), "modelo": "Corolla", "placa": "TYC2C34", "preco": "119900"},
    )
    veiculo = Veiculo.query.filter_by(placa="TYC2C34").one()
    client.post("/logout")

    # 3. Visitante vê no catálogo e envia duas propostas
    assert "Corolla" in client.get("/").get_data(as_text=True)
    for email, valor in (("ana@exemplo.com", "115000"), ("bruno@exemplo.com", "110000")):
        client.post(
            f"/veiculos/{veiculo.id}/propostas",
            data={"nome": "Cliente Teste", "email": email, "telefone": "11912345678", "valor_ofertado": valor},
        )
    assert Proposta.query.filter_by(status="PENDENTE").count() == 2

    # 4. Admin aceita a melhor proposta → veículo reservado (continua no catálogo com selo)
    fazer_login(client, admin.email, SENHA_ADMIN)
    melhor = Proposta.query.join(Cliente).filter(Cliente.email == "ana@exemplo.com").one()
    client.post(f"/admin/propostas/{melhor.id}/aceitar")
    assert veiculo.status == "RESERVADO"
    assert "Reservado" in client.get("/").get_data(as_text=True)

    # 5. Registra a venda a partir da proposta
    resposta = client.post(
        "/admin/vendas/nova",
        data={
            "proposta_id": str(melhor.id),
            "veiculo_id": str(veiculo.id),
            "nome": "Ana Compradora",
            "email": "ana@exemplo.com",
            "telefone": "11912345678",
            "cpf": CPF_VALIDO,
            "valor_final": "115000",
            "forma_pagamento": "A_VISTA",
        },
        follow_redirects=True,
    )
    assert "registrada com sucesso" in resposta.get_data(as_text=True)

    # 6. Estado final consistente
    assert veiculo.status == "VENDIDO"
    assert Venda.query.one().valor_final == 115000
    assert Proposta.query.filter_by(status="RECUSADA").count() == 1
    assert f"/veiculos/{veiculo.id}" not in client.get("/").get_data(as_text=True)
    assert client.get(f"/veiculos/{veiculo.id}").status_code == 404
    assert "R$ 115.000,00" in client.get("/admin/").get_data(as_text=True)


def test_fluxo_reserva_desfeita_volta_ao_catalogo(client, admin, veiculo):
    client.post(
        f"/veiculos/{veiculo.id}/propostas",
        data={"nome": "Carlos Lima", "email": "carlos@exemplo.com", "telefone": "1133334444", "valor_ofertado": "60000"},
    )
    fazer_login(client, admin.email, SENHA_ADMIN)
    proposta = Proposta.query.one()
    client.post(f"/admin/propostas/{proposta.id}/aceitar")
    assert veiculo.status == "RESERVADO"
    client.post(f"/admin/propostas/{proposta.id}/recusar")
    assert veiculo.status == "DISPONIVEL"
    assert client.get(f"/veiculos/{veiculo.id}").status_code == 200


def test_comando_seed_e_idempotente(app):
    runner = app.test_cli_runner()
    primeira = runner.invoke(args=["seed"])
    assert primeira.exit_code == 0, primeira.output
    total = Veiculo.query.count()
    assert total == 9
    assert Veiculo.query.filter(Veiculo.imagem.isnot(None)).count() == 9
    assert "9 foto(s) adicionada(s)" in primeira.output
    segunda = runner.invoke(args=["seed"])
    assert segunda.exit_code == 0
    assert Veiculo.query.count() == total
    assert "0 veículo(s) novo(s)" in segunda.output
