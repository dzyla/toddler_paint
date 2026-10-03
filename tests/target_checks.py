"""The shared app target resolves to write_v6.html by default, v5 on request."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.pop('ART_APP', None)
import app_target
assert app_target.APP_PATH.name == 'write_v6.html', app_target.APP_PATH
assert app_target.APP_PATH.exists(), 'write_v6.html must exist'
assert app_target.APP_URL.startswith('file://'), app_target.APP_URL

os.environ['ART_APP'] = 'write_v5.html'
import importlib
importlib.reload(app_target)
assert app_target.APP_PATH.name == 'write_v5.html', app_target.APP_PATH
print('PASS: shared app target defaults to v6 and honours ART_APP')
