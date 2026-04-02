#!/bin/bash

# Set strict mode for reliable execution
set -e

echo "==========================================="
echo " PWA Video Downloader Kurulum ve Çalıştırma"
echo "==========================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

MISSING_PKG=""

# Check ffmpeg
if ! command_exists ffmpeg; then
    MISSING_PKG="$MISSING_PKG ffmpeg"
fi

# Check python3-venv (Ubuntu/Debian specific)
if command_exists dpkg; then
    if ! dpkg -s python3-venv >/dev/null 2>&1; then
        MISSING_PKG="$MISSING_PKG python3-venv"
    fi
    if ! dpkg -s python3-pip >/dev/null 2>&1; then
        MISSING_PKG="$MISSING_PKG python3-pip"
    fi
fi

# Check nodejs (JavaScript runtime needed by yt-dlp to bypass bot protection)
if ! command_exists node; then
    MISSING_PKG="$MISSING_PKG nodejs npm"
fi

if [ -n "$MISSING_PKG" ]; then
    echo "Eksik paketler tespit edildi:$MISSING_PKG"
    echo "Yükleniyor... (Root yetkisi için şifreniz istenebilir)"
    sudo apt update
    sudo apt install -y $MISSING_PKG
else
    echo "✅ Gerekli sistem paketleri kurulu."
fi

# Create Virtual Environment if it doesn't exist
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Python sanal ortamı (venv) oluşturuluyor..."
    python3 -m venv "$VENV_DIR"
else
    echo "✅ Sanal ortam (venv) zaten mevcut."
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install/Upgrade pip and requirements
echo "Python bağımlılıkları kontrol ediliyor/kuruluyor..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r backend/requirements.txt

# Ensure yt-dlp is updated to the latest version to bypass recent YouTube protections
echo "yt-dlp güncelleniyor..."
pip install -U yt-dlp > /dev/null 2>&1

# Configure UFW (Firewall)
if command_exists ufw; then
    UFW_STATUS=$(sudo ufw status | grep "Status: active" || true)
    if [ -n "$UFW_STATUS" ]; then
        if ! sudo ufw status | grep -E -q "3003/tcp.*ALLOW"; then
            echo "Güvenlik duvarı üzerinden 3003 portu açılıyor..."
            sudo ufw allow 3003/tcp
        else
            echo "✅ 3003 portu güvenlik duvarında zaten açık."
        fi
    else
        echo "ℹ️  UFW (Güvenlik Duvarı) aktif değil. Port izni adımı atlandı."
    fi
fi

echo "==========================================="
echo "✅ Sistem hazır! Sunucu başlatılıyor..."
echo "Çıkmak için CTRL+C tuşlarına basabilirsiniz."
echo "==========================================="

uvicorn backend.main:app --host 0.0.0.0 --port 3003
