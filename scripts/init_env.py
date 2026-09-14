"""
Membuat file .env dari .env.example jika belum ada,
lengkap dengan SECRET_KEY acak yang layak pakai.

Dipakai oleh setup.bat. Bisa juga dijalankan manual:
    .venv\\Scripts\\python.exe scripts\\init_env.py
"""
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXAMPLE = BASE_DIR / '.env.example'
TARGET = BASE_DIR / '.env'
PLACEHOLDER = 'SECRET_KEY=GANTI-DENGAN-SECRET-KEY-ACAK-ANDA-SENDIRI'


def buat_secret_key() -> str:
    try:
        from django.core.management.utils import get_random_secret_key
        return get_random_secret_key()
    except Exception:
        import secrets
        # Fallback: 50 karakter dari alfabet aman Django
        alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        return ''.join(secrets.choice(alphabet) for _ in range(50))


def main() -> int:
    if TARGET.exists():
        print(f'[i] .env sudah ada, tidak diubah: {TARGET}')
        return 0

    if not EXAMPLE.exists():
        print(f'[X] File {EXAMPLE.name} tidak ditemukan. Tidak bisa membuat .env.')
        return 1

    teks = EXAMPLE.read_text(encoding='utf-8')
    teks = teks.replace(PLACEHOLDER, f'SECRET_KEY={buat_secret_key()}')
    teks = re.sub(r'^SECRET_KEY=.*$', lambda m: m.group(0) if 'GANTI-DENGAN' not in m.group(0)
                  else f'SECRET_KEY={buat_secret_key()}', teks, flags=re.MULTILINE)
    TARGET.write_text(teks, encoding='utf-8', newline='\n')
    print(f'[OK] .env dibuat dari .env.example (SECRET_KEY acak sudah diisi).')
    print('     Sesuaikan DB_ENGINE bila ingin memakai MySQL/PostgreSQL.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
