@echo off
cd /d "%~dp0"

rem Opens the main window (upload + settings in one). pyw/pythonw = no console window.
where pyw >nul 2>nul && goto :pyw
where pythonw >nul 2>nul && goto :pythonw
where py >nul 2>nul && goto :py
where python >nul 2>nul && goto :python

echo Python 3 is not installed.
where winget >nul 2>nul || goto :nowinget
set /p ANS=Install Python 3 now with winget? (Y/N):
if /i not "%ANS%"=="Y" goto :nowinget
winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
echo.
echo Done. Close this window and double-click update.bat again.
pause
goto :eof

:nowinget
echo Get it from https://www.python.org/downloads/ (check "Add python.exe to PATH").
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
