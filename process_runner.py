"""Run media subprocesses and publish their output to the UI event queue."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from js_runtime import find_runtime, runtime_args


def run_worker(owner, args, action):
    process = None
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        command = [str(Path(sys.executable).parent / 'yt-dlp.exe')] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'yt_dlp']
        extra = runtime_args(find_runtime()) if action in ('inspect', 'download') else []
        command = args if action == 'convert' else [*command, '--ignore-config', *extra, *args]
        with tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as error_output:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=error_output, text=True, encoding='utf-8', errors='replace', creationflags=flags)
            owner.process = process
            if owner.cancelled:
                process.terminate()
            lines = []
            for line in process.stdout:
                line = line.strip()
                lines.append(line)
                if action == 'download' and line.startswith('PROGRESS:'):
                    owner.events.put(('progress', line[9:]))
                elif action == 'download' and line.startswith('OUTPUT:'):
                    owner.events.put(('output_path', line[7:]))
                elif action == 'download' and line.startswith(('[Merger]', '[VideoConvertor]', '[ExtractAudio]')):
                    owner.events.put(('phase', line))
            code = process.wait()
            error_output.seek(0)
            errors = error_output.read()
            if errors and (action != 'inspect' or code != 0):
                lines.append(errors.strip())
        if owner.process is process:
            owner.process = None
        owner.events.put(('done', (action, code, '\n'.join(lines))))
    except Exception as exc:
        owner.events.put(('done', (action, 1, str(exc))))
    finally:
        if owner.process is process:
            owner.process = None
