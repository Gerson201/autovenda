import os
import tempfile
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

SECRET_KEY_DESENVOLVIMENTO = "dev-troque-esta-chave-em-producao"


class Config:
    # AUTOVENDA_AMBIENTE=producao faz a aplicação exigir SECRET_KEY própria
    # e marcar o cookie de sessão como Secure (ver app/__init__.py).
    AMBIENTE = os.environ.get("AUTOVENDA_AMBIENTE", "desenvolvimento").strip().lower()

    SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY_DESENVOLVIMENTO)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "autovenda.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "views", "static", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB por requisição
    EXTENSOES_IMAGEM = {"jpg", "jpeg", "png", "webp"}

    ITENS_POR_PAGINA_CATALOGO = 9
    ITENS_POR_PAGINA_ADMIN = 15

    CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = AMBIENTE == "producao"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Freio de força bruta no login (janela deslizante em memória).
    LOGIN_MAX_TENTATIVAS = 5
    LOGIN_JANELA_MINUTOS = 10
    LOGIN_BLOQUEIO_MINUTOS = 15


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    UPLOAD_FOLDER = tempfile.mkdtemp(prefix="autovenda-testes-")
    # Nos testes o freio de login fica frouxo para não interferir nos cenários
    # que fazem vários logins seguidos; há testes próprios que o exercitam.
    LOGIN_MAX_TENTATIVAS = 50
