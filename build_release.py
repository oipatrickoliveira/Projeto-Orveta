"""Build Orveta in a dedicated clean workspace and checksum its installer."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def reset_build_directory(path):
    resolved = path.resolve()
    allowed = {(ROOT / 'build' / 'release-build').resolve(), (ROOT / 'dist' / 'release-build').resolve()}
    if resolved not in allowed:
        raise ValueError('Refusing to clear an unexpected build directory')
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iscc', default=r'C:\Projetos\ISCC.exe', help='Path to the Inno Setup compiler')
    args = parser.parse_args()
    version = (ROOT / 'version.txt').read_text(encoding='utf-8').strip()
    pieces = version.split('.')
    if len(pieces) != 3 or not all(p.isdigit() for p in pieces):
        raise ValueError('version.txt must contain a three-part numeric version')
    version_tuple = ', '.join([*pieces, '0'])
    build = ROOT / 'build' / 'release-build'
    dist = ROOT / 'dist' / 'release-build'
    reset_build_directory(build)
    reset_build_directory(dist)
    licenses = build / 'licenses'
    licenses.mkdir()
    shutil.copyfile(Path(sys.base_prefix) / 'LICENSE.txt', licenses / 'Python-LICENSE.txt')
    tk_licenses = sorted((Path(sys.base_prefix) / 'tcl').glob('tk*/demos/license.terms'))
    if not tk_licenses:
        raise FileNotFoundError('Tcl/Tk license not found in the Python installation')
    shutil.copyfile(tk_licenses[-1], licenses / 'Tcl-Tk-LICENSE.txt')
    metadata = build / 'version_info.txt'
    metadata.write_text(f"""VSVersionInfo(ffi=FixedFileInfo(filevers=({version_tuple}), prodvers=({version_tuple}), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('CompanyName', 'Orveta'), StringStruct('FileDescription', 'Orveta'), StringStruct('FileVersion', '{version}'), StringStruct('ProductName', 'Orveta'), StringStruct('ProductVersion', '{version}'), StringStruct('OriginalFilename', 'Orveta.exe')])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])""", encoding='utf-8')
    cert = os.environ.get('ORVETA_CERT_FILE')
    password = os.environ.get('ORVETA_CERT_PASSWORD')
    if bool(cert) != (password is not None):
        raise ValueError('Set both ORVETA_CERT_FILE and ORVETA_CERT_PASSWORD, or neither')
    if not cert:
        print('Aviso: build sem assinatura digital; configure ORVETA_CERT_FILE e ORVETA_CERT_PASSWORD para assinar.', flush=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed', '--name', 'Orveta', '--icon', str(ROOT / 'orveta.ico'), '--version-file', str(metadata), '--add-data', f'{ROOT / "orveta.ico"};.', '--add-data', f'{ROOT / "version.txt"};.', '--workpath', str(build / 'work'), '--specpath', str(build), '--distpath', str(dist), str(ROOT / 'app.py')], cwd=ROOT, check=True)
    compiler = [args.iscc]
    if cert:
        subprocess.run([sys.executable, str(ROOT / 'sign_file.py'), str(dist / 'Orveta' / 'Orveta.exe')], cwd=ROOT, check=True)
        compiler += ['/DSignedBuild', f'/SOrveta="{sys.executable}" "{ROOT / "sign_file.py"}" $f']
    subprocess.run([*compiler, str(ROOT / 'installer.iss')], cwd=ROOT, check=True)
    installer = ROOT / 'release' / f'Orveta-Instalador-{version}.exe'
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    (installer.parent / f'{installer.name}.sha256').write_text(f'{digest}  {installer.name}\n', encoding='ascii')
    print(f'Instalador: {installer}\nSHA-256: {digest}')


if __name__ == '__main__':
    main()
