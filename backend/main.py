import os
import uuid
import asyncio
import subprocess
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import yt_dlp
import socket
import re

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
    client_id: Optional[str] = None
    resolution: Optional[str] = None
    selected_indices: Optional[List[int]] = None

progress_store = {}

def remove_file(path: str):
    """Background task to remove the file after it has been sent."""
    try:
        # Give it a tiny bit of time to ensure it's released, though Starlette's FileResponse
        # usually handles the file handles properly.
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error removing file {path}: {e}")

@app.post("/api/info")
async def get_video_info(request: DownloadRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    url_match = re.search(r'(https?://[^\s]+)', request.url)
    if url_match:
        request.url = url_match.group(1)

    ydl_opts = {
        'noplaylist': False, # Now allow playlist parsing to count videos
        'quiet': True,
        'js_runtimes': {'node': {}},
    }

    # Determine which cookie file to use based on URL
    cookie_file = "cookies.txt" # fallback
    if "instagram.com" in request.url.lower() and os.path.exists("instagram_cookies.txt"):
        cookie_file = "instagram_cookies.txt"
    elif "facebook.com" in request.url.lower() and os.path.exists("facebook_cookies.txt"):
        cookie_file = "facebook_cookies.txt"
    elif "youtube.com" in request.url.lower() and os.path.exists("youtube_cookies.txt"):
        cookie_file = "youtube_cookies.txt"

    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    ydl_opts['socket_timeout'] = 30  # Timeout for slow network connections

    try:
        def run_yt_dlp(opts, url):
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)

        info_dict = await asyncio.to_thread(run_yt_dlp, ydl_opts, request.url)

        videos = []
        if 'entries' in info_dict:
            # It's a playlist or a multi-video post
            for idx, entry in enumerate(info_dict['entries']):
                if entry:
                    videos.append({
                        "index": idx + 1,
                        "title": entry.get('title', f'Video {idx + 1}'),
                        "thumbnail": entry.get('thumbnail', ''),
                        "duration": entry.get('duration', 0)
                    })
        else:
            videos.append({
                "index": 1,
                "title": info_dict.get('title', 'Bilinmeyen Video'),
                "thumbnail": info_dict.get('thumbnail', ''),
                "duration": info_dict.get('duration', 0)
            })

        return {
            "title": info_dict.get('title', 'Bilinmeyen Video'),
            "thumbnail": info_dict.get('thumbnail', ''),
            "duration": info_dict.get('duration', 0),
            "videos": videos
        }

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "ffmpeg is not installed" in error_msg.lower():
            raise HTTPException(status_code=500, detail="FFmpeg kurulu değil! Lütfen README.md dosyasındaki kurulum adımlarını izleyin.")
        if "confirm you’re not a bot" in error_msg.lower() or "confirm you're not a bot" in error_msg.lower():
            raise HTTPException(status_code=400, detail="YouTube bot korumasına takıldınız! Çözüm için: Bilgisayarınızda YouTube'a girin, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucudaki proje ana dizinine 'cookies.txt' adıyla kaydedip sunucuyu yeniden başlatın.")
        if "login required" in error_msg.lower() or "rate-limit reached" in error_msg.lower() or "facebook.com/login" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Instagram/Facebook giriş sınırına takıldınız (veya çerezleriniz eksik/süresi geçmiş)! Çözüm: Bilgisayarınızda Instagram'a (veya Facebook'a) giriş yapın, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucuya 'instagram_cookies.txt' (veya facebook_cookies.txt) adıyla kaydedip yeniden başlatın.")
        raise HTTPException(status_code=400, detail=f"Bilgi alınamadı: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@app.post("/api/shortcut_download")
async def shortcut_download_video(request: DownloadRequest, background_tasks: BackgroundTasks):
    """
    iOS Shortcuts endpoint that returns the actual MP4 file directly
    instead of JSON, so the shortcut can save it straight to the camera roll.
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    url_match = re.search(r'(https?://[^\s]+)', request.url)
    if url_match:
        request.url = url_match.group(1)

    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}_%(id)s.%(ext)s")

    format_str = 'bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    ydl_opts = {
        'outtmpl': output_template,
        'format': format_str,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': False,
        'updatetime': False,
        'socket_timeout': 30, # network stability
        'js_runtimes': {'node': {}},
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'postprocessor_args': {
            'FFmpegVideoConvertor': [
                '-map_metadata', '-1',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                '-c:a', 'aac'
            ]
        }
    }

    cookie_file = None
    if "instagram.com" in request.url.lower() and os.path.exists("instagram_cookies.txt"):
        cookie_file = "instagram_cookies.txt"
    elif "facebook.com" in request.url.lower() and os.path.exists("facebook_cookies.txt"):
        cookie_file = "facebook_cookies.txt"

    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    # Set fake user-agent for Instagram to prevent bot-blocking
    if "instagram.com" in request.url.lower():
        ydl_opts['http_headers'] = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    try:
        def extract_and_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.url, download=True)
                return info

        info = await asyncio.to_thread(extract_and_download)

        # Determine final filename
        downloaded_file = None
        for file in os.listdir(DOWNLOAD_DIR):
            if file.startswith(file_id):
                downloaded_file = os.path.join(DOWNLOAD_DIR, file)
                break

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise HTTPException(status_code=500, detail="Video indirilemedi.")

        background_tasks.add_task(remove_file, downloaded_file)

        return FileResponse(
            path=downloaded_file,
            filename="video.mp4",
            media_type='video/mp4',
            content_disposition_type='attachment'
        )
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Sign in to confirm you're not a bot" in error_msg or "login" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Instagram/Facebook giriş sınırına takıldınız (veya çerezleriniz eksik/süresi geçmiş)! Çözüm: Bilgisayarınızda Instagram'a (veya Facebook'a) giriş yapın, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucuya 'instagram_cookies.txt' (veya facebook_cookies.txt) adıyla kaydedip yeniden başlatın.")
        raise HTTPException(status_code=400, detail=f"İndirme hatası: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@app.post("/api/download")
async def download_video(request: DownloadRequest, background_tasks: BackgroundTasks):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    url_match = re.search(r'(https?://[^\s]+)', request.url)
    if url_match:
        request.url = url_match.group(1)

    # Unique filename base
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}_%(id)s.%(ext)s")

    def progress_hook(d):
        if request.client_id and d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total and total > 0:
                percent = d.get('downloaded_bytes', 0) / total * 100
                progress_store[request.client_id] = round(percent, 1)

    format_str = 'bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    ydl_opts = {
        'outtmpl': output_template,
        # Sadece Apple/iOS (iPhone) cihazların yerel olarak desteklediği H.264 (avc) codec'ini zorlar
        'format': format_str,
        'merge_output_format': 'mp4', # İndirme bitince mp4'e birleştir/dönüştür
        'noplaylist': False, # Allow downloading all videos from a tweet/playlist
        'quiet': False,
        'updatetime': False, # Ensures the file gets the current date, not the original upload date (fixes gallery sorting)
        'js_runtimes': {'node': {}}, # Explicitly tell yt-dlp to use node JS runtime
        'progress_hooks': [progress_hook],
    }

    if request.selected_indices:
        ydl_opts['playlist_items'] = ','.join(map(str, request.selected_indices))

    # Optional postprocessors mapping
    ydl_opts['postprocessors'] = [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',
    }]
    ydl_opts['postprocessor_args'] = {'FFmpegVideoConvertor': [
        '-map_metadata', '-1',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        '-c:a', 'aac'
    ]}

    # Determine which cookie file to use based on URL
    cookie_file = "cookies.txt" # fallback
    if "instagram.com" in request.url.lower() and os.path.exists("instagram_cookies.txt"):
        cookie_file = "instagram_cookies.txt"
    elif "facebook.com" in request.url.lower() and os.path.exists("facebook_cookies.txt"):
        cookie_file = "facebook_cookies.txt"
    elif "youtube.com" in request.url.lower() and os.path.exists("youtube_cookies.txt"):
        cookie_file = "youtube_cookies.txt"

    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    ydl_opts['socket_timeout'] = 30  # Timeout for slow network connections

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
        ydl_opts['postprocessor_args'] = {'FFmpegVideoConvertor': [
            '-ss', request.start_time,
            '-to', request.end_time,
            '-map_metadata', '-1',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
            '-c:a', 'aac'
        ]}

    try:
        # We run yt_dlp in a separate thread so it doesn't block the async event loop
        def run_yt_dlp(opts, url):
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
                return True

        await asyncio.to_thread(run_yt_dlp, ydl_opts, request.url)

        # Bulunan tüm dosyaları (aynı id prefix'ine sahip) topla
        downloaded_files = []
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(file_id):
                downloaded_files.append(os.path.join(DOWNLOAD_DIR, f))

        if not downloaded_files:
             raise HTTPException(status_code=500, detail="Download failed, file not found.")

        final_filename = downloaded_files[0] # iOS Shortcut için sadece bir tane döndüreceğiz

        for current_file in downloaded_files:
            temp_filename = current_file + ".temp.mp4"
            cmd = []

            if request.start_time and request.end_time:
                # Helper to parse HH:MM:SS to seconds for accurate calculation
                def parse_time(time_str):
                    if not time_str:
                        return 0.0
                    parts = time_str.split(':')
                    if len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    elif len(parts) == 2: return int(parts[0]) * 60 + float(parts[1])
                    return float(parts[0]) if parts[0] else 0.0

                start_sec = parse_time(request.start_time)
                end_sec = parse_time(request.end_time)
                duration_sec = end_sec - start_sec if end_sec > start_sec else 1

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", request.start_time,
                    "-i", current_file,
                    "-t", str(duration_sec),
                    "-map_metadata", "-1",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", temp_filename
                ]
            else:
                # Eğer kırpma (trim) yoksa sadece metadata'yı siliyoruz
                cmd = [
                    "ffmpeg", "-y",
                    "-i", current_file,
                    "-map_metadata", "-1",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", temp_filename
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
                    # Orijinal dosyayı silip kesilmiş/temizlenmiş dosyayı orijinal ismiyle kaydediyoruz.
                    os.replace(temp_filename, current_file)
                else:
                    print(f"FFmpeg clipping failed: {stderr.decode()}")
            except Exception as e:
                print(f"Error executing FFmpeg: {e}")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

        # Schedule file deletion after it's sent
        for f in downloaded_files:
            background_tasks.add_task(remove_file, f)

        # We extract a clean name for the user
        download_name = "video" + os.path.splitext(final_filename)[1]
        
        # Sadece bir adet FileResponse döndürebiliriz (Kestirmeler uygulaması için)
        return FileResponse(
            path=final_filename, 
            filename=download_name, 
            media_type='video/mp4',
            content_disposition_type='attachment'
        )

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "ffmpeg is not installed" in error_msg.lower():
            raise HTTPException(status_code=500, detail="FFmpeg kurulu değil! Videoları birleştirmek veya kesmek için sunucuda FFmpeg'in kurulu ve ortam değişkenlerine (PATH) ekli olması gereklidir. Lütfen README.md dosyasındaki kurulum adımlarını izleyin.")
        if "confirm you’re not a bot" in error_msg.lower() or "confirm you're not a bot" in error_msg.lower():
            raise HTTPException(status_code=400, detail="YouTube bot korumasına takıldınız! Çözüm için: Bilgisayarınızda YouTube'a girin, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucudaki proje ana dizinine 'cookies.txt' adıyla kaydedip sunucuyu yeniden başlatın.")
        if "login required" in error_msg.lower() or "rate-limit reached" in error_msg.lower() or "facebook.com/login" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Instagram/Facebook giriş sınırına takıldınız (veya çerezleriniz eksik/süresi geçmiş)! Çözüm: Bilgisayarınızda Instagram'a (veya Facebook'a) giriş yapın, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucuya 'instagram_cookies.txt' (veya facebook_cookies.txt) adıyla kaydedip yeniden başlatın.")
        raise HTTPException(status_code=400, detail=f"İndirme hatası: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@app.post("/api/prepare")
async def prepare_download(request: DownloadRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    url_match = re.search(r'(https?://[^\s]+)', request.url)
    if url_match:
        request.url = url_match.group(1)

    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}_%(id)s.%(ext)s")

    def progress_hook(d):
        if request.client_id and d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total and total > 0:
                percent = d.get('downloaded_bytes', 0) / total * 100
                progress_store[request.client_id] = round(percent, 1)

    format_str = 'bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    if request.resolution and request.resolution != "best":
        # Modify the format string to limit height (e.g. 720, 480, 360)
        res = request.resolution
        format_str = f'bestvideo[height<={res}][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best[height<={res}]'

    ydl_opts = {
        'outtmpl': output_template,
        # Sadece Apple/iOS (iPhone) cihazların yerel olarak desteklediği H.264 (avc) codec'ini zorlar
        'format': format_str,
        'merge_output_format': 'mp4', # İndirme bitince mp4'e birleştir/dönüştür
        'noplaylist': False, # Allow downloading all videos from a tweet/playlist
        'quiet': False,
        'updatetime': False, # Ensures the file gets the current date, not the original upload date (fixes gallery sorting)
        'js_runtimes': {'node': {}}, # Explicitly tell yt-dlp to use node JS runtime
        'progress_hooks': [progress_hook],
    }

    if request.selected_indices:
        ydl_opts['playlist_items'] = ','.join(map(str, request.selected_indices))

    # Optional postprocessors mapping
    ydl_opts['postprocessors'] = [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',
    }]
    ydl_opts['postprocessor_args'] = {'FFmpegVideoConvertor': [
        '-map_metadata', '-1',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
        '-c:a', 'aac'
    ]}

    # Determine which cookie file to use based on URL
    cookie_file = "cookies.txt" # fallback
    if "instagram.com" in request.url.lower() and os.path.exists("instagram_cookies.txt"):
        cookie_file = "instagram_cookies.txt"
    elif "facebook.com" in request.url.lower() and os.path.exists("facebook_cookies.txt"):
        cookie_file = "facebook_cookies.txt"
    elif "youtube.com" in request.url.lower() and os.path.exists("youtube_cookies.txt"):
        cookie_file = "youtube_cookies.txt"

    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    ydl_opts['socket_timeout'] = 30  # Timeout for slow network connections

    try:
        def run_yt_dlp(opts, url):
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
                return True

        await asyncio.to_thread(run_yt_dlp, ydl_opts, request.url)

        # Bulunan tüm dosyaları topla
        downloaded_files = []
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(file_id):
                downloaded_files.append(os.path.join(DOWNLOAD_DIR, f))

        if not downloaded_files:
             raise HTTPException(status_code=500, detail="Download failed, file not found.")

        results = []

        for idx, current_file in enumerate(downloaded_files):
            temp_filename = current_file + ".temp.mp4"
            cmd = []

            if request.start_time and request.end_time:
                # Helper to parse HH:MM:SS to seconds for accurate calculation
                def parse_time(time_str):
                    if not time_str:
                        return 0.0
                    parts = time_str.split(':')
                    if len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    elif len(parts) == 2: return int(parts[0]) * 60 + float(parts[1])
                    return float(parts[0]) if parts[0] else 0.0

                start_sec = parse_time(request.start_time)
                end_sec = parse_time(request.end_time)
                duration_sec = end_sec - start_sec if end_sec > start_sec else 1

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", request.start_time,
                    "-i", current_file,
                    "-t", str(duration_sec),
                    "-map_metadata", "-1",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", temp_filename
                ]
            else:
                # Eğer kırpma (trim) yoksa sadece metadata'yı siliyoruz
                cmd = [
                    "ffmpeg", "-y",
                    "-i", current_file,
                    "-map_metadata", "-1",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", temp_filename
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
                    # Orijinal dosyayı silip kesilmiş/temizlenmiş dosyayı orijinal ismiyle kaydediyoruz.
                    os.replace(temp_filename, current_file)
                else:
                    print(f"FFmpeg clipping failed: {stderr.decode()}")
            except Exception as e:
                print(f"Error executing FFmpeg: {e}")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

        # Instead of returning the file directly, return the tokens so the frontend can do standard GET downloads
        results = []
        for idx, current_file in enumerate(downloaded_files):
            token = os.path.basename(current_file)
            if len(downloaded_files) > 1:
                filename = f"video_part{idx + 1}" + os.path.splitext(current_file)[1]
            else:
                filename = "video" + os.path.splitext(current_file)[1]
            results.append({"token": token, "filename": filename})

        return {"files": results}

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "ffmpeg is not installed" in error_msg.lower():
            raise HTTPException(status_code=500, detail="FFmpeg kurulu değil! Videoları birleştirmek veya kesmek için sunucuda FFmpeg'in kurulu ve ortam değişkenlerine (PATH) ekli olması gereklidir. Lütfen README.md dosyasındaki kurulum adımlarını izleyin.")
        if "confirm you’re not a bot" in error_msg.lower() or "confirm you're not a bot" in error_msg.lower():
            raise HTTPException(status_code=400, detail="YouTube bot korumasına takıldınız! Çözüm için: Bilgisayarınızda YouTube'a girin, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucudaki proje ana dizinine 'cookies.txt' adıyla kaydedip sunucuyu yeniden başlatın.")
        if "login required" in error_msg.lower() or "rate-limit reached" in error_msg.lower() or "facebook.com/login" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Instagram/Facebook giriş sınırına takıldınız (veya çerezleriniz eksik/süresi geçmiş)! Çözüm: Bilgisayarınızda Instagram'a (veya Facebook'a) giriş yapın, 'Get cookies.txt LOCALLY' eklentisiyle çerezleri indirin ve sunucuya 'instagram_cookies.txt' (veya facebook_cookies.txt) adıyla kaydedip yeniden başlatın.")
        raise HTTPException(status_code=400, detail=f"İndirme hatası: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")

@app.get("/api/progress/{client_id}")
async def get_progress(client_id: str):
    return {"progress": progress_store.get(client_id, 0)}

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
        media_type='video/mp4',
        content_disposition_type='attachment'
    )

@app.get("/api/download_extension")
def download_chrome_extension():
    import shutil
    import os

    extension_dir = "extension"
    zip_path = os.path.join(DOWNLOAD_DIR, "viddown_chrome_extension")

    if not os.path.exists(extension_dir):
        raise HTTPException(status_code=404, detail="Eklenti klasörü bulunamadı.")

    shutil.make_archive(zip_path, 'zip', extension_dir)

    return FileResponse(
        path=zip_path + ".zip",
        filename="viddown_chrome_extension.zip",
        media_type="application/zip",
        content_disposition_type="attachment"
    )

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

