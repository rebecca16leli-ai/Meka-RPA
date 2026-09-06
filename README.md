# Meka RPA - Almah

Aplicacao local em Flask + Playwright que le PDFs financeiros com IA e prepara
lancamentos de Contas a Pagar no Almah.

## Configuracao

Copie `.env.example` para `.env` e configure:

```dotenv
OPENAI_API_KEY=
ALMAH_USUARIO=
ALMAH_SENHA=
DRY_RUN=true
SLOW_MO_MS=2000
```

Em desenvolvimento, o arquivo fica na raiz do projeto. No executavel instalado,
ele tambem pode ficar em `%LOCALAPPDATA%\Meka RPA\.env`. Esse segundo local tem
precedencia e evita editar arquivos dentro de `Program Files`.

Nao versione nem envie o `.env`: ele contem a senha do portal.

## Fluxo

1. O usuario escolhe o condominio e envia um ou mais PDFs.
2. A IA extrai e valida os dados dos documentos.
3. Um contexto limpo do Chrome e aberto.
4. O robo faz login usando `ALMAH_USUARIO` e `ALMAH_SENHA`.
5. No mesmo contexto, seleciona o condominio, abre Contas a Pagar e prepara os
   lancamentos.
6. Por seguranca, a interface executa em modo de previa: preenche e valida, mas
   nao salva o lancamento quando `DRY_RUN=true`.

Para COPEL, a automacao pesquisa a recorrencia pelos quatro ultimos digitos da
unidade consumidora e monta a descricao como
`COPEL GERAL REF. MM/AAAA - 3642 KWH`. Se a IA nao localizar unidade consumidora
ou consumo em kWh, o lancamento e interrompido para revisao.

Para SANEPAR, a pesquisa usa a matricula completa e a descricao segue o formato
`SANEPAR GERAL REF. MM/AAAA - 22 M³`. Matricula e consumo em metros cubicos sao
obrigatorios para prosseguir.

Use `DRY_RUN=false` para permitir gravacao real. Reinicie o programa depois de
alterar o `.env`. A interface mostra uma faixa vermelha enquanto a gravacao real
estiver ativa.

`SLOW_MO_MS=2000` adiciona uma pausa de 2 segundos entre as acoes do navegador,
facilitando acompanhar a automacao e identificar visualmente onde ocorreu um erro.

## Sincronizacao do instalador com o MEGA

Configure no `.env` a pasta local sincronizada pelo MEGA Desktop:

```dotenv
MEGA_OUTPUT_DIR=%USERPROFILE%\Documents\MEGA\Meka-RPA\Output
```

Para copiar o `Output` imediatamente:

```powershell
.\scripts\sync_output_to_mega.ps1
```

Para monitorar alteracoes e iniciar automaticamente no logon do Windows:

```powershell
.\scripts\install_mega_output_watcher.ps1
```

O monitor espelha a pasta `Output` no destino configurado e grava o historico em
`%LOCALAPPDATA%\Meka RPA\logs\mega_sync.log`.

Nao existe mais dependencia de `auth_state.json` nem regravacao manual de login.

## Executar

```powershell
venv\Scripts\python.exe run.py
```

Validacao de login e condominio pela linha de comando:

```powershell
venv\Scripts\python.exe -m worker.runner --condominio "NOME EXATO"
```

Lancamento por JSON (previa por padrao):

```powershell
venv\Scripts\python.exe -m worker.lancar --arquivo dados.json --condominio "NOME EXATO"
```

Somente a entrada CLI permite salvar, e exige a opcao explicita `--confirmar`.

## Dados locais

- logs: `%LOCALAPPDATA%\Meka RPA\logs\execucao.log`
- banco: `%LOCALAPPDATA%\Meka RPA\instance\data.db`
- evidencias: `%LOCALAPPDATA%\Meka RPA\evidence`
- uploads: temporarios; sao removidos ao fim de cada processamento

As evidencias sao agrupadas por execucao e lancamento:

```text
evidence\20260713_203000_000000\
  00_execucao\
  01_CLARO_NXT_TELECOMUNICACOES_S_A_REF_04_2026\
  02_COPEL_DISTRIBUICAO_S_A_REF_05_2026\
```

Cada pasta de lancamento guarda a recorrencia selecionada, o formulario original,
o formulario preenchido e o resultado final. Erros geram uma evidencia `99_erro`.

## Validacao

```powershell
venv\Scripts\python.exe -m compileall -q app.py api automation core extraction worker run.py tests
venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
venv\Scripts\python.exe -m PyInstaller Meka_RPA.spec --noconfirm
```
