"""Measure time until a new Orveta window is created on Windows (non-visual check)."""
import argparse
import ctypes
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)
ENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [ENUMPROC, wintypes.LPARAM]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]


def windows():
    found = set()
    @ENUMPROC
    def visit(handle, _parameter):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(handle, title, len(title))
        if title.value.startswith('Orveta —'):
            found.add(int(handle))
        return True
    user32.EnumWindows(visit, 0)
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--timeout', type=float, default=20)
    args = parser.parse_args()
    baseline = windows()
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    started = time.perf_counter()
    process = subprocess.Popen([str(args.executable.resolve())], startupinfo=startup)
    try:
        while time.perf_counter() - started < args.timeout:
            if windows() - baseline:
                print(f'{time.perf_counter() - started:.3f} s (new window created)')
                return
            if process.poll() is not None:
                raise RuntimeError(f'Process exited with {process.returncode} before creating a window')
            time.sleep(0.02)
        raise TimeoutError('No new window appeared before timeout')
    finally:
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


if __name__ == '__main__':
    main()
