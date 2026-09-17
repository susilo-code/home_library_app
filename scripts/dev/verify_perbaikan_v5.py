# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Verifikasi batch v1.4.2:
  1. Menu top bar (Dashboard, Katalog Buku, Cetak Label) punya IKON
  2. Halaman Cetak Label punya tombol TAMBAH BUKU
"""
import os
import re
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402
from django.urls import reverse  # noqa: E402

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
nav = dashboard.split('hidden md:flex items-center gap-6', 1)[-1]
nav = nav[:nav.find('</div>')]          # tepat isi blok navigasi desktop
menu_mobile = dashboard.split('id="mobile-menu"', 1)[-1][:3000]

print('═' * 78)
print('1. IKON PADA MENU TOP BAR')
print('═' * 78)
cek('Blok navigasi ditemukan', len(nav) > 100, f'{len(nav)} karakter')

# tiap tautan nav harus memuat <svg> (ikon)
tautan_nav = re.findall(r'<a href="[^"]+"[^>]*>(.*?)</a>', nav, re.S)
# v1.8: nav desktop kini 4 tautan — Dashboard / Katalog Buku / Cetak Label / Label Rak
# ("Tentang Aplikasi" adalah <button>, bukan <a>, jadi tidak dihitung di sini).
cek('Nav berisi tepat 4 tautan', len(tautan_nav) == 4, f'{len(tautan_nav)} tautan')
for i, isi in enumerate(tautan_nav, 1):
    punya_svg = '<svg' in isi
    teks = re.sub(r'<[^>]+>', ' ', isi)
    teks = re.sub(r'\s+', ' ', teks).strip()
    cek(f'Tautan #{i} punya ikon (svg) — teks: "{teks}"', punya_svg)

cek('Ikon Dashboard = ikon rumah', 'M3 12l2-2m0 0l7-7 7 7' in nav)
cek('Ikon Katalog Buku = ikon buku', 'M12 6.253v13' in nav)
cek('Ikon Cetak Label = ikon label/tag', 'M7 7h.01M7 3h5a1.99' in nav)
cek('Ikon diletakkan dalam bulatan berwarna',
    nav.count('flex h-7 w-7 items-center justify-center rounded-lg bg-purple-100') == 5,
    f"{nav.count('flex h-7 w-7 items-center justify-center rounded-lg bg-purple-100')} bulatan")
cek('Ada efek hover pada ikon', nav.count('group-hover:bg-purple-200') == 5,
    f"{nav.count('group-hover:bg-purple-200')} efek hover")
# v1.8: menu "Label Rak" ditambahkan -> jumlah menu berikon menjadi 5.
# (Angka 4 di sini adalah sisa dari sebelum fitur label rak ada.)
cek('Menu "Label Rak" ada di nav dan berikon sama rapi',
    'Label Rak' in nav and nav.count('/label-rak/') == 1,
    f"jumlah tautan label-rak={nav.count('/label-rak/')}")
# v1.6: menu ke-4 "Tentang Aplikasi" (pemicu modal) wajib berikon sama rapi
cek('Tombol "Tentang Aplikasi" ada di nav', 'id="buka-tentang"' in nav)
cek('Ikon "Tentang Aplikasi" = ikon info',
    'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' in nav)

print()
print('2. IKON DI MENU MOBILE')
print('═' * 78)
for label in ['Dashboard', 'Katalog Buku', 'Cetak Label', 'Profil Saya']:
    blok = menu_mobile.split(label, 1)[0][-700:] if label in menu_mobile else ''
    cek(f'Menu mobile "{label}" punya ikon', '<svg' in blok)

print()
print('═' * 78)
print('3. TOMBOL TAMBAH BUKU DI HALAMAN CETAK LABEL')
print('═' * 78)
r = c.get(reverse('label-select'))
html = r.content.decode()
cek('Halaman Cetak Label terbuka (HTTP 200)', r.status_code == 200)
cek('Ada tombol "Tambah Buku"', 'Tambah Buku' in html)
cek('Tombol mengarah ke form tambah buku',
    f'href="{reverse("book-create")}"' in html, reverse('book-create'))
cek('Tombol punya ikon plus', 'M12 4v16m8-8H4' in html)
cek('Tombol lain (kembali ke katalog) tetap ada', 'Kembali ke Katalog' in html)
cek('Tombol memakai gaya utama (btn-primary)', 'btn-primary' in html)

# dari sisi halaman form buku: tombol + genre/rak juga sudah ada (tidak terpengaruh)
form_html = c.get(reverse('book-create')).content.decode()
cek('Tombol tambah genre masih ada di form buku', 'buka-genre-baru' in form_html)
cek('Tombol tambah rak masih ada di form buku', 'buka-rak-baru' in form_html)

# lembar cetak tidak boleh memuat tombol tambah buku (khusus cetak)
lembar = c.get(reverse('label-print'), {'ids': str(__import__('library.models', fromlist=['Book']).Book.objects.first().pk)}).content.decode()
cek('Lembar cetak TIDAK memuat tombol tambah buku', 'Tambah Buku' not in lembar)
cek('Lembar cetak tetap punya tombol cetak', 'window.print()' in lembar)

print()
print('═' * 78)
total, ok = len(hasil), sum(hasil)
print(f'HASIL AKHIR: {ok}/{total} pemeriksaan LULUS' + (' — SEMUA BAIK ✅' if ok == total else f' — {total - ok} GAGAL ❌'))
print('═' * 78)
sys.exit(0 if ok == total else 1)
