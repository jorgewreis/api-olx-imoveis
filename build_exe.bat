@echo off
cd /d "%~dp0"
echo Instalando dependencias...
python -m pip install -r requirements.txt -q
echo Gerando OlxImoveis.exe ...
python -m PyInstaller build/olx_imoveis.spec --noconfirm
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Sucesso: dist\OlxImoveis.exe
) else (
    echo Falha no build. Verifique se Python e PyInstaller estao instalados.
)
pause
