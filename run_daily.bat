@echo off
setlocal

set CLAUDE=C:\Users\lenovo\AppData\Roaming\npm\claude.cmd
set WORKDIR=C:\Yuna
set LOGFILE=C:\Yuna\logs\daily.log

if not exist "C:\Yuna\logs" mkdir "C:\Yuna\logs"

cd /d "%WORKDIR%"

echo [%date% %time%] 일일 업무보고 시작 >> "%LOGFILE%"
python "C:\Yuna\업무보고\auto_report.py" --type daily >> "%LOGFILE%" 2>&1
echo [%date% %time%] 완료 (exit: %errorlevel%) >> "%LOGFILE%"

endlocal
