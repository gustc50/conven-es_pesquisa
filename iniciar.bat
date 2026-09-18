@echo off
setlocal
title Buscador de Convencao Coletiva
cd /d "%~dp0"

set PYEXE=

where py >nul 2>nul
if not errorlevel 1 (
    set PYEXE=py
    goto python_ok
)

where python >nul 2>nul
if not errorlevel 1 (
    set PYEXE=python
    goto python_ok
)

echo.
echo [ERRO] Python nao foi encontrado neste computador.
echo Instale o Python em https://www.python.org/downloads/
echo e marque a opcao "Add python.exe to PATH" durante a instalacao.
echo Depois, execute este arquivo novamente.
echo.
pause
exit /b 1

:python_ok
if not exist venv (
    echo Criando ambiente virtual Python...
    %PYEXE% -m venv venv
)

call venv\Scripts\activate.bat

echo Instalando dependencias (pode levar um minuto na primeira vez)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if not exist venv\.chromium_instalado (
    echo Baixando o navegador usado na busca automatica...
    echo Isso acontece so na primeira vez e pode levar alguns minutos.
    python -m playwright install chromium
    if not errorlevel 1 echo ok> venv\.chromium_instalado
)

echo.
echo Iniciando o Buscador de Convencao Coletiva...
echo O navegador sera aberto automaticamente em instantes.
echo Para encerrar, feche esta janela.
echo.
python app.py

echo.
pause
