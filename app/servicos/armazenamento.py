"""Gravação das fotos dos veículos em disco."""

import os
from uuid import uuid4

from flask import current_app


def _extensao(nome_arquivo):
    nome_arquivo = nome_arquivo or ""
    return nome_arquivo.rsplit(".", 1)[-1].lower() if "." in nome_arquivo else ""


def _assinatura_valida(extensao, cabecalho):
    if extensao in ("jpg", "jpeg"):
        return cabecalho.startswith(b"\xff\xd8\xff")
    if extensao == "png":
        return cabecalho.startswith(b"\x89PNG\r\n\x1a\n")
    if extensao == "webp":
        return cabecalho[:4] == b"RIFF" and cabecalho[8:12] == b"WEBP"
    return False


def validar_imagem(arquivo):
    """Retorna a mensagem de erro, ou None se o arquivo for uma imagem aceita."""
    extensao = _extensao(arquivo.filename)
    if extensao not in current_app.config["EXTENSOES_IMAGEM"]:
        return "Formato de imagem não permitido. Envie um arquivo JPG, PNG ou WEBP."
    cabecalho = arquivo.stream.read(12)
    arquivo.stream.seek(0)
    if not _assinatura_valida(extensao, cabecalho):
        return "O arquivo enviado não é uma imagem válida."
    return None


def salvar_imagem(arquivo):
    """Grava com nome aleatório (evita sobrescrita e path traversal) e devolve o nome."""
    nome = f"{uuid4().hex}.{_extensao(arquivo.filename)}"
    pasta = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(pasta, exist_ok=True)
    arquivo.save(os.path.join(pasta, nome))
    return nome


def remover_imagem(nome):
    if not nome:
        return
    caminho = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(nome))
    try:
        os.remove(caminho)
    except OSError:
        current_app.logger.warning("Não foi possível remover a imagem %s", caminho)
