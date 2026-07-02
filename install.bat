@echo off
chcp 65001 >nul
title Meka - Instalacao
cd /d "%~dp0"
echo ============================================================
echo   INSTALACAO DO MEKA - LANCAMENTOS ALMAH
echo   Isso prepara o programa nesta maquina. Roda so uma vez.
echo ============================================================
echo.

REM --- verifica Python ---
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado nesta maquina.
  echo Baixe e instale o Python 3.12 em https://www.python.org/downloads/
  echo IMPORTANTE: na instalacao, marque a caixa "Add Python to PATH".
  echo Depois rode este INSTALAR novamente.
  echo.
  pause
  exit /b 1
)
echo [OK] Python encontrado.

echo.
echo [1/4] Criando ambiente isolado (venv)...
if exist "venv" rmdir /s /q "venv"
python -m venv venv
if errorlevel 1 ( echo [ERRO] Falha ao criar o ambiente. & pause & exit /b 1 )

echo [2/4] Ativando ambiente...
call venv\Scripts\activate.bat

echo [3/4] Instalando bibliotecas (pode levar alguns minutos)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 ( echo [ERRO] Falha ao instalar bibliotecas. Verifique a internet. & pause & exit /b 1 )

echo [4/4] Baixando o navegador da automacao (Chromium)...
python -m playwright install chromium
if errorlevel 1 ( echo [ERRO] Falha ao baixar o navegador. & pause & exit /b 1 )

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo   Agora use o atalho "Meka Lancamentos" para abrir o painel.
echo   Na primeira vez, rode tambem "GRAVAR LOGIN" para entrar no Almah.
echo ============================================================
echo.
pause
