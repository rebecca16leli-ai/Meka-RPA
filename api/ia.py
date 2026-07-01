from openai import OpenAI
import json
import pandas as pd
from prompt import PROMPT
from os import path, getcwd
from dotenv import load_dotenv
from rapidfuzz import process

load_dotenv()

client = OpenAI()

def match_fornecedor(nome_arquivo):
    csv_path = path.join(getcwd(), "data", "fornecedores.csv")
    df = pd.read_csv(csv_path)

    choices = list(df[["nome_almah", "codigo"]].itertuples(index=False, name=None))
    # formato: [("CLARO", 123), ("COPEL", 456)]

    best = process.extractOne(
        nome_arquivo, choices, processor=lambda x: x[0]  # compara só pelo nome
    )

    if best:
        (nome, codigo), score, _ = best
        return nome, codigo, score

    return None, None, 0


def ler_documentos(pdf):
    match = match_fornecedor(pdf)
    print(match)

    content = [
        {"type": "input_text", "text": PROMPT.replace("[FORNECEDORES]", str(match))}
    ]

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
    resultado = ler_documentos("pdfs/BOLETO CLARO.pdf")

    print(json.dumps(resultado, indent=4, ensure_ascii=False))
