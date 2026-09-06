from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request
from werkzeug.utils import secure_filename

from api.db import db
from api.ia import ler_documento
from api.models import Condominios, Fornecedores
from api.services import executar_lancamento_json
from automation.pages.contas_pagar_page import fornecedor_e_copel, fornecedor_e_sanepar
from core.config.settings import settings
from core.logging.logger import get_logger

bp = Blueprint("main", __name__)
log = get_logger("routes")


def register_routes(app) -> None:
    app.register_blueprint(bp)


@bp.route("/", methods=["GET"])
def ui() -> str:
    return render_template("index.html", dry_run=settings.dry_run)


@bp.route("/condominios", methods=["GET"])
def condominios() -> tuple:
    conds = db.session.query(Condominios.id, Condominios.nome).all()
    return jsonify([c._asdict() for c in conds]), 200


@bp.route("/fornecedores", methods=["POST"])
def fornecedores() -> tuple:
    itens = db.session.query(Fornecedores.codigo, Fornecedores.nome).all()
    return jsonify([item._asdict() for item in itens]), 200


@bp.route("/validar-condominio", methods=["POST"])
def validar_condominio_route() -> tuple:
    from api.services import validar_condominio

    payload = request.get_json(silent=True) or {}
    condominio = str(payload.get("condominio") or "").strip()
    if not condominio:
        return jsonify({"detail": "Campo 'condominio' e obrigatorio."}), 400

    resultado = validar_condominio(condominio)
    if not resultado.get("ok"):
        return jsonify({"detail": resultado.get("erro")}), 400
    return jsonify(resultado), 200


def _nome_fornecedor(nome_arquivo: str) -> str:
    nome = Path(nome_arquivo).stem.upper()
    nome = re.sub(r"[\W_]+", " ", nome, flags=re.UNICODE)
    termos_documento = (
        "BOLETO",
        "HOLERITE",
        "COMPROVANTE",
        "FATURA",
        "RECIBO",
        "NOTA FISCAL",
        "NF",
    )
    for termo in termos_documento:
        nome = re.sub(rf"\b{re.escape(termo)}\b", " ", nome)

    # Remove sufixos de copia como _2 e transforma _, hifens e pontuacao
    # em espacos. Ex.: FATURA_-_COPEL_2.pdf -> COPEL.
    nome = re.sub(r"\d+", " ", nome)
    return re.sub(r"\s+", " ", nome).strip()


def _localizar_fornecedor(nome: str) -> Fornecedores | None:
    if not nome:
        return None
    candidatos = Fornecedores.query.filter(Fornecedores.nome.contains(nome)).all()
    return next(
        (item for item in candidatos if nome.casefold() in item.nome.casefold()),
        None,
    )


def _erro_item(nome_arquivo: str, mensagem: str, indice: int) -> dict:
    return {
        "indice": indice,
        "ok": False,
        "status": "erro",
        "mensagem": mensagem,
        "fornecedor": "Fornecedor nao identificado",
        "referencia": "",
        "arquivos": [nome_arquivo],
        "evidencias": [],
    }


def _resumo_lote(itens: list[dict], evidencias: list[str] | None = None) -> dict:
    sucessos = sum(1 for item in itens if item.get("ok"))
    erros = len(itens) - sucessos
    return {
        "ok": erros == 0,
        "status": "concluido" if not erros else "parcial" if sucessos else "erro",
        "mensagem": f"Lote concluido: {sucessos} sucesso(s) e {erros} erro(s).",
        "total": len(itens),
        "sucessos": sucessos,
        "erros": erros,
        "itens": itens,
        "evidencias": evidencias or [],
    }


