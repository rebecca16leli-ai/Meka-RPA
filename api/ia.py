from openai import OpenAI
import json
import pandas as pd
from api.prompt import PROMPT
from os import path, getcwd
from dotenv import load_dotenv
from rapidfuzz import process, fuzz
from api.db import db
from api.models import Fornecedores
load_dotenv()

client = OpenAI()

def match_fornecedor(nome_sujo, fornecedores, threshold=95):
    nome_sujo = nome_sujo.upper().strip()

    resultado = process.extractOne(nome_sujo, fornecedores.keys(), scorer=fuzz.token_sort_ratio)
    if resultado and resultado[1] >= threshold:
        nome_match, score, _ = resultado
        return fornecedores[nome_match], nome_match, score
    return 0, None, 0


def ler_documento(dados):

    content = [
        {"type": "input_text", "text": PROMPT.replace("[FORNECEDOR]", str(dados))}
    ]

    for item in dados:
        pdf = item["pdf"]
        arquivo = client.files.create(file=open(pdf, "rb"), purpose="assistants")
        content.append({"type": "input_file", "file_id": arquivo.id})

    response = client.responses.create(
        model="gpt-5",
        input=[
            {"role": "user", "content": content},
        ],
        text={"format": {"type": "json_object"}},
    )

    return json.loads(response.output_text)


if __name__ == "__main__":
    resultado = ler_documento("pdfs/BOLETO CLARO.pdf")

    print(json.dumps(resultado, indent=4, ensure_ascii=False))
