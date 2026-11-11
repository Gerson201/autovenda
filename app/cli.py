"""Comandos de terminal: `flask --app run seed` e `flask --app run criar-usuario`."""

import os
import shutil
from uuid import uuid4

import click
from flask import current_app

from .extensions import db
from .models import ErroValidacao, Marca, Usuario, Veiculo

MARCAS_INICIAIS = [
    "Chevrolet", "Fiat", "Ford", "Honda", "Hyundai", "Jeep",
    "Nissan", "Renault", "Toyota", "Volkswagen",
]

VEICULOS_INICIAIS = [
    ("Chevrolet", "Onix", "1.0 Turbo RS", 2022, 2023, "Vermelho", 28500, "FLEX", "MANUAL", "84900.00", "QTX1A23",
     "Único dono, revisões na concessionária, IPVA pago."),
    ("Fiat", "Argo", "1.3 Trekking", 2021, 2021, "Vermelho", 41200, "FLEX", "MANUAL", "69900.00", "FJA4B56",
     "Multimídia com Android Auto e Apple CarPlay."),
    ("Toyota", "Corolla", "2.0 XEi", 2020, 2021, "Azul", 55800, "FLEX", "AUTOMATICO", "119900.00", "TYC2C34",
     "Câmbio CVT, bancos em couro, manual e chave reserva."),
    ("Volkswagen", "T-Cross", "1.0 TSI Comfortline", 2022, 2022, "Cinza", 33000, "FLEX", "AUTOMATICO",
     "129500.00", "VWT5D67", "Teto solar, sensor de estacionamento, garantia de fábrica."),
    ("Honda", "Civic", "2.0 EXL", 2019, 2019, "Branco", 72000, "FLEX", "AUTOMATICO", "112000.00", "HCV8901",
     "Bem conservado, pneus novos."),
    ("Jeep", "Renegade", "1.3 T270 Longitude", 2023, 2023, "Cinza", 15400, "FLEX", "AUTOMATICO", "139900.00",
     "JRN3E45", "Ainda na garantia, completo."),
    ("Hyundai", "HB20", "1.0 Sense", 2020, 2020, "Branco", 60500, "FLEX", "MANUAL", "57900.00", "HBZ6F78",
     "Econômico, ideal para o dia a dia."),
    ("Ford", "Ranger", "XLT 4x4 Cabine Dupla", 2019, 2020, "Branco", 98000, "DIESEL", "AUTOMATICO", "179900.00",
     "FRG9012", "Capota marítima e engate."),
    ("Toyota", "Corolla Cross", "1.8 Hybrid XRX", 2023, 2024, "Prata", 12000, "HIBRIDO", "AUTOMATICO",
     "189900.00", "TCC7G89", "Híbrido, baixíssimo consumo."),
]

# Fotos livres (Wikimedia Commons) nomeadas pela placa; créditos em seed_imagens/CREDITOS.md
PASTA_IMAGENS_SEED = os.path.join(os.path.dirname(__file__), "seed_imagens")


def _copiar_foto_seed(placa):
    """Copia a foto de demonstração para a pasta de uploads e devolve o nome gerado."""
    origem = os.path.join(PASTA_IMAGENS_SEED, f"{placa}.jpg")
    if not os.path.exists(origem):
        return None
    pasta = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(pasta, exist_ok=True)
    nome = f"{uuid4().hex}.jpg"
    shutil.copyfile(origem, os.path.join(pasta, nome))
    return nome


def registrar(app):
    @app.cli.command("seed")
    def seed():
        """Cria usuários, marcas e veículos de demonstração."""
        if not Usuario.query.filter_by(email="admin@autovenda.com").first():
            Usuario.criar("Administrador", "admin@autovenda.com", "Admin@123", "ADMIN")
        if not Usuario.query.filter_by(email="vendedor@autovenda.com").first():
            Usuario.criar("Carla Vendedora", "vendedor@autovenda.com", "Vende@123", "VENDEDOR")

        for nome in MARCAS_INICIAIS:
            if not Marca.query.filter_by(nome=nome).first():
                Marca.criar(nome)
        db.session.commit()

        criados = fotos = 0
        for (marca, modelo, versao, fab, mod, cor, km, comb, cambio, preco, placa, desc) in VEICULOS_INICIAIS:
            existente = Veiculo.query.filter_by(placa=placa).first()
            if existente:
                if existente.imagem is None and existente.status != "VENDIDO":
                    existente.imagem = _copiar_foto_seed(placa)
                    fotos += existente.imagem is not None
                continue
            veiculo = Veiculo()
            veiculo.preencher({
                "marca_id": Marca.query.filter_by(nome=marca).first().id,
                "modelo": modelo, "versao": versao, "ano_fabricacao": fab, "ano_modelo": mod,
                "cor": cor, "quilometragem": km, "combustivel": comb, "cambio": cambio,
                "preco": preco, "placa": placa, "descricao": desc,
            })
            veiculo.imagem = _copiar_foto_seed(placa)
            fotos += veiculo.imagem is not None
            db.session.add(veiculo)
            criados += 1
        db.session.commit()
        click.echo(f"Dados de demonstração prontos ({criados} veículo(s) novo(s), {fotos} foto(s) adicionada(s)).")
        click.echo("Admin: admin@autovenda.com / Admin@123")
        click.echo("Vendedor: vendedor@autovenda.com / Vende@123")

    @app.cli.command("criar-usuario")
    @click.option("--nome", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--perfil", type=click.Choice(["ADMIN", "VENDEDOR"]), default="VENDEDOR", prompt=True)
    @click.password_option("--senha")
    def criar_usuario(nome, email, perfil, senha):
        """Cria um usuário do painel administrativo."""
        try:
            Usuario.criar(nome, email, senha, perfil)
            db.session.commit()
        except ErroValidacao as erro:
            db.session.rollback()
            raise click.ClickException(str(erro)) from erro
        click.echo(f"Usuário {email} criado.")
