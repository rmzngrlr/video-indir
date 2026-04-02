@echo off
:: Yonetici izinlerini kontrol et
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Yonetici izinleri dogrulandi. Guvenlik duvari kurali ekleniyor...
) else (
    echo Lutfen bu dosyaya sag tiklayip "Yonetici olarak calistir" (Run as administrator) secenegini secin.
    pause
    exit /b
)

:: Kurali ekle
netsh advfirewall firewall add rule name="PWA Video Downloader 3003" dir=in action=allow protocol=TCP localport=3003
echo.
echo Islem tamamlandi! Baska cihazlardan IP adresiniz uzerinden erisim saglayabilirsiniz.
pause
