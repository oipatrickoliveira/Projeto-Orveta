import subprocess
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import App, conversion_command

ROOT = Path(__file__).resolve().parent
FFMPEG = Path(os.environ.get('ORVETA_TEST_FFMPEG', ROOT / 'vendor' / 'ffmpeg' / 'ffmpeg.exe'))


class Variable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class ConversionTest(unittest.TestCase):
    def test_playlist_and_rate_options(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            calls = []
            app = SimpleNamespace(valid_url=lambda: 'https://example.com/watch', folder=Variable(directory), find_ffmpeg=lambda: str(FFMPEG), mode=Variable('Melhor qualidade'), output_format=Variable('Vídeo · MP4'), rate_limit=Variable('2M'), playlist_enabled=Variable(True), subtitle_enabled=Variable(False), start=lambda args, action: calls.append((args, action)))
            App.download(app)
            self.assertEqual(calls[0][0][calls[0][0].index('--limit-rate') + 1], '2M')
            self.assertIn('--yes-playlist', calls[0][0])
            self.assertEqual(calls[0][0][calls[0][0].index('--playlist-items') + 1], '1:100')
            app.rate_limit = Variable('0')
            with patch('app.messagebox.showerror') as error:
                App.download(app)
            error.assert_called_once()
            self.assertEqual(len(calls), 1)

    def test_queue_runs_in_order(self):
        first = (['first'], 'convert', 'one.mp4')
        second = (['second'], 'convert', 'two.mp4')
        calls = []
        fake = SimpleNamespace(busy=False, jobs=[first, second], refresh_queue=lambda: None, start=lambda args, action: calls.append((args, action)))
        App.run_next_job(fake)
        self.assertEqual(calls, [(['first'], 'convert')])
        self.assertEqual(fake.pending_path, 'one.mp4')
        self.assertEqual(fake.jobs, [second])
        fake.busy = True
        App.run_next_job(fake)
        self.assertEqual(fake.jobs, [second])

    def test_trim_validation(self):
        command = conversion_command(FFMPEG, 'in.mp4', 'out.mp4', 'mp4', '2', '5')
        self.assertEqual(command[command.index('-t') + 1], '3.0')
        for start, end in [('5', '3'), ('-1', ''), ('nan', '5')]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                conversion_command(FFMPEG, 'in.mp4', 'out.mp4', 'mp4', start, end)

    def test_formats_and_existing_file_protection(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            folder = Path(directory)
            source = folder / 'sample.mp4'
            subprocess.run([str(FFMPEG), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=160x120:rate=10', '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(source)], check=True)
            for label, extension in [('Vídeo · MP4', 'mp4'), ('Vídeo · MKV', 'mkv'), ('Vídeo · WebM', 'webm'), ('Áudio · MP3', 'mp3'), ('Áudio · M4A', 'm4a'), ('Áudio · OPUS', 'opus'), ('Áudio · WAV', 'wav'), ('Áudio · FLAC', 'flac')]:
                with self.subTest(format=extension):
                    target = folder / f'converted.{extension}'
                    calls = []
                    fake = SimpleNamespace(busy=False, local_file=Variable(str(source)), convert_format=Variable(label), find_ffmpeg=lambda: str(FFMPEG), start=lambda args, action: calls.append((args, action)))
                    with patch('app.filedialog.asksaveasfilename', return_value=str(target)):
                        App.convert(fake)
                    self.assertEqual(calls[0][1], 'convert')
                    result = subprocess.run(calls[0][0], capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
                    self.assertGreater(target.stat().st_size, 0)
                    with patch('app.filedialog.asksaveasfilename', return_value=str(target)), patch('app.messagebox.showerror') as error:
                        App.convert(fake)
                    error.assert_called_once()
                    self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
