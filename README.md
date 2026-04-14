# PWA Video Downloader

Bu proje, Twitter, YouTube, Facebook, Instagram, TikTok vb. platformlardan tam veya kesitli (başlangıç ve bitiş zamanına göre) video indirebileceğiniz, uzaktan erişilebilir, mobil uyumlu bir PWA panelidir. Arka uçta `FastAPI` ve indirme işlemleri için `yt-dlp` kullanılmaktadır.

## Kurulum ve Çalıştırma (Docker)

Bu proje tamamen Docker tabanlı çalışacak şekilde güncellenmiştir. Yerel bilgisayarınıza Python, FFmpeg, NodeJS veya başka bağımlılıklar kurmanıza gerek yoktur. Her şey izole bir Docker container'ı içinde çalışır.

### Başlatma Adımları

1. Bilgisayarınızda veya sunucunuzda **Docker** ve **Docker Compose** kurulu olduğundan emin olun.
2. Terminalden proje kök dizinine (bu dosyanın bulunduğu yere) gidin.
3. Aşağıdaki komutu çalıştırarak sunucuyu arka planda başlatın:
   ```bash
   docker-compose up -d --build
   ```

Sunucu hazır olduğunda tarayıcınızdan `http://localhost:3003` adresine (veya sunucunuzun dış IP adresine `http://IP_ADRESI:3003`) giderek arayüze ulaşabilirsiniz. Docker otomatik olarak 3003 portunu dışarı açacaktır.

*(Uygulamayı durdurmak için `docker-compose down` kullanabilirsiniz.)*

### Notlar (Cookie Kullanımı)
YouTube, Instagram veya Facebook gibi platformlarda bot engeline takılmamak için `cookies.txt` (veya `instagram_cookies.txt` vb.) dosyalarınızı ana dizine koyup `docker-compose.yml` içindeki volume satırlarını aktif ederek yeniden başlatabilirsiniz.

## PWA ve Kurulum (Ana Ekrana Ekleme) Notu
Şu anki altyapı bir PWA'nın (Progressive Web App) temel gereksinimlerini (`manifest.json` ve `sw.js`) barındırmaktadır. Ancak tarayıcıların "Ana Ekrana Ekle" (Install) butonunu çıkarabilmesi için uygulamanın **HTTPS** üzerinden sunulması gereklidir. Geliştirme aşamasında localhost (örn. `http://localhost:3003`) PWA kurulumuna izin verir, ancak ağdaki başka bir cihaz (IP adresi üzerinden) HTTPS olmadan PWA olarak kuramaz. Bu durumda ngrok, Cloudflare Tunnels gibi araçlar kullanılabilir.
