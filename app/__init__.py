import os

from flask import Flask

from .config import Config
from .extensions import db


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="views/templates",
        static_folder="views/static",
    )
    app.config.from_object(config_class)

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
