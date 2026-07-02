from __future__ import annotations
from flask import Flask, jsonify
from flask_cors import CORS
from api.routes import register_routes
from dotenv import load_dotenv
from api.db import db
from os import getenv
from sqlalchemy import event
from sqlalchemy.engine import Engine
from threading import Thread

load_dotenv()

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["JSON_SORT_KEYS"] = False
    CORS(app, allow_headers="*")  # Carrega os CORS security
    app.config["SECRET_KEY"] = getenv("SECRET")
    app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")
    register_routes(app)
    return app

app = create_app()
db.init_app(app)
with app.app_context(): db.create_all()  # Cria as tabelas

@event.listens_for(Engine, "connect")
def ativar_case_insensitive(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # Força o LIKE do SQLite a ser case-insensitive para tudo
    cursor.execute("PRAGMA case_sensitive_like = OFF;")
    cursor.close()

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000, debug=True)