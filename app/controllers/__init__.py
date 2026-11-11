"""Camada CONTROLLER: recebe as requisições, aciona os Models e escolhe a View."""


def registrar_blueprints(app):
    from .auth_controller import bp as auth_bp
    from .catalogo_controller import bp as catalogo_bp
    from .marca_controller import bp as marca_bp
    from .painel_controller import bp as painel_bp
    from .proposta_controller import bp as proposta_bp
    from .veiculo_controller import bp as veiculo_bp
    from .venda_controller import bp as venda_bp

    for bp in (catalogo_bp, auth_bp, painel_bp, veiculo_bp, marca_bp, proposta_bp, venda_bp):
        app.register_blueprint(bp)
