from api.db import db

class Fornecedores(db.Model):
    __tablename__ = 'fornecedores'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String)
    codigo = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)