from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..models import Usuario
from ..models.util import texto
from ..seguranca import destino_seguro

bp = Blueprint("auth", __name__)


def _chave_tentativa(email):
    """Conta as falhas por e-mail + origem da requisição.

    Usar só o e-mail deixaria um atacante bloquear a conta de um vendedor de
    propósito; usar só o IP deixaria passar quem varre vários e-mails.
    """
    return (texto(email).lower(), request.remote_addr or "desconhecido")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        return redirect(url_for("painel.index"))

    if request.method == "POST":
        email = request.form.get("email", "")
        controle = current_app.extensions["tentativas_login"]
        chave = _chave_tentativa(email)

        segundos = controle.segundos_de_bloqueio(chave)
        if segundos:
            minutos = max(1, round(segundos / 60))
            flash(
                "Muitas tentativas de acesso com estes dados. "
                f"Aguarde cerca de {minutos} minuto(s) e tente novamente.",
                "erro",
            )
            return render_template("auth/login.html", email=email), 429

        usuario = Usuario.autenticar(email, request.form.get("senha", ""))
        if usuario is None:
            bloqueou = controle.registrar_falha(chave)
            if bloqueou:
                minutos = current_app.config["LOGIN_BLOQUEIO_MINUTOS"]
                flash(
                    "E-mail ou senha incorretos. Por segurança, novas tentativas com "
                    f"estes dados ficam bloqueadas por {minutos} minutos.",
                    "erro",
                )
                return render_template("auth/login.html", email=email), 429
            flash("E-mail ou senha incorretos.", "erro")
            return render_template("auth/login.html", email=email), 401

        controle.registrar_sucesso(chave)
        session.clear()
        session["usuario_id"] = usuario.id
        session.permanent = True  # aplica PERMANENT_SESSION_LIFETIME
        flash(f"Bem-vindo(a), {usuario.nome}!", "sucesso")
        return redirect(destino_seguro(request.args.get("proximo")) or url_for("painel.index"))

    return render_template("auth/login.html", email="")


@bp.post("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("catalogo.index"))
