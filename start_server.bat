@echo off
echo ================================================================
echo   RepoAuditor AI - Starting FastAPI Server
echo ================================================================
echo.

cd /d "%~dp0"

echo [INFO] Project directory: %CD%
echo.

echo [INFO] Starting FastAPI server...
echo [INFO] Press Ctrl+C to stop the server
echo.
echo ================================================================
echo.

python -m uvicorn app.main:app --reload

pause
