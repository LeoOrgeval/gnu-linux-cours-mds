from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, redirect, render_template_string, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "change-me-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

USERS = {
    "admin": "admin123",
    "alice": "alice123",
}


def configure_logging() -> None:
    log_file = os.environ.get("APP_LOG_FILE", "/var/log/flask-auth/app.log")
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


configure_logging()


LOGIN_PAGE = """
<!doctype html>
<html lang="fr">
  <head><meta charset="utf-8"><title>Connexion</title></head>
  <body>
    <h1>Connexion</h1>
    {% if error %}<p style="color: red;">{{ error }}</p>{% endif %}
    <form method="post" action="/login">
      <label>Utilisateur: <input type="text" name="username" required></label><br>
      <label>Mot de passe: <input type="password" name="password" required></label><br>
      <button type="submit">Se connecter</button>
    </form>
  </body>
</html>
"""


@app.get("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template_string(LOGIN_PAGE, error=None)

    username = request.form.get("username", "")
    password = request.form.get("password", "")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()

    if USERS.get(username) == password:
        session["authenticated"] = True
        session["username"] = username
        app.logger.info("AUTH_OK ip=%s user=%s path=/login", ip, username)
        return redirect(url_for("private"))

    app.logger.warning("AUTH_FAIL ip=%s user=%s path=/login", ip, username)
    return render_template_string(LOGIN_PAGE, error="Identifiants invalides"), 401


@app.get("/private")
def private():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return "Acces au contenu prive autorise", 200


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
