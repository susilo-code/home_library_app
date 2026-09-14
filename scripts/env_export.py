"""
Cetak variabel konfigurasi dari .env dalam format baris `set "VAR=value"`.

Dipakai oleh start.bat supaya port/host bisa diubah cukup dari file .env
tanpa menyentuh file batch. Output-nya di-"call" oleh batch.

Jalankan manual:
    .venv\\Scripts\\python.exe scripts\\env_export.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass  # .env dilewati bila python-dotenv belum terpasang; nilai default dipakai

DEFAULTS = {
    'DJANGO_PORT': '8000',
    'FASTAPI_HOST': '127.0.0.1',
    'FASTAPI_PORT': '8001',
}

for key, default in DEFAULTS.items():
    value = (os.getenv(key) or default).strip()
    # Buang tanda kutip yang mungkin ditulis di .env
    value = value.strip('"').strip("'")
    print(f'set "{key}={value}"')
