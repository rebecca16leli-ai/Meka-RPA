import csv
import tempfile
from pathlib import Path
from api.db import db
from flask import Blueprint, jsonify, render_template, request
from api.models import Fornecedores
from api.ia import ler_documento
import re
from os import path
from json import dumps

bp = Blueprint("main", __name__)

def register_routes(app) -> None:
    app.register_blueprint(bp)

@bp.route("/", methods=["GET"])
def ui() -> str:
    return render_template("index.html")

@bp.route("/condominios", methods=["GET"])
def condominios() -> tuple:
    csv_path = Path(__file__).resolve().parents[1] / "data" / "condominios.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    itens = [
        {"nome": row.get("nome_almah") or row.get("nome") or "", "valor": row.get("nome_almah") or row.get("nome") or ""}
        for row in rows
        if (row.get("nome_almah") or row.get("nome") or "").strip()
    ]
    return jsonify(itens), 200

@bp.route("/fornecedores", methods=["POST"])
def getForns():
    forns = db.session.query(Fornecedores.codigo, Fornecedores.nome).select_from(Fornecedores).all()
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

@bp.route("/executar-lancamento", methods=["POST"])
def executar_lancamento_route() -> tuple:
    from api.services import executar_lancamento_json

    payload = request.get_json(silent=True) or {}
    arquivo = payload.get("arquivo")
    confirmar = bool(payload.get("confirmar", False))

    if not arquivo:
        return jsonify({"detail": "Campo 'arquivo' é obrigatório."}), 400

    resultado = executar_lancamento_json(arquivo, confirmar=confirmar)
    if not resultado.get("ok"):
        return jsonify({"detail": resultado.get("erro")}), 400

    return jsonify(resultado), 200

@bp.route("/processar", methods=["POST"])
def processar() -> tuple:
    condominio = request.form.get("condominio", "").strip()
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
    
    extracao = dict()
    try:
        pdfs = sorted(str(p) for p in pasta.glob("*.pdf"))
        dados = []
        for pdf in pdfs:
            nomee = path.basename(pdf)
            nome = path.splitext(nomee)[0]
            nomef = nome.split("-")
            if len(nomef) > 1: nome = nomef[1]
            
            nome = (
                nome
                .replace("BOLETO","")
                .replace("HOLERITE","")
                .replace("COMPROVANTE","")
                .replace("RECIBO","")
                .replace("NF","")
                .replace(",","")
                .replace(".","")
                .replace(".pdf","")
                .replace("pdf","")
            )
            nome = re.sub(r'\d+', '', nome).strip()
            
            queryNome = Fornecedores.query.all()
            for item in queryNome: 
                if nome in item.nome: query = item; break
            
            dados.append({
                "fornecedor": query.nome,
                "fornecedor_id": query.id,
                "pdf": pdf,
                "condominio": condominio
            })

        print("="*50)
        print("Lendo dados com IA")
        extracao = ler_documento(dados)
        print(dumps(extracao, indent=4, ensure_ascii=False))
        print("="*50)

        resultado = {
            "ok": True,
            "message": "Pré-processamento concluído; o fluxo do robô será iniciado com os dados extraídos.",
            "data": extracao
        }
    except Exception as exc: return jsonify({"ok": False, "detail": str(exc)}), 500
    return jsonify(resultado), 200


