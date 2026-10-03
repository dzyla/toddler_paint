"""Which app file the checks drive. Defaults to write_v6.html; set ART_APP to override."""
import os
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / os.environ.get('ART_APP', 'write_v6.html')
APP_URL = APP_PATH.as_uri()