def _extrair_documentos_sem_agrupar_utilidades(dados: list[dict]) -> dict:
    """COPEL/SANEPAR sao processadas arquivo a arquivo por regra de negocio."""
    agrupaveis: list[dict] = []
    isolados: list[dict] = []
    for item in dados:
        fornecedor = item.get("fornecedor")
        destino = (
            isolados
            if fornecedor_e_copel(fornecedor) or fornecedor_e_sanepar(fornecedor)
            else agrupaveis
        )
        destino.append(item)
    documentos: list[dict] = []

    if agrupaveis:
        documentos.extend((ler_documento(agrupaveis) or {}).get("documentos", []))
    for item in isolados:
        # Uma chamada por arquivo impede agrupamento mesmo se o modelo ignorar
        # a instrucao textual do prompt.
        documentos.extend((ler_documento([item]) or {}).get("documentos", []))
    return {"documentos": documentos}


@bp.route("/processar", methods=["POST"])
def processar() -> tuple:
    condominio = request.form.get("condominio", "").strip()
    if not condominio:
        return jsonify({"ok": False, "detail": "Condominio nao informado."}), 400

    arquivos = [item for item in request.files.getlist("files") if item.filename]
    if not arquivos:
        return jsonify({"ok": False, "detail": "Selecione ao menos um PDF."}), 400

    pasta_base = settings.data_dir / "pdfs"
    pasta_base.mkdir(parents=True, exist_ok=True)
    pasta = Path(tempfile.mkdtemp(prefix="meka_upload_", dir=str(pasta_base)))

    try:
        pdfs: list[tuple[Path, str]] = []
        for indice, upload in enumerate(arquivos, start=1):
            nome_seguro = secure_filename(upload.filename or "")
            if not nome_seguro or Path(nome_seguro).suffix.lower() != ".pdf":
                return jsonify({"ok": False, "detail": "Envie somente arquivos PDF validos."}), 400
            destino = pasta / nome_seguro
            if destino.exists():
                destino = pasta / f"{indice:02d}_{nome_seguro}"
            upload.save(destino)
            pdfs.append((destino, upload.filename or nome_seguro))

        dados = []
        erros_arquivo: list[dict] = []
        for indice, (pdf, nome_original) in enumerate(pdfs, start=1):
            nome = _nome_fornecedor(nome_original)
            fornecedor = _localizar_fornecedor(nome)
            if fornecedor is None:
                erros_arquivo.append(_erro_item(
                    nome_original,
                    f"Fornecedor nao encontrado para o arquivo '{nome_original}'.",
                    indice,
                ))
                continue
            dados.append({
                "fornecedor": fornecedor.nome,
                "fornecedor_id": fornecedor.id,
                "arquivo": str(pdf),
            })

        if dados:
            log.info("Iniciando extracao de %d documento(s) com IA", len(dados))
            extracao = _extrair_documentos_sem_agrupar_utilidades(dados)
            log.info(f"A IA retornou:{json.dumps(extracao, indent=4)}")
            log.info("Extracao concluida; iniciando login e automacao em lote")
            resultado_automacao = executar_lancamento_json(extracao, cond=condominio)
            itens_automacao = resultado_automacao.get("itens", [])
            if not itens_automacao and not resultado_automacao.get("ok"):
                mensagem = (
                    resultado_automacao.get("mensagem")
                    or resultado_automacao.get("erro")
                    or "A IA nao retornou documentos validos para lancamento."
                )
                itens_automacao = [
                    _erro_item(Path(item["arquivo"]).name, mensagem, indice)
                    for indice, item in enumerate(dados, start=1)
                ]
            itens = itens_automacao + erros_arquivo
            resultado = _resumo_lote(
                itens,
                resultado_automacao.get("evidencias", []),
            )
        else:
            resultado = _resumo_lote(erros_arquivo)

        log.info("Automacao finalizada com status %s", resultado.get("status"))
        return jsonify({
            # A requisicao foi processada ate o fim mesmo quando alguns itens
            # exigem revisao. O estado individual fica em res.itens.
            "ok": True,
            "message": resultado.get("mensagem"),
            "res": resultado,
        }), 200
    except Exception as exc:
        log.exception("Falha no processamento")
        return jsonify({"ok": False, "detail": str(exc)}), 500
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
