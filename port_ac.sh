#!/bin/bash
echo "Ubuntu (UFW) Güvenlik duvarından 3003 portuna izin veriliyor..."

if [ "$EUID" -ne 0 ]; then
  echo "Lütfen bu betiği root veya sudo ile çalıştırın. (Örnek: sudo ./port_ac.sh)"
  exit 1
fi

ufw allow 3003/tcp
echo "İşlem tamamlandı! Başka cihazlardan erişebilirsiniz."
