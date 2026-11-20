import json
import ctypes
import base64
import os
import platform
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from translations import canonical, translate
from diagnostics import create_logger
from process_runner import run_worker
from updater import update_action, update_binary, should_retry_after_update
from js_runtime import find_runtime
from app_version import get_version
from download_options import DownloadOptionError, build_download_args

DATA_DIR = Path(os.environ.get('APPDATA', Path.home())) / 'Orveta'


def ui_text(owner, text):
    language = getattr(owner, 'language', None)
    return translate(text, language.get() if language is not None else 'Português')


from media_commands import conversion_command, friendly_error
from settings_store import load_json, save_json


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Orveta — Baixar vídeos')
        if os.name == 'nt':
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Orveta.Orveta.Desktop')
            except (AttributeError, OSError):
                pass
        icon = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'orveta.ico'
        if icon.is_file():
            try:
                self.iconbitmap(default=str(icon))
            except tk.TclError:
                pass
        self.geometry('920x820')
        self.minsize(760, 720)
        self.configure(bg='#FAF8F5')
        self.events = queue.Queue()
        self.process = None
        self.busy = False
        self.cancelled = False
        self.jobs = []
        self.queueing = False
        self.runtime_warning_shown = False
        self.retry_args = None
        self.retrying_download = False
        self.inspect_timer = None
        self.log = create_logger(DATA_DIR)
        self.log.info('Aplicativo iniciado')
        preferences = load_json(DATA_DIR / 'preferences.json', {})
        if not isinstance(preferences, dict):
            preferences = {}
        language = preferences.get('language', 'Português')
        self.language = tk.StringVar(value=language if language in ('Português', 'English', 'Español') else 'Português')
        self.history = load_json(DATA_DIR / 'history.json', [])
        if not isinstance(self.history, list):
            self.history = []
        self.history = self.history[-500:]
        self.url = tk.StringVar()
        self.folder = tk.StringVar(value=preferences.get('folder', str(Path.home() / 'Downloads')))
        self.mode = tk.StringVar(value=preferences.get('mode', 'Melhor qualidade'))
        self.output_format = tk.StringVar(value=preferences.get('output_format', 'Vídeo · MP4'))
        self.status = tk.StringVar(value='Cole um link para começar.')
        self.details = tk.StringVar(value='Nenhum vídeo analisado.')
        self.video_info = None
        self.local_file = tk.StringVar()
        self.convert_format = tk.StringVar(value=preferences.get('convert_format', 'Vídeo · MP4'))
        self.convert_status = tk.StringVar(value='Escolha um arquivo para começar.')
        self.subtitle_enabled = tk.BooleanVar(value=False)
        self.subtitle_languages = tk.StringVar(value='pt.*,en.*')
        self.subtitle_mode = tk.StringVar(value='Arquivo separado')
        self.trim_start = tk.StringVar()
        self.trim_end = tk.StringVar()
        self.playlist_enabled = tk.BooleanVar(value=False)
        self.rate_limit = tk.StringVar()
        self.update_channel = tk.StringVar(value=preferences.get('update_channel', 'stable') if preferences.get('update_channel') in ('stable', 'nightly') else 'stable')
        self.downloader_version = tk.StringVar(value='yt-dlp: …')
        self.build_ui()
        self.apply_language()
        self.format_changed()
        for variable in (self.folder, self.mode, self.output_format, self.convert_format, self.language, self.update_channel):
            variable.trace_add('write', self.save_preferences)
        self.after(100, self.poll)
        threading.Thread(target=self.read_downloader_version, daemon=True).start()
        self.protocol('WM_DELETE_WINDOW', self.close)

    def build_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background='#FAF8F5')
        style.configure('TLabel', background='#FAF8F5', foreground='#14221D', font=('Segoe UI', 10))
        style.configure('TButton', padding=(16, 9), background='#E8EEE9', foreground='#0D3B2E', borderwidth=0, font=('Segoe UI', 10, 'bold'), focusthickness=2, focuscolor='#C85A32')
        style.map('TButton', background=[('active', '#D6E5DA'), ('pressed', '#C6DACE'), ('disabled', '#E2DDD6')], foreground=[('disabled', '#4C5E53')])
        style.configure('Primary.TButton', padding=(20, 10), background='#0D3B2E', foreground='white', font=('Segoe UI', 10, 'bold'))
        style.map('Primary.TButton', background=[('active', '#155641'), ('disabled', '#51695B')], foreground=[('disabled', '#FFFFFF')])
        style.configure('TEntry', fieldbackground='#FFFFFF', foreground='#14221D', bordercolor='#D8DFD9', lightcolor='#D8DFD9', darkcolor='#D8DFD9', padding=8)
        style.map('TEntry', bordercolor=[('focus', '#0D3B2E')], lightcolor=[('focus', '#0D3B2E')], darkcolor=[('focus', '#0D3B2E')])
        style.configure('TCombobox', fieldbackground='#FFFFFF', background='#E8EEE9', foreground='#14221D', selectbackground='#FFFFFF', selectforeground='#14221D', bordercolor='#D8DFD9', padding=7, arrowsize=14)
        style.map('TCombobox', fieldbackground=[('readonly', '#FFFFFF'), ('disabled', '#F0F0ED')], foreground=[('disabled', '#52675D')], bordercolor=[('focus', '#0D3B2E')])
        style.configure('TCheckbutton', background='#FAF8F5', foreground='#14221D', font=('Segoe UI', 10), padding=4)
        style.map('TCheckbutton', background=[('active', '#FAF8F5')], foreground=[('disabled', '#75817A')])
        style.configure('TNotebook', background='#FAF8F5', borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure('TNotebook.Tab', background='#F0EDE7', foreground='#52675D', padding=(18, 10), borderwidth=0, font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#0D3B2E'), ('active', '#DAE8E0')], foreground=[('selected', '#FFFFFF'), ('active', '#0D3B2E')])
        style.map('TNotebook.Tab', padding=[('selected', (18, 10)), ('!selected', (18, 10))])
        style.configure('Horizontal.TProgressbar', background='#C85A32', troughcolor='#E2DDD6', borderwidth=0)
        frame = ttk.Frame(self, padding=(36, 24, 36, 24))
        frame.pack(fill='both', expand=True)
        header = ttk.Frame(frame)
        header.pack(fill='x', pady=(0, 18))
        logo = tk.Canvas(header, width=48, height=48, bg='#FAF8F5', highlightthickness=0)
        logo.pack(side='left', padx=(0, 12))
        logo.create_rectangle(2, 2, 46, 46, fill='#0D3B2E', outline='#0D3B2E')
        logo.create_oval(11, 13, 37, 39, outline='#FAF8F5', width=4)
        logo.create_oval(33, 8, 40, 15, fill='#C85A32', outline='#C85A32')
        ttk.Label(header, text='Orveta', foreground='#0D3B2E', font=('Georgia', 25)).pack(side='left')
        ttk.Label(header, text='  /  mídia sem complicação', foreground='#5A6B62', font=('Segoe UI', 10)).pack(side='left', padx=(8, 0))
        self.language_choice = ttk.Combobox(header, textvariable=self.language, state='readonly', width=12, values=['Português', 'English', 'Español'])
        self.language_choice.pack(side='right')
        self.language_choice.bind('<<ComboboxSelected>>', self.apply_language)
        ttk.Button(header, text='Sobre', command=self.show_about).pack(side='right', padx=(0, 12))
        ttk.Label(frame, text='Baixe somente conteúdo que você tem direito de baixar.', foreground='#52675D', font=('Segoe UI', 9), wraplength=750).pack(side='bottom', anchor='w', pady=(8, 0))
        tabs = ttk.Notebook(frame)
        self.tabs = tabs
        tabs.pack(fill='both', expand=True)
        download_tab = ttk.Frame(tabs, padding=(4, 16))
        convert_tab = ttk.Frame(tabs, padding=(4, 16))
        history_tab = ttk.Frame(tabs, padding=(4, 16))
        options_tab = ttk.Frame(tabs, padding=(4, 16))
        queue_tab = ttk.Frame(tabs, padding=(4, 16))
        tabs.add(download_tab, text='Baixar')
        tabs.add(convert_tab, text='Converter arquivos')
        tabs.add(history_tab, text='Histórico')
        tabs.add(options_tab, text='Opções')
        tabs.add(queue_tab, text='Fila')
        tabs.insert(1, queue_tab)
        ttk.Label(queue_tab, text='Fila de tarefas', font=('Segoe UI', 20, 'bold'), foreground='#0D3B2E').pack(anchor='w')
        ttk.Label(queue_tab, text='As tarefas aguardam a conclusão da operação atual.', wraplength=600).pack(anchor='w', pady=(4, 12))
        self.queue_list = tk.Listbox(queue_tab, font=('Segoe UI', 10), height=14, bg='#FFFFFF', fg='#14221D', selectbackground='#0D3B2E', selectforeground='#FFFFFF', relief='flat', highlightthickness=1, highlightbackground='#E2DDD6', activestyle='none')
        self.queue_list.pack(fill='both', expand=True)
        ttk.Button(queue_tab, text='Remover item selecionado', command=self.remove_queued).pack(anchor='w', pady=12)
        ttk.Button(queue_tab, text='Atualizar mecanismo de download', command=self.update_downloader).pack(anchor='w', pady=4)
        ttk.Button(queue_tab, text='Copiar diagnóstico', command=self.copy_diagnostics).pack(anchor='w', pady=4)
        ttk.Label(queue_tab, text='A atualização usa a ferramenta oficial e requer conexão com a internet.', wraplength=600).pack(anchor='w')
        ttk.Label(options_tab, text='Legendas', font=('Segoe UI', 20, 'bold'), foreground='#0D3B2E').pack(anchor='w')
        ttk.Label(options_tab, text='Escolha idiomas para baixar as legendas disponíveis.', wraplength=600).pack(anchor='w', pady=(4, 16))
        ttk.Checkbutton(options_tab, text='Baixar legendas quando disponíveis', variable=self.subtitle_enabled).pack(anchor='w')
        ttk.Label(options_tab, text='Idiomas (códigos separados por vírgula)').pack(anchor='w', pady=(16, 4))
        ttk.Entry(options_tab, textvariable=self.subtitle_languages).pack(fill='x')
        ttk.Label(options_tab, text='Exemplo: pt.*,en.* — inclui português e inglês.').pack(anchor='w', pady=(4, 16))
        ttk.Label(options_tab, text='Como salvar').pack(anchor='w')
        self.subtitle_choice = ttk.Combobox(options_tab, textvariable=self.subtitle_mode, state='readonly', values=['Arquivo separado', 'Incorporar ao vídeo'])
        self.subtitle_choice.pack(fill='x', pady=(4, 8))
        ttk.Label(options_tab, text='A disponibilidade depende do vídeo e do site. Para incorporar, escolha MP4 ou MKV.', wraplength=600).pack(anchor='w', pady=8)
        ttk.Separator(options_tab).pack(fill='x', pady=12)
        ttk.Checkbutton(options_tab, text='Baixar a playlist inteira (até 100 itens)', variable=self.playlist_enabled).pack(anchor='w')
        ttk.Label(options_tab, text='Limite de velocidade (opcional): exemplos 500K ou 2M por segundo').pack(anchor='w', pady=(12, 4))
        ttk.Entry(options_tab, textvariable=self.rate_limit).pack(fill='x')
        ttk.Label(options_tab, text='Canal de atualização do mecanismo').pack(anchor='w', pady=(12, 4))
        ttk.Combobox(options_tab, textvariable=self.update_channel, state='readonly', values=['stable', 'nightly']).pack(fill='x')
        ttk.Label(options_tab, textvariable=self.downloader_version).pack(anchor='w', pady=(6, 0))
        ttk.Label(history_tab, text='Histórico', font=('Segoe UI', 20, 'bold'), foreground='#0D3B2E').pack(anchor='w')
        ttk.Label(history_tab, text='Downloads e conversões concluídos neste computador.').pack(anchor='w', pady=(4, 12))
        self.history_list = tk.Listbox(history_tab, font=('Segoe UI', 10), height=15, bg='#FFFFFF', fg='#14221D', selectbackground='#0D3B2E', selectforeground='#FFFFFF', relief='flat', highlightthickness=1, highlightbackground='#E2DDD6', activestyle='none')
        self.history_list.pack(fill='both', expand=True)
        ttk.Button(history_tab, text='Abrir pasta', command=self.open_history_folder).pack(anchor='w', pady=12)
        self.refresh_history()
        self.build_converter(convert_tab)
        frame = download_tab
        ttk.Label(frame, text='Baixar vídeos', font=('Segoe UI', 20, 'bold'), foreground='#0D3B2E').pack(anchor='w')
        ttk.Label(frame, text='Salve vídeos e áudios dos seus links em um só lugar.').pack(anchor='w', pady=(4, 18))
        ttk.Label(frame, text='Link do vídeo').pack(anchor='w')
        link_row = ttk.Frame(frame)
        link_row.pack(fill='x', pady=(4, 10))
        self.link_entry = ttk.Entry(link_row, textvariable=self.url)
        self.link_entry.pack(side='left', fill='x', expand=True)
        self.link_entry.bind('<Return>', self.schedule_inspect)
        self.link_entry.bind('<<Paste>>', lambda _event: self.after_idle(self.schedule_inspect))
        self.link_hint = tk.Label(link_row, text='', background='#FFFFFF', foreground='#52675D', font=('Segoe UI', 10), cursor='xterm')
        self.link_hint.bind('<Button-1>', lambda _event: self.link_entry.focus_set())
        self.url.trace_add('write', self.update_link_hint)
        self.update_link_hint()
        ttk.Button(link_row, text='Colar link', command=self.paste_link).pack(side='left', padx=(8, 0))
        self.preview = ttk.Label(frame)
        self.preview.pack(anchor='e')
        actions = ttk.Frame(frame)
        actions.pack(fill='x', pady=(0, 4))
        self.inspect_button = ttk.Button(actions, text='Buscar informações', command=self.inspect)
        self.inspect_button.pack(side='left')
        ttk.Button(actions, text='Adicionar à fila', command=self.queue_download).pack(side='left', padx=8)
        ttk.Label(frame, textvariable=self.details, wraplength=750, foreground='#5A6B62').pack(anchor='w', pady=(8, 12))
        format_row = ttk.Frame(frame)
        format_row.pack(fill='x', pady=(0, 12))
        format_row.columnconfigure(0, weight=1)
        format_row.columnconfigure(1, weight=1)
        ttk.Label(format_row, text='Formato do arquivo').grid(row=0, column=0, sticky='w')
        ttk.Label(format_row, text='Qualidade do vídeo').grid(row=0, column=1, sticky='w', padx=(12, 0))
        format_choice = ttk.Combobox(format_row, textvariable=self.output_format, state='readonly', values=['Vídeo · MP4', 'Vídeo · MKV', 'Vídeo · WebM', 'Áudio · MP3', 'Áudio · M4A', 'Áudio · OPUS', 'Áudio · WAV', 'Áudio · FLAC'])
        self.format_choice = format_choice
        format_choice.grid(row=1, column=0, sticky='ew', pady=(4, 0))
        format_choice.bind('<<ComboboxSelected>>', self.format_changed)
        self.quality_choice = ttk.Combobox(format_row, textvariable=self.mode, state='readonly', values=['Melhor qualidade', 'Até 1080p', 'Até 720p', 'Até 480p'])
        self.quality_choice.grid(row=1, column=1, sticky='ew', padx=(12, 0), pady=(4, 0))
        self.quality_choice.bind('<<ComboboxSelected>>', self.clear_combo_selection)
        ttk.Label(frame, text='Pasta de destino').pack(anchor='w')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=(4, 16))
        ttk.Entry(row, textvariable=self.folder).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='Escolher…', command=self.choose_folder).pack(side='left', padx=(8, 0))
        row = ttk.Frame(frame)
        row.pack(fill='x')
        self.download_button = ttk.Button(row, text='Baixar agora', command=self.download, style='Primary.TButton')
        self.download_button.pack(side='left')
        self.cancel_button = ttk.Button(row, text='Cancelar', command=self.cancel, state='disabled')
        self.cancel_button.pack(side='left', padx=8)
        self.open_output_button = ttk.Button(row, text='Abrir pasta', command=self.open_output_folder, state='disabled')
        self.open_output_button.pack(side='left')
        self.progress = ttk.Progressbar(frame, mode='determinate', maximum=100)
        self.progress.pack(fill='x', pady=(14, 6))
        ttk.Label(frame, textvariable=self.status, wraplength=650).pack(anchor='w')
        self.after_idle(self.link_entry.focus_set)

    def apply_language(self, _event=None):
        language = self.language.get()
        def visit(widget):
            if isinstance(widget, (ttk.Label, ttk.Button, ttk.Checkbutton)) and not str(widget.cget('textvariable')):
                if not hasattr(widget, '_source_text'):
                    widget._source_text = widget.cget('text')
                widget.configure(text=translate(widget._source_text, language))
            for child in widget.winfo_children():
                visit(child)
        visit(self)
        for tab, label in zip(self.tabs.tabs(), ('Baixar', 'Fila', 'Converter arquivos', 'Histórico', 'Opções')):
            self.tabs.tab(tab, text=translate(label, language))
        for combo, variable in ((self.format_choice, self.output_format), (self.convert_choice, self.convert_format), (self.quality_choice, self.mode), (self.subtitle_choice, self.subtitle_mode)):
            if not hasattr(combo, '_source_values'):
                combo._source_values = tuple(combo.cget('values'))
            current = canonical(variable.get())
            combo.configure(values=[translate(value, language) for value in combo._source_values])
            variable.set(translate(current, language))
        self.title('Orveta — ' + translate('Baixar vídeos', language))
        self.link_hint.configure(text=translate('Ex.: https://exemplo.com/video', language))
        for variable in (self.status, self.details, self.convert_status):
            text = variable.get()
            for source, alternatives in __import__('translations').TRANSLATIONS.items():
                if text in (source, *alternatives):
                    variable.set(translate(source, language))
                    break
        if self.video_info is not None:
            self.show_video_info(self.video_info)
        self.refresh_queue()
        self.refresh_history()

    def show_video_info(self, info):
        heights = sorted({f['height'] for f in (info.get('formats') or []) if isinstance(f.get('height'), int)}, reverse=True)
        resolutions = ', '.join(f'{height}p' for height in heights[:6]) or ui_text(self, 'não informadas')
        subtitles = sorted(set(info.get('subtitles') or {}) | set(info.get('automatic_captions') or {}))
        languages = ', '.join(subtitles[:8]) + ('…' if len(subtitles) > 8 else '') if subtitles else ui_text(self, 'não informadas')
        channel = info.get('uploader') or info.get('channel') or ui_text(self, 'Não informado')
        duration = info.get('duration_string') or ui_text(self, 'Não informada')
        title = info.get('title') or ui_text(self, 'Sem título')
        channel_line = ui_text(self, 'Canal: {channel} | Duração: {duration}').format(channel=channel, duration=duration)
        format_line = ui_text(self, 'Resoluções: {resolutions} | Legendas: {languages}').format(resolutions=resolutions, languages=languages)
        self.details.set(f'{title}\n{channel_line}\n{format_line}')

    def build_converter(self, frame):
        ttk.Label(frame, text='Converter arquivos', font=('Segoe UI', 20, 'bold'), foreground='#0D3B2E').pack(anchor='w')
        ttk.Label(frame, text='Transforme vídeos e áudios que estão no seu computador.', wraplength=600).pack(anchor='w', pady=(4, 20))
        ttk.Label(frame, text='Arquivo de origem').pack(anchor='w')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=(4, 18))
        ttk.Entry(row, textvariable=self.local_file).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='Escolher…', command=self.choose_local_file).pack(side='left', padx=(8, 0))
        ttk.Label(frame, text='Formato de saída').pack(anchor='w')
        self.convert_choice = ttk.Combobox(frame, textvariable=self.convert_format, state='readonly', values=['Vídeo · MP4', 'Vídeo · MKV', 'Vídeo · WebM', 'Áudio · MP3', 'Áudio · M4A', 'Áudio · OPUS', 'Áudio · WAV', 'Áudio · FLAC'])
        self.convert_choice.pack(fill='x', pady=(4, 8))
        self.convert_choice.bind('<<ComboboxSelected>>', self.clear_combo_selection)
        ttk.Label(frame, text='Para extrair o áudio de um vídeo, escolha um formato de áudio.', wraplength=600).pack(anchor='w', pady=(0, 18))
        cut = ttk.Frame(frame)
        cut.pack(fill='x', pady=(0, 10))
        ttk.Label(cut, text='Cortar (opcional) — início e fim em segundos').pack(anchor='w')
        ttk.Entry(cut, textvariable=self.trim_start, width=12).pack(side='left', pady=4)
        ttk.Label(cut, text='  até  ').pack(side='left')
        ttk.Entry(cut, textvariable=self.trim_end, width=12).pack(side='left')
        row = ttk.Frame(frame)
        row.pack(fill='x')
        self.convert_button = ttk.Button(row, text='Converter e salvar…', command=self.convert, style='Primary.TButton')
        self.convert_button.pack(side='left')
        self.convert_cancel = ttk.Button(row, text='Cancelar', command=self.cancel, state='disabled')
        self.convert_cancel.pack(side='left', padx=8)
        ttk.Button(frame, text='Converter vários arquivos…', command=self.convert_batch).pack(anchor='w', pady=(10, 0))
        self.convert_progress = ttk.Progressbar(frame, mode='indeterminate')
        self.convert_progress.pack(fill='x', pady=(20, 6))
        ttk.Label(frame, textvariable=self.convert_status, wraplength=600).pack(anchor='w')

    def choose_local_file(self):
        path = filedialog.askopenfilename(title=ui_text(self, 'Escolha um vídeo ou áudio'), filetypes=[(ui_text(self, 'Vídeos e áudios'), '*.mp4 *.mkv *.webm *.mov *.avi *.mpeg *.mpg *.m4v *.mp3 *.m4a *.aac *.wav *.flac *.ogg *.opus *.wma'), (ui_text(self, 'Todos os arquivos'), '*.*')])
        if path:
            self.local_file.set(path)

    def paste_link(self):
        try:
            self.url.set(self.clipboard_get().strip())
            self.schedule_inspect()
        except tk.TclError:
            messagebox.showinfo(ui_text(self, 'Área de transferência'), ui_text(self, 'Não há texto disponível para colar.'))

    def update_link_hint(self, *_args):
        if self.url.get():
            self.link_hint.place_forget()
        else:
            self.link_hint.place(in_=self.link_entry, x=10, rely=0.5, anchor='w')

    def schedule_inspect(self, _event=None):
        if self.inspect_timer is not None:
            self.after_cancel(self.inspect_timer)
        self.inspect_timer = self.after(400, self.run_scheduled_inspect)
        return 'break'

    def run_scheduled_inspect(self):
        self.inspect_timer = None
        if self.busy:
            self.status.set(translate('Aguarde a tarefa atual para buscar informações.', self.language.get()))
        else:
            self.inspect()

    def open_output_folder(self):
        path = Path(getattr(self, 'last_output_path', ''))
        folder = path if path.is_dir() else path.parent
        if folder.is_dir():
            os.startfile(folder)
        else:
            messagebox.showerror(translate('Pasta indisponível', self.language.get()), translate('A pasta não foi encontrada.', self.language.get()))

    def save_preferences(self, *_args):
        try:
            save_json(DATA_DIR / 'preferences.json', {name: canonical(getattr(self, name).get()) if name in ('mode', 'output_format', 'convert_format') else getattr(self, name).get() for name in ('folder', 'mode', 'output_format', 'convert_format', 'language', 'update_channel')})
        except OSError:
            self.status.set('Não foi possível salvar as preferências.')

    def refresh_history(self):
        self.history_list.delete(0, tk.END)
        for item in reversed(self.history):
            self.history_list.insert(tk.END, f"{item.get('time', '')}  |  {ui_text(self, item.get('kind', ''))}  |  {item.get('path', '')}")

    def record_history(self, kind, path):
        self.history.append({'time': datetime.now().strftime('%d/%m/%Y %H:%M'), 'kind': kind, 'path': path})
        self.history = self.history[-500:]
        try:
            save_json(DATA_DIR / 'history.json', self.history)
        except OSError:
            messagebox.showerror(ui_text(self, 'Histórico'), ui_text(self, 'Não foi possível salvar o histórico.'))
        self.refresh_history()

    def open_history_folder(self):
        selection = self.history_list.curselection()
        if not selection:
            return
        path = Path(self.history[-1 - selection[0]]['path'])
        folder = path if path.is_dir() else path.parent
        if folder.is_dir():
            os.startfile(folder)
        else:
            messagebox.showerror(ui_text(self, 'Pasta indisponível'), ui_text(self, 'A pasta não foi encontrada.'))

    def find_ffmpeg(self):
        base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent / 'vendor'
        bundled = base / 'ffmpeg' / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
        ffmpeg = str(bundled) if bundled.exists() else shutil.which('ffmpeg')
        if not ffmpeg:
            if getattr(sys, 'frozen', False):
                title = translate('FFmpeg não encontrado', self.language.get())
                message = translate('O arquivo do FFmpeg não foi encontrado. Reinstale o Orveta. Caminho esperado:', self.language.get())
            else:
                title = translate('FFmpeg não encontrado', self.language.get())
                message = translate('FFmpeg ausente no ambiente de desenvolvimento. Verifique vendor/ffmpeg ou o PATH. Caminho esperado:', self.language.get())
            messagebox.showerror(title, f'{message}\n{bundled}')
        return ffmpeg

    def convert(self):
        if self.busy:
            return
        source = Path(self.local_file.get().strip()).expanduser()
        if not self.local_file.get().strip() or not source.is_file():
            messagebox.showerror(ui_text(self, 'Arquivo inválido'), ui_text(self, 'Escolha um arquivo de vídeo ou áudio existente.'))
            return
        ffmpeg = self.find_ffmpeg()
        if not ffmpeg:
            return
        fmt = self.convert_format.get().rsplit(' ', 1)[-1].lower()
        destination = filedialog.asksaveasfilename(title=ui_text(self, 'Salvar arquivo convertido'), initialdir=str(source.parent), initialfile=f'{source.stem}-convertido.{fmt}', defaultextension=f'.{fmt}', filetypes=[(fmt.upper(), f'*.{fmt}')])
        if not destination:
            return
        target = Path(destination)
        if target.suffix.lower() != f'.{fmt}':
            messagebox.showerror(ui_text(self, 'Extensão inválida'), ui_text(self, 'O arquivo de saída deve terminar em .{format}.').format(format=fmt))
            return
        if target.resolve() == source.resolve() or target.exists():
            messagebox.showerror(ui_text(self, 'Arquivo já existe'), ui_text(self, 'Escolha um nome novo para preservar os arquivos existentes.'))
            return
        try:
            args = self.conversion_command(ffmpeg, source, target, fmt) if hasattr(self, 'conversion_command') else conversion_command(ffmpeg, source, target, fmt)
        except ValueError as exc:
            messagebox.showerror(ui_text(self, 'Tempo inválido'), ui_text(self, str(exc)))
            return
        self.pending_path = str(target)
        self.start(args, 'convert')

    def conversion_command(self, ffmpeg, source, target, fmt):
        start = self.trim_start.get().strip()
        end = self.trim_end.get().strip()
        return conversion_command(ffmpeg, source, target, fmt, start, end)

    def convert_batch(self):
        paths = filedialog.askopenfilenames(title=ui_text(self, 'Escolha os arquivos para converter'))
        if not paths:
            return
        folder = filedialog.askdirectory(title=ui_text(self, 'Escolha a pasta de destino'))
        ffmpeg = self.find_ffmpeg() if folder else None
        if not ffmpeg:
            return
        fmt = self.convert_format.get().rsplit(' ', 1)[-1].lower()
        planned = []
        targets = set()
        for name in paths:
            source = Path(name)
            target = Path(folder) / f'{source.stem}-convertido.{fmt}'
            if target.exists() or target.resolve() == source.resolve() or str(target).casefold() in targets:
                messagebox.showerror(ui_text(self, 'Arquivo já existe'), ui_text(self, 'Escolha outra pasta ou renomeie o arquivo de saída: {name}').format(name=target.name))
                return
            try:
                args = self.conversion_command(ffmpeg, source, target, fmt)
            except ValueError as exc:
                messagebox.showerror(ui_text(self, 'Tempo inválido'), ui_text(self, str(exc)))
                return
            targets.add(str(target).casefold())
            planned.append((args, 'convert', str(target)))
        self.jobs.extend(planned)
        self.refresh_queue()
        self.after_idle(self.run_next_job)


    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder.get())
        if folder:
            self.folder.set(folder)

    def format_changed(self, _event=None):
        if _event is not None:
            self.clear_combo_selection(_event)
        self.quality_choice.configure(state='disabled' if canonical(self.output_format.get()).startswith('Áudio') else 'readonly')

    @staticmethod
    def clear_combo_selection(event):
        event.widget.selection_clear()

    def valid_url(self):
        value = self.url.get().strip()
        parsed = urlparse(value)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            messagebox.showerror(ui_text(self, 'Link inválido'), ui_text(self, 'Informe um link HTTP ou HTTPS completo.'))
            return None
        return value

    def start(self, args, action):
        if self.queueing:
            self.jobs.append((list(args), action, self.folder.get() if action == 'download' else self.pending_path))
            self.refresh_queue()
            if not self.busy:
                self.after_idle(self.run_next_job)
            return
        if self.busy:
            return
        if action in ('download', 'inspect') and not self.runtime_warning_shown:
            host = (urlparse(args[-1]).hostname or '').lower()
            if (host == 'youtu.be' or host == 'youtube.com' or host.endswith('.youtube.com')) and not find_runtime():
                messagebox.showwarning(translate('Runtime JavaScript ausente', self.language.get()), translate('O runtime JavaScript não foi encontrado. O YouTube pode não funcionar corretamente. Reinstale o Orveta.', self.language.get()))
                self.runtime_warning_shown = True
        self.busy = True
        self.cancelled = False
        self.active_action = action
        if action == 'download':
            self.active_args = list(args)
            self.download_retried = self.retrying_download
            self.retrying_download = False
        self.log.info('Operação iniciada: %s', action if action in ('download', 'convert', 'inspect', 'update') else 'outra')
        if action == 'download':
            self.pending_path = args[args.index('-P') + 1]
        self.progress['value'] = 0
        self.open_output_button['state'] = 'disabled'
        self.status.set(translate('Atualizando mecanismo…', self.language.get()) if action == 'update' else ('Analisando vídeo…' if action == 'inspect' else 'Preparando download…'))
        self.inspect_button['state'] = self.download_button['state'] = 'disabled'
        self.convert_button['state'] = 'disabled'
        self.cancel_button['state'] = 'disabled' if action == 'update' else 'normal'
        self.convert_cancel['state'] = 'disabled' if action == 'update' else 'normal'
        if action == 'convert':
            self.convert_status.set('Convertendo arquivo…')
            self.convert_progress.start(12)
        threading.Thread(target=self.worker, args=(args, action), daemon=True).start()

    def queue_download(self):
        self.queueing = True
        try:
            self.download()
        finally:
            self.queueing = False

    def update_downloader(self):
        title, message, args = update_action(self.busy, getattr(sys, 'frozen', False))
        if args is None:
            messagebox.showinfo(ui_text(self, title), ui_text(self, message))
            return
        self.start([self.update_channel.get()], 'update')

    def copy_diagnostics(self):
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent / 'vendor'
        def version(command):
            try:
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5, creationflags=flags)
                return (result.stdout.splitlines() or ['indisponível'])[0] if result.returncode == 0 else 'indisponível'
            except (OSError, subprocess.SubprocessError):
                return 'indisponível'
        try:
            lines = (DATA_DIR / 'logs' / 'orveta.log').read_text(encoding='utf-8').splitlines()[-20:]
        except OSError:
            lines = []
        report = '\n'.join([f'Orveta {get_version()}', f'Windows: {platform.release()} {platform.version()}', f"yt-dlp: {version([str(base / 'yt-dlp.exe'), '--version'])}", f"FFmpeg: {version([str(base / 'ffmpeg' / 'ffmpeg.exe'), '-version'])}", '', *lines])
        self.clipboard_clear()
        self.clipboard_append(report)
        messagebox.showinfo(translate('Diagnóstico', self.language.get()), translate('Diagnóstico copiado para a área de transferência.', self.language.get()))

    def show_about(self):
        window = tk.Toplevel(self)
        window.title(translate('Sobre o Orveta', self.language.get()))
        window.transient(self)
        window.configure(background='#FAF8F5')
        content = ttk.Frame(window, padding=24)
        content.pack(fill='both', expand=True)
        ttk.Label(content, text=f'Orveta {get_version()}', font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(content, text=self.downloader_version.get()).pack(anchor='w', pady=8)
        base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
        ffmpeg = base / 'ffmpeg' / 'ffmpeg.exe' if getattr(sys, 'frozen', False) else base / 'vendor' / 'ffmpeg' / 'ffmpeg.exe'
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run([str(ffmpeg), '-version'], capture_output=True, text=True, timeout=3, creationflags=flags)
            ffmpeg_version = result.stdout.splitlines()[0] if result.returncode == 0 and result.stdout else 'FFmpeg: —'
        except (OSError, subprocess.SubprocessError):
            ffmpeg_version = 'FFmpeg: —'
        ttk.Label(content, text=ffmpeg_version, wraplength=500).pack(anchor='w')
        ttk.Label(content, text=translate('O Orveta usa FFmpeg e QuickJS-NG.', self.language.get())).pack(anchor='w', pady=(8, 0))
        def open_licenses():
            path = base / 'licenses' if getattr(sys, 'frozen', False) else base / 'THIRD_PARTY_NOTICES.md'
            if path.exists():
                os.startfile(path)
            else:
                messagebox.showerror(translate('Licenças', self.language.get()), translate('Os arquivos de licença não foram encontrados.', self.language.get()))
        ttk.Button(content, text=translate('Abrir licenças', self.language.get()), command=open_licenses).pack(anchor='w', pady=(16, 0))

    def read_downloader_version(self):
        base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent / 'vendor'
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run([str(base / 'yt-dlp.exe'), '--version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5, creationflags=flags)
            value = result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else '—'
        except (OSError, subprocess.SubprocessError):
            value = '—'
        self.events.put(('yt_version', value))

    def refresh_queue(self):
        self.queue_list.delete(0, tk.END)
        for args, action, target in self.jobs:
            name = args[-1] if action == 'download' else target
            label = ui_text(self, 'Baixar' if action == 'download' else 'Conversão')
            self.queue_list.insert(tk.END, f'{label}: {name}')

    def remove_queued(self):
        selection = self.queue_list.curselection()
        if selection:
            self.jobs.pop(selection[0])
            self.refresh_queue()

    def run_next_job(self):
        if self.busy or not self.jobs:
            return
        args, action, target = self.jobs.pop(0)
        self.refresh_queue()
        self.pending_path = target
        self.start(args, action)

    def worker(self, args, action):
        if action == 'update':
            try:
                update_binary(Path(sys.executable).resolve().parent / 'yt-dlp.exe', args[0])
                self.events.put(('done', (action, 0, 'Mecanismo atualizado e verificado.')))
            except Exception as exc:
                self.events.put(('done', (action, 1, str(exc))))
            return
        run_worker(self, args, action)

    def inspect(self):
        url = self.valid_url()
        if url:
            self.start(['--no-playlist', '--dump-single-json', '--skip-download', '--', url], 'inspect')

    def load_thumbnail(self, url):
        try:
            if urlparse(url).scheme not in ('http', 'https'):
                return
            with urlopen(Request(url, headers={'User-Agent': 'Orveta'}), timeout=10) as response:
                image_data = response.read(3 * 1024 * 1024 + 1)
            if len(image_data) > 3 * 1024 * 1024:
                return
            base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent / 'vendor'
            ffmpeg = base / 'ffmpeg' / 'ffmpeg.exe'
            result = subprocess.run([str(ffmpeg), '-v', 'error', '-i', 'pipe:0', '-frames:v', '1', '-vf', 'scale=120:68:force_original_aspect_ratio=decrease', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'], input=image_data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if result.returncode == 0 and result.stdout:
                self.events.put(('thumbnail', (url, base64.b64encode(result.stdout).decode('ascii'))))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass

    def download(self):
        url = self.valid_url()
        if not url:
            return
        folder = Path(self.folder.get()).expanduser()
        if not folder.is_dir():
            messagebox.showerror(ui_text(self, 'Pasta inválida'), ui_text(self, 'Escolha uma pasta existente.'))
            return
        ffmpeg = self.find_ffmpeg()
        if not ffmpeg:
            return
        subtitles = self.subtitle_enabled.get()
        try:
            args = build_download_args(
                url, folder, ffmpeg, canonical(self.mode.get()), canonical(self.output_format.get()),
                self.rate_limit.get(), self.playlist_enabled.get(), subtitles,
                self.subtitle_languages.get() if subtitles else '',
                canonical(self.subtitle_mode.get()) if subtitles else '',
            )
        except DownloadOptionError as exc:
            messagebox.showerror(ui_text(self, exc.title), ui_text(self, str(exc)))
            return
        self.start(args, 'download')

    def cancel(self):
        if self.busy:
            self.cancelled = True
            self.status.set('Cancelando…')
            self.convert_status.set('Cancelando…')
            if self.process:
                self.process.terminate()

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == 'progress':
                    self.status.set('Baixando: ' + data)
                    try:
                        self.progress['value'] = float(data.split('%')[0].strip())
                    except ValueError:
                        pass
                elif kind == 'output_path':
                    self.pending_path = data
                elif kind == 'phase':
                    self.status.set('Processando arquivo. Isso pode levar alguns minutos…')
                elif kind == 'thumbnail':
                    thumbnail_url, data = data
                    if thumbnail_url == getattr(self, 'thumbnail_url', None):
                        try:
                            self.thumbnail_image = tk.PhotoImage(data=data)
                            self.preview.configure(image=self.thumbnail_image)
                        except tk.TclError:
                            pass
                elif kind == 'yt_version':
                    self.downloader_version.set(f'yt-dlp: {data}')
                else:
                    action, code, output = data
                    self.log.info('Operação concluída: %s, resultado=%s, cancelada=%s', action if action in ('download', 'convert', 'inspect', 'update') else 'outra', 'sucesso' if code == 0 else 'erro', bool(self.cancelled))
                    self.busy = False
                    self.inspect_button['state'] = self.download_button['state'] = 'normal'
                    self.convert_button['state'] = 'normal'
                    self.cancel_button['state'] = 'disabled'
                    self.convert_cancel['state'] = 'disabled'
                    self.convert_progress.stop()
                    if self.cancelled:
                        self.status.set('Operação cancelada. Arquivos parciais podem permanecer na pasta.')
                        self.convert_status.set('Operação cancelada. Um arquivo parcial pode permanecer na pasta escolhida.')
                    elif code:
                        if should_retry_after_update(action, output, getattr(self, 'download_retried', False), getattr(sys, 'frozen', False)):
                            self.retry_args = self.active_args
                            self.status.set(translate('Falha de extração. Atualizando o mecanismo antes de tentar novamente…', self.language.get()))
                            self.start([self.update_channel.get()], 'update')
                            continue
                        if action == 'update':
                            self.retry_args = None
                        if action == 'convert':
                            self.convert_status.set('Não foi possível converter. Verifique se o arquivo contém vídeo ou áudio compatível.')
                        else:
                            self.status.set('Não foi possível concluir. Verifique o link e tente novamente.')
                        details = ui_text(self, output) if action == 'update' else output[-1800:]
                        messagebox.showerror(ui_text(self, 'Erro'), ui_text(self, friendly_error(output)) + '\n\n' + (details or ui_text(self, 'O processo terminou com erro.')))
                    elif action == 'inspect':
                        try:
                            info = json.loads(output)
                            self.video_info = info
                            self.thumbnail_url = info.get('thumbnail')
                            self.preview.configure(image='')
                            if self.thumbnail_url:
                                threading.Thread(target=self.load_thumbnail, args=(self.thumbnail_url,), daemon=True).start()
                            self.show_video_info(info)
                            self.status.set('Vídeo analisado. Escolha as opções e clique em Baixar agora.')
                        except json.JSONDecodeError:
                            self.status.set('Não foi possível interpretar os dados do vídeo.')
                    elif action == 'update':
                        threading.Thread(target=self.read_downloader_version, daemon=True).start()
                        if self.retry_args is not None:
                            retry_args, self.retry_args = self.retry_args, None
                            self.retrying_download = True
                            self.start(retry_args, 'download')
                            continue
                        self.status.set('Verificação do mecanismo concluída.')
                        messagebox.showinfo(ui_text(self, 'Atualização do mecanismo'), ui_text(self, output[-2000:] or 'Verificação concluída.'))
                    elif action == 'convert':
                        self.convert_status.set('Conversão concluída. O arquivo foi salvo no local escolhido.')
                        self.record_history('Conversão', self.pending_path)
                    else:
                        self.progress['value'] = 100
                        self.status.set('Download concluído.')
                        self.last_output_path = self.pending_path
                        self.open_output_button['state'] = 'normal'
                        self.record_history('Download', self.pending_path)
                    if self.jobs:
                        self.after_idle(self.run_next_job)
                self.apply_status_language()
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def apply_status_language(self):
        for variable in (self.status, self.convert_status):
            value = variable.get()
            if value.startswith('Baixando: '):
                label = {'Português': 'Baixando', 'English': 'Downloading', 'Español': 'Descargando'}[self.language.get()]
                variable.set(label + ': ' + value[len('Baixando: '):])
            else:
                variable.set(translate(value, self.language.get()))

    def close(self):
        if self.busy and getattr(self, 'active_action', None) == 'update':
            messagebox.showinfo(translate('Atualização em andamento', self.language.get()), translate('Aguarde a atualização terminar antes de fechar o Orveta.', self.language.get()))
            return
        if self.busy and not messagebox.askyesno(ui_text(self, 'Sair'), ui_text(self, 'Há uma operação em andamento. Deseja cancelá-la e sair?')):
            return
        if self.process:
            self.process.terminate()
        self.destroy()


