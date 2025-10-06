@echo off
REM Scholar Citation Tracker Startup Script for Windows

cd /d "%~dp0"
echo Starting Scholar Citation Tracker...
echo Working directory: %CD%

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Start the application
python app.py

pause