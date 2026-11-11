class ErroValidacao(Exception):
    """Dados de entrada inválidos. `erros` mapeia o nome do campo para a mensagem."""

    def __init__(self, erros):
        self.erros = dict(erros)
        super().__init__("; ".join(self.erros.values()))


class ErroRegraNegocio(Exception):
    """Operação válida no formato, mas proibida pelas regras de negócio."""
