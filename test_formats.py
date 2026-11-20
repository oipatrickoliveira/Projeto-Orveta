import functools
import http.server
import os
import subprocess
import tempfile
import threading
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    ffmpeg = Path(os.environ.get('ORVETA_TEST_FFMPEG', root / 'vendor' / 'ffmpeg' / 'ffmpeg.exe'))
    ytdlp = root / 'vendor' / 'yt-dlp.exe'
    with tempfile.TemporaryDirectory(dir=root) as temp:
        folder = Path(temp)
        source = folder / 'sample.mp4'
        subprocess.run([str(ffmpeg), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=160x120:rate=10', '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(source)], check=True)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=temp)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/sample.mp4'
            for fmt in ('mp4', 'mkv', 'webm', 'mp3', 'm4a', 'opus', 'wav', 'flac'):
                args = ['--recode-video', fmt] if fmt in ('mp4', 'mkv', 'webm') else ['-x', '--audio-format', fmt]
                result = subprocess.run([str(ytdlp), '--ignore-config', '--ffmpeg-location', str(ffmpeg.parent), '-o', str(folder / f'out-{fmt}.%(ext)s'), *args, '--', url], capture_output=True, text=True)
                if result.returncode or not (folder / f'out-{fmt}.{fmt}').exists():
                    raise RuntimeError(f'{fmt}: {result.stdout}\n{result.stderr}')
                print(f'{fmt}: OK', flush=True)
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
