import os

from flask import Flask

from .config import SECRET_KEY_DESENVOLVIMENTO, Config
from .extensions import db


def _conferir_configuracao(app):
    """Impede subir em produção com a chave de sessão de desenvolvimento.

    Sem isso, quem tiver acesso ao repositório consegue assinar cookies de
    sessão válidos e entrar no painel como qualquer usuário.
    """
    if app.config["AMBIENTE"] != "producao":
        if app.config["SECRET_KEY"] == SECRET_KEY_DESENVOLVIMENTO and not app.config.get("TESTING"):
            app.logger.warning(
                "SECRET_KEY de desenvolvimento em uso. Defina a variável de ambiente "
                "SECRET_KEY antes de publicar a aplicação."
            )
        return
    if app.config["SECRET_KEY"] == SECRET_KEY_DESENVOLVIMENTO:
        raise RuntimeError(
            "AUTOVENDA_AMBIENTE=producao exige a variável de ambiente SECRET_KEY "
            "com um valor próprio e secreto. Gere uma com: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="views/templates",
        static_folder="views/static",
    )
    app.config.from_object(config_class)
    _conferir_configuracao(app)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    from . import cli, seguranca
    from .controllers import registrar_blueprints
    from .controllers.erro_controller import registrar_tratadores
    from .views import filtros

    seguranca.init_app(app)
    filtros.registrar(app)
    registrar_blueprints(app)
    registrar_tratadores(app)
    cli.registrar(app)

    with app.app_context():
        db.create_all()

    return app
