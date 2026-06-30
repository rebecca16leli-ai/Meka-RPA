# Dados do projeto (seed)

Tabelas geradas a partir dos relatórios do Almah (15/05 e 04/06/2026).

| Arquivo | Origem | Status |
|---|---|---|
| `condominios.csv` | Relatório de Condomínios | **Conferido** — 27 condomínios, nomes exatos. Preencha `nome_pasta` com o nome da pasta local de cada um. |
| `fornecedores.csv` | Relatório de Fornecedores | Auto-extraído — ~1.295 fornecedores (código, CNPJ, nome). **Conferir antes da Fase 6** (a extração de 156 páginas pode ter pulado/mesclado alguns nomes). |
| `fornecedor_contas.csv` | Relatório de Fornecedores | Auto-extraído — vínculo fornecedor → contas (código reduzido + descrição). Muitos fornecedores têm várias contas. |
| `fornecedor_config.csv` | Preenchido manualmente | **De-para que o relatório NÃO tem**: conta padrão, tipo de documento e descrição-padrão por fornecedor. Hoje só a ARTGAZ (MVP). Expandir conforme necessário. |

## Regra da Conta (importante)

A Conta é escolhida pelo `conta_padrao_reduzido` de `fornecedor_config.csv`.
- Se o fornecedor não estiver em `fornecedor_config.csv` mas tiver **uma única** conta em `fornecedor_contas.csv` → usa essa.
- Se tiver **várias** contas e não houver padrão definido → marca o lançamento como **revisão** (não escolhe sozinho).

## MVP

Fornecedor de teste: **ARTGAZ COMERCIO DE GAS LTDA** (0664) → conta GÁS (40102010003),
documento NF, descrição-padrão "REABASTECIMENTO DE GÁS". O complemento final fica
"REABASTECIMENTO DE GÁS REF. MM/AAAA" (descrição-padrão + competência).
