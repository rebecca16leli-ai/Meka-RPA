from openai import OpenAI
from api.prompt import PROMPT
from rapidfuzz import process, fuzz
from json import loads
from core.config.settings import settings

def match_fornecedor(nome_sujo, fornecedores, threshold=95):
    nome_sujo = nome_sujo.upper().strip()
    resultado = process.extractOne(nome_sujo, fornecedores.keys(), scorer=fuzz.token_sort_ratio)
    if resultado and resultado[1] >= threshold:
        nome_match, score, _ = resultado
        return fornecedores[nome_match], nome_match, score
    return 0, None, 0

def ler_documento(dados):
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY nao configurada no arquivo .env.")

    client = OpenAI(api_key=settings.openai_api_key)
    content = [{"type": "input_text", "text": PROMPT.replace("[FORNECEDOR]", str(dados))}]
    file_ids = []
    try:
        for item in dados:
            pdf = item["arquivo"]
            with open(pdf, "rb") as arquivo_pdf:
                arquivo = client.files.create(file=arquivo_pdf, purpose="assistants")
            file_ids.append(arquivo.id)
            content.append({"type": "input_file", "file_id": arquivo.id})

        response = client.responses.create(
            model="gpt-5",
            input=[{"role": "user", "content": content}],
            text={"format": {"type": "json_object"}},
        )
        return loads(response.output_text)
    finally:
        for file_id in file_ids:
            try:
                client.files.delete(file_id)
            except Exception:
                pass
