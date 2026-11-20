import math


def conversion_command(ffmpeg, source, target, fmt, start='', end=''):
    try:
        begin = float(start) if start else 0.0
        finish = float(end) if end else None
        if not math.isfinite(begin) or begin < 0 or (finish is not None and (not math.isfinite(finish) or finish <= begin)):
            raise ValueError
    except ValueError:
        raise ValueError('Use segundos positivos e um fim maior que o início.') from None
    video_codecs = {'mp4': ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac'], 'mkv': ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac'], 'webm': ['-c:v', 'libvpx-vp9', '-c:a', 'libopus']}
    audio_codecs = {'mp3': 'libmp3lame', 'm4a': 'aac', 'opus': 'libopus', 'wav': 'pcm_s16le', 'flac': 'flac'}
    options = ['-map', '0:v:0', '-map', '0:a:0?', *video_codecs[fmt]] if fmt in video_codecs else ['-map', '0:a:0', '-vn', '-c:a', audio_codecs[fmt]]
    timing = (['-ss', str(begin)] if begin else []) + (['-t', str(finish - begin)] if finish is not None else [])
    return [str(ffmpeg), '-nostdin', '-hide_banner', '-n', '-i', str(source), *timing, *options, str(target)]


def friendly_error(output):
    text = output.lower()
    if any(term in text for term in ('sign in', 'login required', 'authentication required', 'cookies')):
        return 'Este conteúdo pode exigir acesso à conta. Esta versão ainda não oferece login.'
    if any(term in text for term in ('drm', 'protected content')):
        return 'O conteúdo parece estar protegido e não pode ser processado pelo Orveta.'
    if any(term in text for term in ('unsupported url', 'no suitable extractor')):
        return 'O site ou link não é compatível com o mecanismo de download atual.'
    if 'requested format is not available' in text:
        return 'A qualidade escolhida não está disponível para este vídeo. Tente outra opção.'
    if any(term in text for term in ('private video', 'video unavailable', 'not available', '404')):
        return 'O conteúdo pode estar privado, indisponível ou ter sido removido.'
    if any(term in text for term in ('unable to resolve', 'name resolution', 'network is unreachable', 'timed out')):
        return 'Não foi possível conectar ao site. Verifique a conexão e tente novamente.'
    return 'Não foi possível concluir a operação. Consulte os detalhes abaixo.'


