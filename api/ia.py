from openai import OpenAI
from api.prompt import PROMPT
from rapidfuzz import process, fuzz
from json import loads
from core.config.settings import settings

client = OpenAI(api_key=settings.openai_api_key)

def match_fornecedor(nome_sujo, fornecedores, threshold=95):
    nome_sujo = nome_sujo.upper().strip()
    resultado = process.extractOne(nome_sujo, fornecedores.keys(), scorer=fuzz.token_sort_ratio)
    if resultado and resultado[1] >= threshold:
        nome_match, score, _ = resultado
        return fornecedores[nome_match], nome_match, score
    return 0, None, 0

def ler_documento(dados):
    content = [{"type": "input_text", "text": PROMPT.replace("[FORNECEDOR]", str(dados))},]
    for item in dados:
        pdf = item["arquivo"]
        arquivo = client.files.create(file=open(pdf, "rb"), purpose="assistants")
        content.append({"type": "input_file", "file_id": arquivo.id})

    response = client.responses.create(
        model="gpt-5",
        input=[
            {"role": "user", "content": content},
        ],
        text={"format": {"type": "json_object"}},
    )

    return loads(response.output_text)