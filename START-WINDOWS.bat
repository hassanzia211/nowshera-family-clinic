@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (set "PYTHON=py -3") else (set "PYTHON=python")
if not exist .venv\Scripts\python.exe %PYTHON% -m venv .venv
if not exist .venv\Scripts\python.exe goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe manage.py demo
if errorlevel 1 goto error
if exist instance\DEMO-LOGINS.txt start notepad instance\DEMO-LOGINS.txt
start "Clinic browser" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"
.venv\Scripts\python.exe run.py
pause
exit /b
:error
echo Setup failed. Install Python 3.11 or newer with Add Python to PATH, then run this file again.
pause
