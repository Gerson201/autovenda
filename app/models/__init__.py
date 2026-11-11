"""Camada MODEL: entidades, validações e regras de negócio."""

from .cliente import Cliente
from .erros import ErroRegraNegocio, ErroValidacao
from .marca import Marca
from .proposta import STATUS_PROPOSTA, Proposta
from .usuario import PERFIS, Usuario
from .veiculo import CAMBIOS, COMBUSTIVEIS, ORDENACOES, STATUS_VEICULO, Veiculo
from .venda import FORMAS_PAGAMENTO, Venda

__all__ = [
    "CAMBIOS",
    "COMBUSTIVEIS",
    "Cliente",
    "ErroRegraNegocio",
    "ErroValidacao",
    "FORMAS_PAGAMENTO",
    "Marca",
    "ORDENACOES",
    "PERFIS",
    "Proposta",
    "STATUS_PROPOSTA",
    "STATUS_VEICULO",
    "Usuario",
    "Veiculo",
    "Venda",
]
