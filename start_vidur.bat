@echo off
cd /d "%~dp0"

echo Starting Docker containers...
docker compose -f infra\docker\docker-compose.yml up -d

echo Starting backend...
start "VIDUR Backend" cmd /k "cd backend && venv\Scripts\activate.bat && uvicorn app.main:app --port 8080"

timeout /t 3 /nobreak >nul

echo Starting local agent...
start "VIDUR Agent" cmd /k "cd backend && venv\Scripts\activate.bat && python scripts\local_agent.py --project-id vidur-self --backend-url http://localhost:8080"

echo Starting frontend...
start "VIDUR Frontend" cmd /k "cd frontend && npm run dev"

echo All VIDUR services launching in separate windows.