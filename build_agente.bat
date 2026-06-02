@echo off
echo ==========================================
echo Gerando EXE - Agente XML Portal do Contador
echo ==========================================

call .venv\Scripts\activate.bat

echo.
echo Instalando dependencias...
python -m pip install --upgrade pyinstaller ttkbootstrap requests

echo.
echo Limpando build antigo...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Gerando painel visual do agente...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --windowed ^
  --name AgenteXMLPortalContador ^
  --paths agente_local ^
  agente_local\app_agente.py

echo.
echo Gerando executor agendado...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --console ^
  --name AgenteXMLRunner ^
  --paths agente_local ^
  agente_local\enviar_xmls.py

echo.
echo Copiando configuracoes...
if not exist dist\AgenteXMLPortalContador\agente_local mkdir dist\AgenteXMLPortalContador\agente_local

copy agente_local\config_agente.json dist\AgenteXMLPortalContador\config_agente.json
copy agente_local\historico_envio.json dist\AgenteXMLPortalContador\historico_envio.json

echo.
echo Criando pastas...
if not exist dist\AgenteXMLPortalContador\logs mkdir dist\AgenteXMLPortalContador\logs

echo.
echo Copiando runner para dentro da pasta principal...
xcopy dist\AgenteXMLRunner dist\AgenteXMLPortalContador\AgenteXMLRunner /E /I /Y

echo.
echo ==========================================
echo EXE gerado em:
echo dist\AgenteXMLPortalContador
echo ==========================================
pause