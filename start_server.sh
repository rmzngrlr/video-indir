#!/bin/bash
echo "PWA Video Downloader başlatılıyor..."
uvicorn backend.main:app --host 0.0.0.0 --port 3003
