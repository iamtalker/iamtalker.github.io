@echo off
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py) || (set PY=python)

if not exist config.json (
  echo First run: opening the settings window...
  %PY% tools\settings_gui.py
  if not exist config.json goto :end
)

%PY% tools\build_books.py docs
if errorlevel 1 goto :error

%PY% tools\build_library.py
if errorlevel 1 goto :error

%PY% -c "import sys; sys.path.insert(0,'tools'); import config; sys.exit(0 if config.load_local()['auto_push'] else 1)"
if errorlevel 1 (
  echo Built. Auto push is off, so nothing was uploaded.
  goto :end
)

%PY% tools\publish.py
if errorlevel 1 goto :error

echo Done. Live in about a minute.
goto :end

:error
echo Something failed above - scroll up for the error.

:end
pause
