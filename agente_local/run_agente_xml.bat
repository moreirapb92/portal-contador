@echo off
cd /d "C:\Users\NONATO\Documents\portalcontador"

if not exist "agente_local\logs" mkdir "agente_local\logs"

echo ================================================ >> "C:\Users\NONATO\Documents\portalcontador\agente_local\logs\agendador_agente.log"
echo Iniciando envio agendado em %date% %time% >> "C:\Users\NONATO\Documents\portalcontador\agente_local\logs\agendador_agente.log"
echo ================================================ >> "C:\Users\NONATO\Documents\portalcontador\agente_local\logs\agendador_agente.log"

"C:\Users\NONATO\Documents\portalcontador\.venv\Scripts\python.exe" "C:\Users\NONATO\Documents\portalcontador\agente_local\enviar_xmls.py" >> "C:\Users\NONATO\Documents\portalcontador\agente_local\logs\agendador_agente.log" 2>&1

echo ================================================ >> "C:\Users\NONATO\Documents\portalcontador\agente_local\logs\agendador_agente.log"
echo Envio agendado finalizado em %date% %time% >> "C:\Users\NONATO\Documents\portalcontador\agente_local\logs\agendador_agente.log"
echo ================================================ >> "C:\Users\NONATO\Documents\portalcontador\agente_local\logs\agendador_agente.log"
echo. >> "C:\Users\NONATO\Documents\portalcontador\agente_local\logs\agendador_agente.log"
