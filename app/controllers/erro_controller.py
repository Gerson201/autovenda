from flask import render_template

from ..extensions import db

PAGINAS_ERRO = {
    400: ("Requisição inválida", "Não foi possível processar o pedido."),
    403: ("Acesso negado", "Seu perfil não tem permissão para esta ação."),
    404: ("Página não encontrada", "O endereço acessado não existe ou o veículo não está mais à venda."),
    405: ("Método não permitido", "Esta ação não pode ser feita desta forma."),
    413: ("Arquivo muito grande", "O arquivo enviado ultrapassa o limite de 5 MB."),
    500: ("Erro interno", "Ocorreu um erro inesperado. Tente novamente em instantes."),
}


def _renderizar(codigo, descricao=None):
    titulo, mensagem = PAGINAS_ERRO[codigo]
    return (
        render_template("erros/erro.html", codigo=codigo, titulo=titulo, mensagem=descricao or mensagem),
        codigo,
    )


def registrar_tratadores(app):
    for codigo in (400, 403, 404, 405, 413):

        def tratador(erro, codigo=codigo):
            descricao = getattr(erro, "description", None) if codigo == 400 else None
            return _renderizar(codigo, descricao)

        app.register_error_handler(codigo, tratador)

    @app.errorhandler(500)
    def erro_interno(_erro):
        db.session.rollback()
        app.logger.exception("Erro interno não tratado")
        return _renderizar(500)
