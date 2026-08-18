@echo off
REM Scholar Citation Tracker - Windows launcher
cd /d "%~dp0"
if not exist logs mkdir logs
set SCHOLAR_AUTO_UPDATE=1
set SCHOLAR_UPDATE_HOUR=3
python -m scholar_counter.cli serve
pause
