@echo off
cd /d "%~dp0"

echo Stopping VIDUR windows...
taskkill /F /FI "WINDOWTITLE eq VIDUR Backend*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VIDUR Agent*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VIDUR Frontend*" /T >nul 2>&1

echo Freeing port 8080...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8080" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo Done. All VIDUR services stopped, port 8080 freed.
pause
