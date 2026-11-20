import hashlib
import os
import queue
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import updater
import orveta_ui


def test_extraction_retry_is_once_and_only_when_packaged():
    assert updater.should_retry_after_update('download', 'ERROR: Unable to extract title', False, True)
    assert not updater.should_retry_after_update('download', 'ERROR: Unable to extract title', True, True)
    assert not updater.should_retry_after_update('download', 'ERROR: Unable to extract title', False, False)
    assert not updater.should_retry_after_update('download', 'ERROR: network timeout', False, True)
    assert not updater.should_retry_after_update('inspect', 'ERROR: Unable to extract title', False, True)


def reader(binary, digest=None):
    digest = digest or hashlib.sha256(binary).hexdigest()
    def read(url, _limit):
        return f'{digest}  yt-dlp.exe\n'.encode() if url.endswith('SHA2-256SUMS') else binary
    return read


def test_update_verifies_and_replaces(tmp_path):
    target = tmp_path / 'yt-dlp.exe'
    target.write_bytes(b'old')
    updater.update_binary(target, read_url=reader(b'new'), validate=lambda p: p.read_bytes() == b'new')
    assert target.read_bytes() == b'new'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['yt-dlp.exe']


def test_bad_checksum_preserves_original(tmp_path):
    target = tmp_path / 'yt-dlp.exe'
    target.write_bytes(b'old')
    with pytest.raises(ValueError):
        updater.update_binary(target, read_url=reader(b'new', '0' * 64), validate=lambda _: True)
    assert target.read_bytes() == b'old'


def test_failed_replacement_restores_original(tmp_path, monkeypatch):
    target = tmp_path / 'yt-dlp.exe'
    target.write_bytes(b'old')
    real_replace = os.replace
    count = 0
    def fail_second(src, dst):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError('simulated replacement failure')
        real_replace(src, dst)
    monkeypatch.setattr(updater.os, 'replace', fail_second)
    with pytest.raises(OSError):
        updater.update_binary(target, read_url=reader(b'new'), validate=lambda _: True)
    assert target.read_bytes() == b'old'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['yt-dlp.exe']


def test_download_extraction_failure_schedules_verified_update(monkeypatch):
    monkeypatch.setattr(orveta_ui.sys, 'frozen', True, raising=False)
    events = queue.Queue()
    events.put(('done', ('download', 1, 'ERROR: Unable to extract title')))
    value = SimpleNamespace(get=lambda: 'stable')
    fake = SimpleNamespace(events=events, log=Mock(), busy=True, inspect_button={}, download_button={}, convert_button={}, cancel_button={}, convert_cancel={}, convert_progress=Mock(), cancelled=False, download_retried=False, active_args=['--', 'https://example.com/v'], status=Mock(), language=SimpleNamespace(get=lambda: 'Português'), update_channel=value, start=Mock(), jobs=[], after=Mock(), poll=Mock(), apply_status_language=Mock())
    orveta_ui.App.poll(fake)
    fake.start.assert_called_once_with(['stable'], 'update')
    assert fake.retry_args == ['--', 'https://example.com/v']
