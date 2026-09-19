@echo off
cd /d "%~dp0"

python tools\build_site.py docs
if errorlevel 1 goto :error

python tools\build_home.py
if errorlevel 1 goto :error

git add -A
git commit -m "content update"
if errorlevel 1 (
  echo No changes to commit.
  goto :end
)

git push
if errorlevel 1 goto :error

echo Done. Live in about a minute at https://iamtalker.github.io/
goto :end

:error
echo Something failed above - scroll up for the error.

:end
pause
