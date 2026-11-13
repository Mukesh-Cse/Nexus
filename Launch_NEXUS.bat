@echo off
setlocal
cd /d "%~dp0"
set "NEXUS_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "NEXUS_PYTHON=%~dp0.venv\Scripts\python.exe"
"%NEXUS_PYTHON%" -c "import streamlit, numpy, pandas, sklearn, requests, bs4" >nul 2>&1
if errorlevel 1 (
  echo NEXUS dependencies are missing.
  echo Run this command from this folder:
  echo python -m pip install -r requirements.txt
  pause
  exit /b 1
)
echo Opening NEXUS. Keep this window open while using the app.
"%NEXUS_PYTHON%" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
if errorlevel 1 pause
endlocal

