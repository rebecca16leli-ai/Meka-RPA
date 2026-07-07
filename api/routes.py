import tempfile
from pathlib import Path
from pandas import read_csv
from api.db import db
from flask import Blueprint, jsonify, render_template, request
from api.models import Fornecedores
from api.ia import ler_documento
import re
from os import path
from json import dumps
from api.services import executar_lancamento_json
from api.models import Condominios

bp = Blueprint("main", __name__)

def register_routes(app) -> None: app.register_blueprint(bp)

@bp.route("/", methods=["GET"])
def ui() -> str:
    return render_template("index.html")


@bp.route("/condominios", methods=["GET"])
def condominios() -> tuple:
    conds = db.session.query(Condominios.nome).all()
    return jsonify([c._asdict() for c in conds]), 200

@bp.route("/fornecedores", methods=["POST"])
def getForns():
    forns = (
        db.session.query(Fornecedores.codigo, Fornecedores.nome)
        .select_from(Fornecedores)
        .all()
    )
    return jsonify([f._asdict() for f in forns]), 200


@bp.route("/validar-condominio", methods=["POST"])
def validar_condominio_route() -> tuple:
    from api.services import validar_condominio

    payload = request.get_json(silent=True) or {}
    condominio = payload.get("condominio")

    if not condominio:
        return jsonify({"detail": "Campo 'condominio' é obrigatório."}), 400

    resultado = validar_condominio(condominio)
    if not resultado.get("ok"):
        return jsonify({"detail": resultado.get("erro")}), 400

    return jsonify(resultado), 200

# Use para testes evita gasto com Token
# com 1 arquivo
# extracao = {'documentos': [{'condominio': 'COND. EDF. ANDARAI', 'fornecedor_codigo': 226, 'fornecedor_nome': 'ARTGAZ COMERCIO DE GAS LTDA', 'competencia': '05/2026', 'documento_referencia': 'REF. 05/2026', 'valor_liquido': 409.38, 'vencimento': '10/06/2026', 'prev_pagto': None, 'emissao': '27/05/2026', 'anexos': ['C:\\Users\\Guilherme\\Documents\\Meka-RPA\\data\\pdfs\\meka_upload_t28jsucn\\BOLETO - ARTGAZ.pdf']}]}

# com 2 arquivos
# extracao = {'documentos': [{'condominio': 'COND. EDF. ANDARAI', 'fornecedor_codigo': 226, 'fornecedor_nome': 'ARTGAZ COMERCIO DE GAS LTDA', 'competencia': '05/2026', 'documento_referencia': 'REF. 05/2026', 'valor_liquido': 409.38, 'vencimento': '10/06/2026', 'prev_pagto': None, 'emissao': '27/05/2026', 'anexos': ['C:\\Users\\Guilherme\\Documents\\Meka-RPA\\data\\pdfs\\meka_upload_6wzqhfqt\\BOLETO - ARTGAZ.pdf']}, {'condominio': 'CONDOMINIO EDIFICIO ANDARARI', 'fornecedor_codigo': 335, 'fornecedor_nome': 'CLARO NXT TELECOMUNICACOES S/A', 'competencia': '04/2026', 'documento_referencia': 'REF. 04/2026', 'valor_liquido': 74.9, 'vencimento': '10/05/2026', 'prev_pagto': None, 'emissao': '22/04/2026', 'anexos': ['C:\\Users\\Guilherme\\Documents\\Meka-RPA\\data\\pdfs\\meka_upload_6wzqhfqt\\BOLETO CLARO.pdf']}]}

@bp.route("/processar", methods=["POST"])
def processar() -> tuple:
    condominio = request.form.get("condominio").strip()
    arquivos = request.files.getlist("files")
    if not arquivos: return jsonify({"ok": False, "detail": "Selecione ao menos um PDF."}), 400

    pasta_base = Path(__file__).resolve().parents[1] / "data" / "pdfs"
    pasta_base.mkdir(parents=True, exist_ok=True)
    pasta = Path(tempfile.mkdtemp(prefix="meka_upload_", dir=str(pasta_base)))

    nomes = []
    for upload in arquivos:
        if upload.filename:
            destino = pasta / upload.filename
            upload.save(destino)
            nomes.append(destino.name)

    try:
        pdfs = sorted(str(p) for p in pasta.glob("*.pdf"))
        dados = []
        for pdf in pdfs:
            nomee = path.basename(pdf)
            nome = path.splitext(nomee)[0]
            nomef = nome.split("-")
            if len(nomef) > 1:
                nome = nomef[1]

            nome = (
                nome.replace("BOLETO", "")
                .replace("HOLERITE", "")
                .replace("COMPROVANTE", "")
                .replace("FATURA", "")
                .replace("RECIBO", "")
                .replace("NF", "")
                .replace(",", "")
                .replace(".", "")
                .replace(".pdf", "")
                .replace("pdf", "")
            )

            query = None
            nome = re.sub(r"\d+", "", nome).strip()
            queryNome = Fornecedores.query.filter(Fornecedores.nome.contains(nome)).all()
            for item in queryNome: query = item if nome in item.nome else None
            if not query: return jsonify({"ok": False, "detail": "Fornecedor não encontrado"}), 404
            dados.append({ "fornecedor": query.nome, "fornecedor_id": query.id, "arquivo": pdf })
            
        extracao = ler_documento(dados)
        print("-"*50)
        print("INFO: Extração da IA: >> ")
        print(extracao)
        print("-"*50)
        print("Iniciando a automação")
        resultado = executar_lancamento_json(extracao, condominio=condominio)
        print("Automação finalizada")
        return jsonify({"ok":True, "message": "Sucesso com a automação", "res": resultado}), 200
    except Exception as exc: return jsonify({"ok": False, "detail": str(exc)}), 500
