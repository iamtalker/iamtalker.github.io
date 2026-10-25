@echo off
cd /d "%~dp0"

rem Opens the main window (upload + settings in one). pyw/pythonw = no console window.
where pyw >nul 2>nul && goto :pyw
where pythonw >nul 2>nul && goto :pythonw
where py >nul 2>nul && goto :py
where python >nul 2>nul && goto :python
echo Python 3 is not installed. Get it from https://www.python.org/downloads/
pause
goto :eof

:pyw
start "" pyw tools\app.py
goto :eof
:pythonw
start "" pythonw tools\app.py
goto :eof
:py
py tools\app.py
goto :eof
:python
python tools\app.py
