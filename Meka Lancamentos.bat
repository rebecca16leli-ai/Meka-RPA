@echo off
chcp 65001 >nul
title Meka - Lancamentos Almah
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo [ERRO] O programa ainda nao foi instalado nesta maquina.
  echo Rode primeiro o arquivo INSTALAR.bat
  echo.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo Abrindo o painel no navegador... (NAO FECHE esta janela enquanto usar o painel)
echo Para encerrar, feche esta janela.
streamlit run app/main.py
