import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, g, redirect, request, session, url_for
from markupsafe import Markup

from .extensions import db
from .models import Usuario


def gerar_csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def campo_csrf():
    return Markup(f'<input type="hidden" name="csrf_token" value="{gerar_csrf_token()}">')


def destino_seguro(destino):
    """Evita open redirect: só aceita caminhos internos da aplicação."""
    if not destino:
        return None
    partes = urlparse(destino)
    if partes.scheme or partes.netloc or not destino.startswith("/") or destino.startswith("//"):
        return None
    return destino


def exigir_login():
    """Usado como before_request nos blueprints do painel."""
    if g.usuario is None:
        flash("Faça login para acessar a área administrativa.", "aviso")
        return redirect(url_for("auth.login", proximo=request.full_path.rstrip("?")))
    return None


def somente_admin(view):
    @wraps(view)
    def envolvida(*args, **kwargs):
        if g.usuario is None or not g.usuario.eh_admin:
            abort(403)
        return view(*args, **kwargs)

    return envolvida


def init_app(app):
    @app.before_request
    def carregar_usuario():
        usuario_id = session.get("usuario_id")
        g.usuario = db.session.get(Usuario, usuario_id) if usuario_id else None
        if g.usuario is not None and not g.usuario.ativo:
            session.clear()
            g.usuario = None

    @app.before_request
    def verificar_csrf():
        if not app.config.get("CSRF_ENABLED"):
            return
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            enviado = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
            esperado = session.get("_csrf", "")
            if not esperado or not secrets.compare_digest(enviado, esperado):
                abort(400, description="Sua sessão expirou. Recarregue a página e tente novamente.")

    @app.after_request
    def cabecalhos_seguranca(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "same-origin")
        return resposta

    app.jinja_env.globals["csrf_token"] = gerar_csrf_token
    app.jinja_env.globals["campo_csrf"] = campo_csrf
