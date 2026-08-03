@echo off
cd /d "%~dp0"

echo Freeing port 8080 if occupied...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8080" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo Starting Docker containers...
docker compose -f infra\docker\docker-compose.yml up -d

echo Starting backend...
start "VIDUR Backend" cmd /k "cd backend && venv\Scripts\activate.bat && uvicorn app.main:app --port 8080"

timeout /t 3 /nobreak >nul

echo Starting local agent...
start "VIDUR Agent" cmd /k "cd backend && venv\Scripts\activate.bat && python scripts\local_agent.py --project-id vidur-self --backend-url http://localhost:8080"

echo Starting frontend...
start "VIDUR Frontend" cmd /k "cd frontend && npm run dev"

echo Waiting for frontend to be ready...
timeout /t 5 /nobreak >nul

echo Opening VIDUR in your browser...
start "" "http://localhost:5173"

echo All VIDUR services launching in separate windows.
echo.
echo Come back to THIS window and press any key when you're done, to stop everything and free port 8080.
pause >nul

echo Stopping VIDUR windows...
taskkill /F /FI "WINDOWTITLE eq VIDUR Backend*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VIDUR Agent*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VIDUR Frontend*" /T >nul 2>&1

echo Freeing port 8080...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8080" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo Done. Port 8080 freed.