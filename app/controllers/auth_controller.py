from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from ..models import Usuario
from ..seguranca import destino_seguro

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        return redirect(url_for("painel.index"))

    if request.method == "POST":
        email = request.form.get("email", "")
        usuario = Usuario.autenticar(email, request.form.get("senha", ""))
        if usuario is None:
            flash("E-mail ou senha incorretos.", "erro")
            return render_template("auth/login.html", email=email), 401

        session.clear()
        session["usuario_id"] = usuario.id
        flash(f"Bem-vindo(a), {usuario.nome}!", "sucesso")
        return redirect(destino_seguro(request.args.get("proximo")) or url_for("painel.index"))

    return render_template("auth/login.html", email="")


@bp.post("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("catalogo.index"))
