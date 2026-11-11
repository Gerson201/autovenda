import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_MILHAR_RE = re.compile(r"-?\d{1,3}(\.\d{3})+")

PRECO_MAXIMO = Decimal("99999999.99")


def agora():
    return datetime.now()


def texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def somente_digitos(valor):
    return re.sub(r"\D", "", texto(valor))


def converter_inteiro(valor):
    """Converte "45000", "45.000" ou 45000 para int. Retorna None se inválido."""
    s = texto(valor)
    if _MILHAR_RE.fullmatch(s):
        s = s.replace(".", "")
    try:
        return int(s)
    except ValueError:
        return None


def converter_decimal(valor):
    """Aceita "85000.00", "85.000,00", "R$ 85.000,00" e "85.000". Retorna None se inválido."""
    s = texto(valor).replace("R$", "").replace(" ", "").replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif _MILHAR_RE.fullmatch(s):
        s = s.replace(".", "")
    try:
        numero = Decimal(s)
        if not numero.is_finite():
            return None
        return numero.quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def validar_cpf(cpf):
    digitos = somente_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(int(digitos[i]) * (posicao + 1 - i) for i in range(posicao))
        verificador = (soma * 10) % 11 % 10
        if verificador != int(digitos[posicao]):
            return False
    return True
