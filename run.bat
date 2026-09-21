@echo off
REM LAND AI - quick start (Windows)
cd /d "%~dp0backend"

if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Starting LAND AI at http://127.0.0.1:5000
python app.py
pause
