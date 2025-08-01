@echo off
echo Configurando el entorno del servidor...
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo.
echo ¡Configuración completa!
pause