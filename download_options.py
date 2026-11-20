"""Build yt-dlp arguments without shell interpolation or UI dependencies."""
import re
from pathlib import Path


class DownloadOptionError(ValueError):
    def __init__(self, title, message):
        self.title = title
        super().__init__(message)


def build_download_args(url, folder, ffmpeg, mode, output_format, rate='', playlist=False, subtitles=False, subtitle_languages='', subtitle_mode=''):
    args = ['--ffmpeg-location', str(Path(ffmpeg).parent), '--newline', '--progress', '--print', 'after_move:OUTPUT:%(filepath)s', '--progress-template', 'download:PROGRESS:%(progress._percent_str)s | %(progress._speed_str)s | ETA %(progress._eta_str)s', '-P', str(folder), '-o', '%(title).180B [%(id)s].%(ext)s']
    rate = rate.strip()
    if rate and (not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?[KkMm]?', rate) or float(rate.rstrip('KkMm')) <= 0):
        raise DownloadOptionError('Limite inválido', 'Informe um valor como 500K ou 2M, ou deixe o campo vazio.')
    if rate:
        args += ['--limit-rate', rate]
    args += ['--yes-playlist', '--playlist-items', '1:100'] if playlist else ['--no-playlist']
    if subtitles:
        languages = subtitle_languages.strip()
        if not languages or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,_*- ' for c in languages):
            raise DownloadOptionError('Idiomas inválidos', 'Informe códigos de idioma separados por vírgulas, como pt.*,en.*.')
        if subtitle_mode == 'Incorporar ao vídeo':
            if output_format not in ('Vídeo · MP4', 'Vídeo · MKV'):
                raise DownloadOptionError('Formato incompatível', 'Para incorporar legendas, escolha vídeo MP4 ou MKV.')
            args += ['--embed-subs']
        args += ['--write-subs', '--write-auto-subs', '--sub-langs', languages]
    if output_format.startswith('Áudio'):
        args += ['-x', '--audio-format', output_format.rsplit(' ', 1)[-1].lower(), '-f', 'bestaudio/best']
    else:
        video_format = output_format.rsplit(' ', 1)[-1].lower()
        limit = {'Até 1080p': 1080, 'Até 720p': 720, 'Até 480p': 480}.get(mode)
        selector = f'bestvideo[height<={limit}]+bestaudio/best[height<={limit}]' if limit else 'bestvideo+bestaudio/best'
        args += ['-f', selector, '--merge-output-format', 'mkv', '--recode-video', video_format]
    return [*args, '--', url]
