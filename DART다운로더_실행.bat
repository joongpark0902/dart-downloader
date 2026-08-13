@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem exe가 Smart App Control에 막힐 때 소스로 바로 실행하는 런처.
rem python.exe는 Python 재단 서명이 있어 차단되지 않는다.

where pythonw >nul 2>&1
if errorlevel 1 goto no_python

start "" pythonw "%~dp0dart_gui.py"
exit /b 0

:no_python
echo.
echo  Python을 찾을 수 없습니다.
echo  https://www.python.org/downloads/ 에서 설치할 때
echo  "Add python.exe to PATH" 를 체크하세요.
echo.
echo  설치 후 아래를 한 번 실행해 주세요.
echo      pip install -r requirements.txt
echo.
pause
exit /b 1
