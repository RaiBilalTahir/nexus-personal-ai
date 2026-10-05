@echo off
cd /d "%~dp0.."
venv\Scripts\python.exe app\core\nexus_core.py
pause