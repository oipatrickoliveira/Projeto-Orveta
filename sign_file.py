"""Sign an executable using certificate settings supplied in environment variables."""
import os
from pathlib import Path
import subprocess
import sys


def main(path):
    certificate = os.environ.get('ORVETA_CERT_FILE')
    password = os.environ.get('ORVETA_CERT_PASSWORD')
    if not certificate or password is None:
        raise RuntimeError('ORVETA_CERT_FILE and ORVETA_CERT_PASSWORD are required for signing')
    if not Path(certificate).is_file():
        raise FileNotFoundError('Signing certificate was not found')
    signtool = os.environ.get('ORVETA_SIGNTOOL', 'signtool.exe')
    timestamp = os.environ.get('ORVETA_TIMESTAMP_URL', 'https://timestamp.digicert.com')
    subprocess.run([signtool, 'sign', '/fd', 'SHA256', '/f', certificate, '/p', password, '/tr', timestamp, '/td', 'SHA256', str(path)], check=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: sign_file.py <file>')
    main(sys.argv[1])
