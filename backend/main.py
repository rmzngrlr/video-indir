import os
import uuid
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import yt_dlp
import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    print(f"\n=========================================================================")
    print(f"✅ SUNUCU BASLADI! Baska cihazlardan erismek icin su adrese gidin:")
    print(f"👉 http://{get_local_ip()}:3003")
    print(f"=========================================================================\n")

# Allow cross-origin requests in case of remote access via ngrok/tunnels
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary directory for downloads
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Mount the static directory to serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

class DownloadRequest(BaseModel):
    url: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None

def remove_file(path: str):
    """Background task to remove the file after it has been sent."""
    try:
        # Give it a tiny bit of time to ensure it's released, though Starlette's FileResponse
        # usually handles the file handles properly.
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error removing file {path}: {e}")

@app.post("/api/download")
async def download_video(request: DownloadRequest, background_tasks: BackgroundTasks):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Unique filename base
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'format': 'bestvideo+bestaudio/best', # En iyi kaliteyi al, mp4/webm fark etmeksizin
        'merge_output_format': 'mp4', # İndirme bitince mp4'e birleştir/dönüştür
        'noplaylist': True,
        'quiet': False,
        'js_runtimes': {'node': {}}, # Explicitly tell yt-dlp to use node JS runtime
    }

    # Check if a cookies file exists in the root directory
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = "cookies.txt"

    # Helper to parse HH:MM:SS to seconds
    def parse_time(time_str):
        if not time_str:
            return None
        parts = time_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(parts[0])

    # If both start and end time are provided, we use the --download-sections feature
    if request.start_time and request.end_time:
        # Instead of download_ranges, which relies on ffmpeg downloading sections natively, 
        # let's download the whole thing and then cut it, or use the postprocessor
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  
        }]
        # ffmpeg -ss X -to Y -i input ... is tricky with yt-dlp's standard opts 
        # so we inject it into the postprocessor args.
        # But a more reliable way if download_ranges gives 403: download full, then clip.
        ydl_opts['postprocessor_args'] = [
            '-ss', request.start_time,
            '-to', request.end_time
        ]

    try:
        # We run yt_dlp in a separate thread so it doesn't block the async event loop
        def run_yt_dlp(opts, url):
            with yt_dlp.YoutubeDL(opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                # Ensure we get the correct final filename
                return ydl.prepare_filename(info_dict)

        final_filename = await asyncio.to_thread(run_yt_dlp, ydl_opts, request.url)

        if not final_filename or not os.path.exists(final_filename):
             # Sometimes yt-dlp changes the extension after merge (e.g., to .mkv or .mp4)
             # Let's search for the file starting with our uuid
             found = False
             for f in os.listdir(DOWNLOAD_DIR):
                 if f.startswith(file_id):
                     final_filename = os.path.join(DOWNLOAD_DIR, f)
                     found = True
                     break
             if not found:
                 raise HTTPException(status_code=500, detail="Download failed, file not found.")

        # Schedule file deletion after it's sent
        background_tasks.add_task(remove_file, final_filename)

        # We extract a clean name for the user
        download_name = "video" + os.path.splitext(final_filename)[1]
        
        return FileResponse(
            path=final_filename, 
            filename=download_name, 
            media_type='application/octet-stream'
        )

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "ffmpeg is not installed" in error_msg.lower():
            raise HTTPException(status_code=500, detail="FFmpeg kurulu değil! Videoları birleştirmek veya kesmek için sunucuda FFmpeg'in kurulu ve ortam değişkenlerine (PATH) ekli olması gereklidir. Lütfen README.md dosyasındaki kurulum adımlarını izleyin.")
        if "confirm you’re not a bot" in error_msg.lower() or "confirm you're not a bot" in error_msg.lower():
            raise HTTPException(status_code=400, detail="YouTube bot korumasına takıldınız! Çözüm için: Bilgisayarınızda YouTube'a girin, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucudaki proje ana dizinine 'cookies.txt' adıyla kaydedip sunucuyu yeniden başlatın.")
        if "login required" in error_msg.lower() or "rate-limit reached" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Instagram/Facebook giriş zorunluluğuna veya sınırına takıldınız! Çözüm için: Kendi bilgisayarınızda ilgili siteye (Instagram vs) giriş yapın, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucu dizinine 'cookies.txt' adıyla kaydedip sunucuyu yeniden başlatın.")
        raise HTTPException(status_code=400, detail=f"İndirme hatası: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@app.post("/api/prepare")
async def prepare_download(request: DownloadRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'format': 'bestvideo+bestaudio/best', # En iyi kaliteyi al, mp4/webm fark etmeksizin
        'merge_output_format': 'mp4', # İndirme bitince mp4'e birleştir/dönüştür
        'noplaylist': True,
        'quiet': False,
        'js_runtimes': {'node': {}}, # Explicitly tell yt-dlp to use node JS runtime
    }

    # Check if a cookies file exists in the root directory
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = "cookies.txt"

    try:
        def run_yt_dlp(opts, url):
            with yt_dlp.YoutubeDL(opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info_dict)

        final_filename = await asyncio.to_thread(run_yt_dlp, ydl_opts, request.url)

        # Eğer kesit (clipping) isteniyorsa, yt-dlp işleminin bitmesinin ardından Python ile FFmpeg'i çağırıyoruz.
        # Bu yöntem yt-dlp hook'larına kıyasla yollar ve tırnak işaretleriyle çok daha tutarlı çalışır.
        if request.start_time and request.end_time and final_filename and os.path.exists(final_filename):
            temp_filename = final_filename + ".temp.mp4"
            import subprocess
            cmd = [
                "ffmpeg", "-y", "-i", final_filename,
                "-ss", request.start_time, "-to", request.end_time,
                "-c", "copy", temp_filename
            ]
            try:
                # Arka planda engellememesi için asyncio üzerinden çağırıyoruz
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0 and os.path.exists(temp_filename):
                    # Orijinal dosyayı silip kesilmiş dosyayı orijinal ismiyle kaydediyoruz.
                    os.replace(temp_filename, final_filename)
                else:
                    print(f"FFmpeg clipping failed: {stderr.decode()}")
            except Exception as e:
                print(f"Error executing FFmpeg: {e}")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

        if not final_filename or not os.path.exists(final_filename):
             found = False
             for f in os.listdir(DOWNLOAD_DIR):
                 if f.startswith(file_id):
                     final_filename = os.path.join(DOWNLOAD_DIR, f)
                     found = True
                     break
             if not found:
                 raise HTTPException(status_code=500, detail="Download failed, file not found.")

        # Instead of returning the file directly, return the token so the frontend can do a standard GET download
        # The frontend will hit GET /api/download_file/{file_id}
        token = os.path.basename(final_filename)
        return {"token": token, "filename": "video" + os.path.splitext(final_filename)[1]}

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "ffmpeg is not installed" in error_msg.lower():
            raise HTTPException(status_code=500, detail="FFmpeg kurulu değil! Videoları birleştirmek veya kesmek için sunucuda FFmpeg'in kurulu ve ortam değişkenlerine (PATH) ekli olması gereklidir. Lütfen README.md dosyasındaki kurulum adımlarını izleyin.")
        if "confirm you’re not a bot" in error_msg.lower() or "confirm you're not a bot" in error_msg.lower():
            raise HTTPException(status_code=400, detail="YouTube bot korumasına takıldınız! Çözüm için: Bilgisayarınızda YouTube'a girin, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucudaki proje ana dizinine 'cookies.txt' adıyla kaydedip sunucuyu yeniden başlatın.")
        if "login required" in error_msg.lower() or "rate-limit reached" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Instagram/Facebook giriş zorunluluğuna veya sınırına takıldınız! Çözüm için: Kendi bilgisayarınızda ilgili siteye (Instagram vs) giriş yapın, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucu dizinine 'cookies.txt' adıyla kaydedip sunucuyu yeniden başlatın.")
        raise HTTPException(status_code=400, detail=f"İndirme hatası: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@app.get("/api/download_file/{token}")
async def download_file(token: str, background_tasks: BackgroundTasks):
    # Security: ensure no path traversal
    token = os.path.basename(token)
    file_path = os.path.join(DOWNLOAD_DIR, token)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı veya süresi doldu.")
        
    # Schedule deletion after it's been downloaded
    background_tasks.add_task(remove_file, file_path)
    
    # Send it as an attachment so the browser always downloads it
    return FileResponse(
        path=file_path, 
        filename="video" + os.path.splitext(token)[1],
        media_type='application/octet-stream',
        content_disposition_type='attachment'
    )

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

