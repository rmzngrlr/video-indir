import yt_dlp
import asyncio

ydl_opts = {
    'quiet': False,
    'extractor_args': {'youtube': ['player_client=tv,default']},
    'js_runtimes': {'node': {}},
}

def run_yt_dlp(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        print("Initialization Success")

run_yt_dlp(ydl_opts, "https://www.youtube.com/watch?v=JKIzZGOh_2k")
