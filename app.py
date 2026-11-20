"""Orveta application entry point and backwards-compatible imports."""
from tkinter import filedialog, messagebox

from orveta_ui import App, DATA_DIR
from download_options import DownloadOptionError, build_download_args
from media_commands import conversion_command, friendly_error
from settings_store import load_json, save_json


if __name__ == '__main__':
    App().mainloop()
