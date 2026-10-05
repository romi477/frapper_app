import os
import sys
from pathlib import Path

LISTENER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LISTENER_ROOT))

# app.listener builds its API client from these at import time.
os.environ.setdefault('FRAPPER_API_HOST', 'api.test')
os.environ.setdefault('FRAPPER_API_PORT', '4040')
os.environ.setdefault('FRAPPER_USERNAME', 'test-user')
os.environ.setdefault('FRAPPER_PASSWORD', 'test-password')
