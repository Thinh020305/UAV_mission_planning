"""Build upstream symba 1.2.1 with its existing pure-Python fallback."""
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / 'references/packages'
with tarfile.open(folder / 'symba-1.2.1.tar.gz') as archive:
    archive.extractall(folder, filter='data')
setup = folder / 'symba-1.2.1/setup.py'
text = setup.read_text(encoding='utf-8')
setup.write_text(text.replace("if platform.python_implementation() == 'CPython':",
                             'if False:  # build only: upstream Python fallback'), encoding='utf-8')
print(setup.parent)
