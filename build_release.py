"""Build a source-complete plugin archive without caches or runtime secrets."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
SKIP = {'__pycache__', '.pytest_cache', '.git', '.venv', 'node_modules', '.DS_Store'}

def build():
    destination = ROOT / 'dist/astrbot_plugin_warframe-v0.7.25.zip'
    destination.parent.mkdir(exist_ok=True)
    files = [p for p in ROOT.iterdir() if p.is_file() and (p.suffix in {'.py', '.json', '.yaml', '.md', '.txt'} or p.name == 'LICENSE')]
    for directory in ('assets', 'pages', 'core', 'scripts', 'upstream_tests', 'tests', 'previews'):
        files += [p for p in (ROOT / directory).rglob('*') if p.is_file()]
    files = sorted(p for p in files if not SKIP.intersection(p.relative_to(ROOT).parts)
                   and p.suffix not in {'.pyc', '.pyo'} and p.name != 'wmr-live.png' and not p.name.startswith('sdjk-'))
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, 'astrbot_plugin_warframe/' + path.relative_to(ROOT).as_posix())
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert not any('/vendor/' in name or '/sdjk_' in name for name in archive.namelist())
        for required in ('main.py', 'metadata.yaml', 'requirements.txt', 'LICENSE',
                         'pages/warframe/index.html', 'core/local_ocr_worker.py', 'runtime.py', 'routing.py', 'presentation.py'):
            assert 'astrbot_plugin_warframe/' + required in archive.namelist()
    print(f'{destination}\n{len(files)} files, {destination.stat().st_size / 1024**2:.1f} MiB; ZIP integrity passed')

if __name__ == '__main__':
    build()
