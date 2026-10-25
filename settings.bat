@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py tools\settings_gui.py) || (python tools\settings_gui.py)
