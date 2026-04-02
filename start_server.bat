@echo off
echo PWA Video Downloader baslatiliyor...
echo.
uvicorn backend.main:app --host 0.0.0.0 --port 3003
pause
