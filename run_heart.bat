@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 -c "import tkinter" >nul 2>nul
if %errorlevel%==0 goto RUNPY
python -c "import tkinter" >nul 2>nul
if %errorlevel%==0 goto RUNPYTHON
echo Python with tkinter not found. Opening the web version instead...
start "" "heart_popup_preview.html"
goto END
:RUNPY
py -3 "heart_popup.py"
goto END
:RUNPYTHON
python "heart_popup.py"
goto END
:END
if errorlevel 1 (
    echo.
    echo Run failed. Please install Python 3 from python.org.
    pause
)
