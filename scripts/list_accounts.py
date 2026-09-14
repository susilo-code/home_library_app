"""
Tampilkan akun pengguna yang benar-benar terdaftar di database.

Dipakai oleh start.bat supaya informasi login selalu akurat — username bisa
diganti dari panel admin, jadi daftar ini dibaca langsung dari database
(bukan ditulis mati di file batch).

Jalankan manual:
    .venv\\Scripts\\python.exe scripts\\list_accounts.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import django
    django.setup()
    from django.contrib.auth.models import User

    users = User.objects.order_by('-is_superuser', 'username')
    total = users.count()
    if not total:
        print('      (belum ada akun — jalankan: manage.py seed_data  atau  manage.py createsuperuser)')
    else:
        tampil = list(users[:6])
        baris = []
        for u in tampil:
            tanda = ' [admin]' if u.is_superuser else ''
            baris.append(f'{u.username}{tanda}')
        print('      ' + ', '.join(baris) + (f', … (+{total - len(tampil)} lagi)' if total > len(tampil) else ''))
        print('      Lupa kata sandi? Atur ulang lewat: manage.py changepassword <username>')
except Exception as exc:  # DB belum dimigrasi, driver hilang, dsb.
    print(f'      (tidak bisa membaca daftar akun: {type(exc).__name__})')
    print('      Pastikan sudah menjalankan: manage.py migrate')
