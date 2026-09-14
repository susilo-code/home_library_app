# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Verifikasi perbaikan batch v1.4.1:
  1. Top bar: tanpa menu Pengguna, tanpa tombol Tambah Buku, tanpa jam digital
  2. Footer "Developed by susilo" + halaman login mencantumkan pengembang
  3. Login: "Statistik Kontribusi" -> "Statistik Buku"
  4. Dashboard: "Kontributor Aktif" -> "User Aktif"; "Buku Anda" -> belum selesai dibaca
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402
from django.urls import reverse  # noqa: E402

from library.models import Book  # noqa: E402

setup_test_environment()
hasil = []


def cek(nama, syarat, info=''):
    hasil.append(bool(syarat))
    print(f'  [{"OK  " if syarat else "GAGAL"}] {nama}' + (f' — {info}' if info else ''))


admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
c = Client()
c.force_login(admin_user)
print(f'Login sebagai: {admin_user.username}\n')

dashboard = c.get(reverse('dashboard')).content.decode()
nav = dashboard.split('hidden md:flex items-center gap-6', 1)[-1][:1000]
menu_mobile = dashboard.split('id="mobile-menu"', 1)[-1][:2000]

print('═' * 78)
print('1. TOP BAR DIBERSIHKAN')
print('═' * 78)
cek('Top bar TIDAK memuat menu "Pengguna"', 'Pengguna' not in nav, nav[:80].replace('\n', ' '))
cek('Top bar TIDAK memuat tombol "+ Tambah Buku"', 'Tambah Buku' not in nav)
cek('Top bar TIDAK memuat jam digital', 'digital-clock' not in dashboard and 'clock-time' not in dashboard)
cek('Top bar tetap memuat Dashboard', 'Dashboard' in nav)
cek('Top bar tetap memuat Katalog Buku', 'Katalog Buku' in nav)
cek('Top bar tetap memuat Cetak Label', 'Cetak Label' in nav)
cek('Menu mobile: tidak ada tombol Tambah Buku', 'Tambah Buku' not in menu_mobile)
cek('Menu mobile: tidak ada menu Kelola Pengguna', 'Kelola Pengguna' not in menu_mobile)
cek('Menu mobile tetap punya Profil & Keluar',
    'Profil Saya' in menu_mobile and 'Keluar' in menu_mobile)
html_form = c.get(reverse('book-create')).content.decode()
cek('Tidak ada sisa elemen jam di halaman lain', 'digital-clock' not in html_form)

# jalan lain untuk menambah buku harus tetap ada
cek('Tombol "Tambah Buku Baru" tersedia di Dashboard', 'Tambah Buku Baru' in dashboard)
katalog = c.get(reverse('book-list')).content.decode()
cek('Tombol "Tambah Buku Baru" tersedia di Katalog', 'Tambah Buku Baru' in katalog)

print()
print('═' * 78)
print('2. FOOTER & KREDIT PENGEMBANG')
print('═' * 78)
cek('Footer memuat "Developed by susilo"', 'Developed by susilo' in dashboard,
    dashboard.split('<footer', 1)[-1][:200].split('</p>')[0][-80:].strip())
cek('Tulisan lama "Dibangun dengan Django" sudah hilang',
    'Dibangun dengan Django' not in dashboard)
halaman_lain = {
    'Katalog': c.get(reverse('book-list')).content.decode(),
    'Pengaturan': c.get(reverse('settings')).content.decode(),
    'Cetak label': c.get(reverse('label-select')).content.decode(),
}
for nama, html in halaman_lain.items():
    cek(f'Footer di halaman {nama} juga memuat kredit pengembang', 'Developed by susilo' in html)

html_login = c.get(reverse('login')).content.decode()
cek('Halaman login mencantumkan "This app is developed by susilo"',
    'This app is developed by susilo' in html_login)

print()
print('═' * 78)
print('3. HALAMAN LOGIN: "Statistik Buku"')
print('═' * 78)
cek('Tulisan "Statistik Buku" tampil', 'Statistik Buku' in html_login)
cek('Tulisan lama "Statistik Kontribusi" sudah hilang', 'Statistik Kontribusi' not in html_login)
cek('Dua bulet lain tidak terganggu',
    'Katalog Koleksi' in html_login and 'Rak &amp; Jenis Dinamis' in html_login)

print()
print('═' * 78)
print('4. KARTU DASHBOARD')
print('═' * 78)
cek('Kartu "User Aktif" tampil (menggantikan Kontributor Aktif)', 'User Aktif' in dashboard)
cek('Tulisan "Kontributor Aktif" sudah hilang', 'Kontributor Aktif' not in dashboard)
cek('Kartu "Belum Selesai Dibaca" tampil', 'Belum Selesai Dibaca' in dashboard)
cek('Tulisan "Buku Anda" sudah hilang', 'Buku Anda' not in dashboard)

ctx = c.get(reverse('dashboard')).context
harusnya = Book.objects.exclude(status=Book.ReadingStatus.COMPLETED).count()
cek('Angka "belum selesai dibaca" benar sesuai database',
    ctx['belum_selesai'] == harusnya,
    f"halaman={ctx['belum_selesai']} database={harusnya} (total buku={Book.objects.count()})")
selesai = Book.objects.filter(status=Book.ReadingStatus.COMPLETED).count()
cek('Perhitungan: total buku = selesai + belum selesai',
    selesai + harusnya == Book.objects.count(),
    f'{selesai} + {harusnya} = {Book.objects.count()}')

print()
print('═' * 78)
total, ok = len(hasil), sum(hasil)
print(f'HASIL AKHIR: {ok}/{total} pemeriksaan LULUS' + (' — SEMUA BAIK ✅' if ok == total else f' — {total - ok} GAGAL ❌'))
print('═' * 78)
sys.exit(0 if ok == total else 1)
