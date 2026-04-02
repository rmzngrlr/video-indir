# PWA Video Downloader

Bu proje, Twitter, YouTube, Facebook, Instagram, TikTok vb. platformlardan tam veya kesitli (başlangıç ve bitiş zamanına göre) video indirebileceğiniz, uzaktan erişilebilir, mobil uyumlu bir PWA panelidir. Arka uçta `FastAPI` ve indirme işlemleri için `yt-dlp` kullanılmaktadır.

## Gereksinimler

Projenin tam anlamıyla çalışabilmesi, özellikle **videolardan kesit (clip) alabilmesi** ve ses/görüntü dosyalarını birleştirebilmesi için sisteminizde **FFmpeg** kurulu olması zorunludur.

### 1. FFmpeg Kurulumu
* **Windows:**
  - [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/) adresinden FFmpeg'i indirin.
  - Sıkıştırılmış dosyayı çıkarın ve `bin` klasörünün yolunu sistem `PATH` ortam değişkenlerine ekleyin.
* **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt update
  sudo apt install ffmpeg
  ```
* **macOS (Homebrew ile):**
  ```bash
  brew install ffmpeg
  ```

### 2. Python Bağımlılıklarının Kurulumu
Projenin kök dizininde veya `backend` klasöründe terminal açın ve aşağıdaki komutu çalıştırarak gerekli kütüphaneleri yükleyin:
```bash
pip install -r backend/requirements.txt
```

## Çalıştırma

Projenin kök dizinindeyken arka uç (backend) sunucusunu başlatmak için oluşturulmuş hazır scriptleri kullanabilirsiniz:

* **Windows:** `start_server.bat` dosyasına çift tıklayın.
* **Ubuntu / Linux:** Terminalde `./start_server.sh` komutunu çalıştırın. (Eğer izin hatası verirse önce `chmod +x start_server.sh` yapın).

Bu scriptler sunucuyu `0.0.0.0` üzerinden başlatır; böylece sunucunun bulunduğu ağa/internete açık IP adresi üzerinden dışarıdan erişebilirsiniz.

**Örnek:** Sunucunuzun IP adresi `192.168.1.50` (veya dış IP) ise, telefonunuzdan şu adrese giderek panele erişebilirsiniz:
`http://192.168.1.50:3003`

### Başka Cihazlardan (Dışarıdan) Erişemiyorsanız (Güvenlik Duvarı Sorunu):
Eğer kodu çalıştırdığınız sunucuda siteye girilebiliyor ancak *uzaktan girdiğinizde hata alıyorsanız*, sunucunuzun **Güvenlik Duvarı 3003 portunu engelliyor demektir**. Bu durumu çözmek için hazır scriptleri kullanabilirsiniz:

* **Ubuntu / Linux:** Terminalde `sudo ./port_ac.sh` komutunu çalıştırarak UFW üzerinden 3003 portunu hemen açabilirsiniz.
* **Windows:** Klasördeki `port_ac.bat` dosyasına sağ tıklayıp **Yönetici Olarak Çalıştır** demeniz yeterlidir.

## PWA ve Kurulum (Ana Ekrana Ekleme) Notu
Şu anki altyapı bir PWA'nın (Progressive Web App) temel gereksinimlerini (`manifest.json` ve `sw.js`) barındırmaktadır. Ancak tarayıcıların "Ana Ekrana Ekle" (Install) butonunu çıkarabilmesi için uygulamanın **HTTPS** üzerinden sunulması gereklidir. Geliştirme aşamasında localhost (örn. `http://localhost:3003`) PWA kurulumuna izin verir, ancak ağdaki başka bir cihaz (IP adresi üzerinden) HTTPS olmadan PWA olarak kuramaz. Bu durumda ngrok, Cloudflare Tunnels gibi araçlar kullanılabilir.
