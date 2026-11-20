"""Characterization tests for the 0.8 behavior before the module split."""
from types import SimpleNamespace
from unittest.mock import Mock
import queue
import re
import sys

import pytest

import app
import settings_store
import process_runner
from process_runner import run_worker
from updater import update_action
from app_version import get_version


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


@pytest.mark.parametrize(('url', 'expected'), [
    ('https://example.com/video', 'https://example.com/video'),
    (' http://example.com/v ', 'http://example.com/v'),
    ('ftp://example.com/v', None), ('not a url', None), ('https://', None),
])
def test_valid_url(monkeypatch, url, expected):
    monkeypatch.setattr(app.messagebox, 'showerror', lambda *args: None)
    assert app.App.valid_url(SimpleNamespace(url=Value(url))) == expected


@pytest.mark.parametrize(('message', 'expected'), [
    ('sign in to confirm', 'conta'), ('protected with DRM', 'protegido'),
    ('unsupported URL', 'compatível'), ('video unavailable', 'indisponível'),
    ('network is unreachable', 'conectar'), ('requested format is not available', 'qualidade'),
    ('unexpected issue', 'detalhes'),
])
def test_friendly_error(message, expected):
    assert expected in app.friendly_error(message)


def test_json_roundtrip_and_corruption(tmp_path):
    path = tmp_path / 'settings.json'
    assert app.load_json(path, {}) == {}
    app.save_json(path, {'idioma': 'Português'})
    assert app.load_json(path, {}) == {'idioma': 'Português'}
    path.write_text('{broken', encoding='utf-8')
    assert app.load_json(path, []) == []


def test_failed_atomic_replace_preserves_old_json(tmp_path, monkeypatch):
    path = tmp_path / 'settings.json'
    app.save_json(path, {'version': 1})
    def fail_replace(*_args):
        raise OSError('simulated failure')
    monkeypatch.setattr(settings_store.os, 'replace', fail_replace)
    with pytest.raises(OSError):
        app.save_json(path, {'version': 2})
    assert app.load_json(path, {}) == {'version': 1}
    assert sorted(p.name for p in tmp_path.iterdir()) == ['settings.json']


@pytest.mark.parametrize(('quality', 'expected'), [
    ('Melhor qualidade', 'bestvideo+bestaudio/best'),
    ('Até 1080p', 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'),
    ('Até 720p', 'bestvideo[height<=720]+bestaudio/best[height<=720]'),
    ('Até 480p', 'bestvideo[height<=480]+bestaudio/best[height<=480]'),
])
def test_download_options(tmp_path, quality, expected):
    start = Mock()
    obj = SimpleNamespace(valid_url=lambda: 'https://example.com/v', folder=Value(str(tmp_path)), find_ffmpeg=lambda: 'ffmpeg.exe', mode=Value(quality), output_format=Value('Vídeo · MP4'), rate_limit=Value('2M'), playlist_enabled=Value(True), subtitle_enabled=Value(True), subtitle_languages=Value('pt.*,en.*'), subtitle_mode=Value('Incorporar ao vídeo'), start=start)
    app.App.download(obj)
    args, action = start.call_args.args
    assert action == 'download'
    assert args[args.index('-f') + 1] == expected
    assert args[args.index('--limit-rate') + 1] == '2M'
    assert args[args.index('--playlist-items') + 1] == '1:100'
    assert '--embed-subs' in args and '--write-subs' in args


def test_audio_download_and_single_video(tmp_path):
    start = Mock()
    obj = SimpleNamespace(valid_url=lambda: 'https://example.com/v', folder=Value(str(tmp_path)), find_ffmpeg=lambda: 'ffmpeg.exe', mode=Value('Melhor qualidade'), output_format=Value('Áudio · MP3'), rate_limit=Value(''), playlist_enabled=Value(False), subtitle_enabled=Value(False), start=start)
    app.App.download(obj)
    args, _ = start.call_args.args
    assert '--no-playlist' in args
    assert args[args.index('--audio-format') + 1] == 'mp3'


def test_conversion_options_and_invalid_time():
    args = app.conversion_command('ffmpeg', 'source', 'out.mp4', 'mp4', '2', '5')
    assert args[args.index('-t') + 1] == '3.0'
    assert '-n' in args and 'libx264' in args
    with pytest.raises(ValueError):
        app.conversion_command('ffmpeg', 'source', 'out.mp4', 'mp4', '5', '2')


def test_process_runner_emits_completion_without_shell():
    owner = SimpleNamespace(process=None, cancelled=False, events=queue.Queue())
    run_worker(owner, [sys.executable, '-c', "print('finished')"], 'convert')
    assert owner.events.get_nowait() == ('done', ('convert', 0, 'finished'))
    assert owner.process is None


def test_inspection_json_is_not_contaminated_by_stderr(monkeypatch):
    owner = SimpleNamespace(process=None, cancelled=False, events=queue.Queue())
    process = SimpleNamespace(stdout=iter(['{"title": "Example"}\n']), wait=lambda: 0)
    def popen(_command, **kwargs):
        kwargs['stderr'].write('WARNING: optional dependency missing\n')
        return process
    monkeypatch.setattr(process_runner.subprocess, 'Popen', popen)
    monkeypatch.setattr(process_runner, 'find_runtime', lambda: None)
    run_worker(owner, ['--dump-single-json'], 'inspect')
    assert owner.events.get_nowait() == ('done', ('inspect', 0, '{"title": "Example"}'))


def test_update_action_preserves_development_and_busy_behavior():
    assert update_action(True, True)[2] is None
    assert update_action(False, False)[2] is None
    assert update_action(False, True)[2] == ['-U']


def test_application_version_matches_version_file():
    assert re.fullmatch(r'\d+\.\d+\.\d+', get_version())


def test_debounce_replaces_pending_inspection():
    obj = SimpleNamespace(inspect_timer='old', after_cancel=Mock(), after=Mock(return_value='new'), run_scheduled_inspect=Mock())
    assert app.App.schedule_inspect(obj) == 'break'
    obj.after_cancel.assert_called_once_with('old')
    obj.after.assert_called_once_with(400, obj.run_scheduled_inspect)
    assert obj.inspect_timer == 'new'
