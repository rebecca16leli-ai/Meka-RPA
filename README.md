# Automação Almah x Meka — Esqueleto (Fase 1)

Automação programática (Playwright) para lançar Contas a Pagar no Sistema Almah,
com **validação obrigatória do condomínio ativo** antes de qualquer escrita.

> Esta entrega é o **esqueleto da Fase 1** (fundação + núcleo de validação de
> condomínio). Passos como Contas a Pagar, recorrência, anexos e salvamento estão
> mapeados na arquitetura e marcados como `TODO` até a coleta dos seletores.

## Princípios

- Sem cliques por coordenada; só seletores robustos (id, role, texto), centralizados.
- Sessão por **login manual único** (`storage_state`). A automação **nunca** digita credenciais.
- Estado confirmado por **dois sinais**: DOM + (opcional) resposta XHR.
- A URL do Almah é sempre a mesma → **não** é usada para validar estado.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env        # edite ALMAH_BASE_URL
```

## Passo 1 — Login uma vez (você autentica)

```bash
python -m automation.login
```

Abre o navegador; **você** faz login; pressione ENTER para gravar a sessão em
`data/auth_state.json`. Repita só quando a sessão expirar.

## Passo 2 — Validar condomínio (núcleo R1)

```bash
python -m worker.runner --condominio "NOME EXATO NO ALMAH"
```

Códigos de saída: `0` ok · `2` sessão expirada · `3` seletor ausente (`TODO`) ·
`4` parada de segurança (condomínio divergente).

## Passo 3 — Rodar um lançamento (PRÉVIA / dry-run)

O fluxo completo lê um lançamento já aprovado (JSON) e executa no Almah. Por
segurança, **por padrão é dry-run**: preenche tudo, valida o total e **PARA antes
de salvar**, gerando prints em `evidence/` para você conferir.

```bash
python -m worker.lancar --arquivo data/exemplo_lancamento.json
```

Confira os prints em `evidence/`. Se estiver tudo certo, aí sim salve de verdade:

```bash
python -m worker.lancar --arquivo data/exemplo_lancamento.json --confirmar
```

Antes de rodar: coloque os PDFs do exemplo em `data/pdfs/` (boleto, comprovante, NF)
com os nomes que estão no `data/exemplo_lancamento.json`, ou ajuste os caminhos no JSON.

Códigos de saída: `0` ok · `2` sessão · `3` seletor ausente · `4` condomínio
divergente · `5` total divergente · `6` competência ambígua (revisão) · `7`
recorrência não encontrada.

## Onde preencher o que falta

Tudo em **`core/config/selectors.yaml`**. Procure por `status: TODO`. O mais
crítico é `condominio.nome_ativo` (nome do condomínio no topo da tela principal),
sem o qual a validação R1 não roda.

## Estrutura

```
automation/          Playwright: browser, login, Page Objects
  pages/condominio_page.py   <- núcleo da validação R1
core/config/         settings + selectors.yaml (central)
core/db/             SQLite (schema + repositório)
core/domain/         regras (normalização de nomes, etc.)
core/logging/        logs + evidências (prints)
extraction/          OCR/extração (Fase 2, contrato)
worker/runner.py     execução em processo separado da UI
api/                 API local para iniciar o bot
tests/               testes que não dependem de navegador
```

## Testes

```bash
pytest -q
```

## API Local

A API local expõe endpoints para iniciar a automação e validar o condomínio.

- `POST /api/validar-condominio` com body `{ "condominio": "NOME EXATO" }`
- `POST /api/executar-lancamento` com body `{ "arquivo": "caminho/para/lancamento.json", "confirmar": false }`

Inicie o servidor com:

```bash
uvicorn api.app:app --reload
```


