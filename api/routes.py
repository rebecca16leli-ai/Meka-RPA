from __future__ import annotations

import csv
from ctypes import resize
import json
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request


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

    if not arquivos:
        return jsonify({"ok": False, "detail": "Selecione ao menos um PDF."}), 400

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
        from extraction.extractor import extrair

        pdfs = sorted(str(p) for p in pasta.glob("*.pdf"))
        extracao = extrair(pdfs) if pdfs else None
        resultado = {
            "ok": True,
            "message": "Pré-processamento concluído; o fluxo do robô será iniciado com os dados extraídos.",
            "condominio": condominio,
            "arquivos": nomes,
            "pasta": str(pasta),
            "dados": {
                "valor": extracao.valor if extracao else None,
                "vencimento": extracao.vencimento if extracao else None,
                "emissao": extracao.emissao if extracao else None,
                "numero_nf": extracao.numero_nf if extracao else None,
                "competencia_sugerida": extracao.competencia_sugerida if extracao else None,
                "confiavel": extracao.confiavel if extracao else None,
                "avisos": extracao.avisos if extracao else [],
                "fontes": extracao.fontes if extracao else {},
            },
        }
        print(resultado)
    except Exception as exc:
        return jsonify({"ok": False, "detail": str(exc)}), 500

    return jsonify(resultado), 200
