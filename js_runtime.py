"""Locate an EJS-compatible JavaScript runtime for yt-dlp."""
import shutil
import sys
from pathlib import Path


def find_runtime(base=None, which=shutil.which):
    if base is None:
        base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    base = Path(base)
    candidates = [base / 'runtime' / 'qjs.exe'] if getattr(sys, 'frozen', False) else [base / 'vendor' / 'qjs-0.18.0.exe']
    for candidate in candidates:
        if candidate.is_file():
            return 'quickjs', str(candidate)
    for kind, executable in (('deno', 'deno'), ('node', 'node'), ('quickjs', 'qjs')):
        path = which(executable)
        if path:
            return kind, path
    return None


def runtime_args(runtime):
    return ['--js-runtimes', f'{runtime[0]}:{runtime[1]}'] if runtime else []
