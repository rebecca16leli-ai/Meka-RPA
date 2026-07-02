@echo off
chcp 65001 >nul
title Meka - Gravar Login do Almah
cd /d "%~dp0"
if not exist "venv\Scripts\activate.bat" (
  echo [ERRO] O programa ainda nao foi instalado. Rode INSTALAR.bat primeiro.
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
echo ============================================================
echo   GRAVAR LOGIN DO ALMAH
echo   1) Vai abrir o navegador.
echo   2) Faca login, escolha um condominio e ENTRE no sistema.
echo   3) Quando a tela inicial do Almah carregar, volte aqui
echo      e pressione ENTER.
echo ============================================================
echo.
python -m automation.login
pause
