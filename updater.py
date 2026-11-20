"""Selection of the existing manual yt-dlp update action."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.request import Request, urlopen

RELEASES = {
    'stable': 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/',
    'nightly': 'https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/',
}
MAX_BINARY_SIZE = 100 * 1024 * 1024


def should_retry_after_update(action, output, attempted, frozen):
    return action == 'download' and frozen and not attempted and 'unable to extract' in output.lower()


def _read_url(url, limit):
    with urlopen(Request(url, headers={'User-Agent': 'Orveta-updater'}), timeout=30) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError('Arquivo de atualização excede o limite permitido.')
    return content


def checksum_for_executable(checksums):
    for line in checksums.decode('utf-8').splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip('*') == 'yt-dlp.exe':
            digest = parts[0].lower()
            if len(digest) == 64 and all(c in '0123456789abcdef' for c in digest):
                return digest
    raise ValueError('Checksum do executável não encontrado.')


def update_binary(target, channel='stable', read_url=_read_url, validate=None):
    """Replace the binary only after checksum and execution checks; restore on failure."""
    if channel not in RELEASES:
        raise ValueError('Canal de atualização inválido.')
    target = Path(target)
    if not target.is_file():
        raise FileNotFoundError('O mecanismo de download não foi encontrado.')
    root = RELEASES[channel]
    expected = checksum_for_executable(read_url(root + 'SHA2-256SUMS', 1024 * 1024))
    data = read_url(root + 'yt-dlp.exe', MAX_BINARY_SIZE)
    if not data or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('O checksum do mecanismo não corresponde à release oficial.')
    temporary = None
    backup = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.orveta-update-', suffix='.exe', delete=False) as file:
            temporary = Path(file.name)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        if validate is None:
            def validate(path):
                flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                result = subprocess.run([str(path), '--version'], capture_output=True, timeout=20, creationflags=flags)
                return result.returncode == 0 and bool(result.stdout.strip())
        if not validate(temporary):
            raise ValueError('O mecanismo baixado não passou no teste de execução.')
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.orveta-backup-', suffix='.exe', delete=False) as file:
            backup = Path(file.name)
        backup.unlink()
        os.replace(target, backup)
        try:
            os.replace(temporary, target)
            temporary = None
        except OSError:
            os.replace(backup, target)
            backup = None
            raise
        backup.unlink()
        backup = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def update_action(busy, frozen):
    if busy:
        return 'Aguarde', 'Aguarde a tarefa atual terminar antes de atualizar.', None
    if not frozen:
        return 'Atualização', 'No modo de desenvolvimento, atualize o yt-dlp pelo ambiente Python.', None
    return None, None, ['-U']
