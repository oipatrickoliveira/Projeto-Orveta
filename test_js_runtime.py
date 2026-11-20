from pathlib import Path

from js_runtime import find_runtime, runtime_args


def test_missing_runtime(tmp_path):
    assert find_runtime(tmp_path, which=lambda _: None) is None
    assert runtime_args(None) == []


def test_bundled_runtime_preferred(tmp_path):
    executable = tmp_path / 'vendor' / 'qjs-0.18.0.exe'
    executable.parent.mkdir()
    executable.write_bytes(b'placeholder')
    result = find_runtime(tmp_path, which=lambda _: 'other-runtime')
    assert result == ('quickjs', str(executable))
    assert runtime_args(result) == ['--js-runtimes', f'quickjs:{executable}']


def test_external_runtime_fallback(tmp_path):
    result = find_runtime(tmp_path, which=lambda name: 'C:/tools/node.exe' if name == 'node' else None)
    assert result == ('node', 'C:/tools/node.exe')
