@echo off
REM Offline installer for the Engineering-Docs Assistant (Windows, Python 3.11)
REM Prerequisites installed from the "installers" folder: Python 3.11, Ollama, Tesseract OCR

python --version || (echo Install Python 3.11 first & exit /b 1)
python -m venv .venv
call .venv\Scripts\activate.bat
pip install --no-index --find-links wheels -r requirements.txt || (echo pip install failed & exit /b 1)

REM turn telemetry off
setx ANONYMIZED_TELEMETRY False
setx OLLAMA_NO_ANALYTICS 1

REM Ollama models: copy the models folder from the online machine to this path
setx OLLAMA_MODELS "%USERPROFILE%\.ollama\models"

if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" echo WARNING: Tesseract not found - OCR will be disabled
if not exist "%USERPROFILE%\.ollama\models" echo WARNING: copy the Ollama models folder to %USERPROFILE%\.ollama\models

echo.
echo Done. Next: python ingestion.py   then   python ask.py "your question"