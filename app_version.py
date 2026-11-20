"""Application version shared with the installer and release build."""
from pathlib import Path
import sys


def get_version():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return (base / 'version.txt').read_text(encoding='utf-8').strip()
