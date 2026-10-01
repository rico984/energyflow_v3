@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python Launcher fehlt.& pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" py -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -r requirements.txt || goto error
python -m streamlit run app.py
exit /b 0
:error
echo Start fehlgeschlagen.
pause
exit /b 1
