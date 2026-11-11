"""Testes unitários das funções auxiliares de conversão e validação."""

from decimal import Decimal

import pytest

from app.models.util import converter_decimal, converter_inteiro, validar_cpf


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("85000", Decimal("85000.00")),
        ("85000.5", Decimal("85000.50")),
        ("85.000,00", Decimal("85000.00")),
        ("R$ 85.000,90", Decimal("85000.90")),
        ("85.000", Decimal("85000.00")),
        ("1.234.567", Decimal("1234567.00")),
        (72900, Decimal("72900.00")),
    ],
)
def test_converter_decimal_formatos_aceitos(entrada, esperado):
    assert converter_decimal(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", None, "abc", "NaN", "Infinity", "12,34,56"])
def test_converter_decimal_invalido_retorna_none(entrada):
    assert converter_decimal(entrada) is None


@pytest.mark.parametrize(
    "entrada, esperado", [("2021", 2021), ("45.000", 45000), (" 10 ", 10), ("-5", -5), (7, 7)]
)
def test_converter_inteiro(entrada, esperado):
    assert converter_inteiro(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", None, "1.5", "dez", "1,5"])
def test_converter_inteiro_invalido(entrada):
    assert converter_inteiro(entrada) is None


@pytest.mark.parametrize("cpf", ["529.982.247-25", "52998224725", "111.444.777-35"])
def test_cpf_valido(cpf):
    assert validar_cpf(cpf)


@pytest.mark.parametrize("cpf", ["529.982.247-26", "111.111.111-11", "123", "", None, "abcdefghijk"])
def test_cpf_invalido(cpf):
    assert not validar_cpf(cpf)
