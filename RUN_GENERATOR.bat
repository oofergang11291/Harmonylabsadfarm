@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Python setup failed. Install Python from python.org and try again.
  pause
  exit /b 1
)
py generate_ads.py
if errorlevel 1 (
  echo Generation failed. See error message above.
  pause
  exit /b 1
)
echo.
echo All 30 posts are inside the output folder.
pause
