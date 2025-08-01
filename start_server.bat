@echo off
echo Iniciando el servidor de la Trading App...
call venv\Scripts\activate.bat
uvicorn main:app --host 0.0.0.0
pause