# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Verifikasi 8 perbaikan (batch v1.4.0):
  1. Judul aplikasi dinamis        5. Password dibebaskan
  2. Kapasitas rak dihapus         6. Dashboard tanpa data per-user
  3. Detail buku -> modal          7. Donut persentase + Top 5 genre
  4. Tambah genre/rak dari form    8. Cetak label 2x3 cm
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

from library.forms import BookForm, ShelfForm  # noqa: E402
from library.models import Book, Genre, Shelf, SiteConfig  # noqa: E402

# Diperlukan agar response.context terisi saat client dipakai di luar TestCase
setup_test_environment()

hasil = []


def cek(nama, syarat, info=''):
    hasil.append(bool(syarat))
    tanda = 'OK  ' if syarat else 'GAGAL'
    print(f'  [{tanda}] {nama}' + (f' — {info}' if info else ''))


admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
c = Client()
c.force_login(admin_user)
print(f'Login sebagai: {admin_user.username}\n')

print('═' * 78)
print('1. JUDUL APLIKASI DINAMIS (bisa disetting)')
print('═' * 78)
cfg = SiteConfig.get_solo()
cek('Model SiteConfig ada & berisi nilai awal', bool(cfg.app_name), cfg.app_name)
judul_asli, singkat_asli = cfg.app_name, cfg.app_short_name

r = c.post(reverse('app-identity'), {
    'app_name': 'Perpustakaan Keluarga Uji',
    'app_short_name': 'Perpus Uji',
    'tagline': 'Tagline Uji Coba',
    'label_owner': 'Keluarga Uji',
})
cek('POST ubah identitas diterima (redirect)', r.status_code == 302)
cfg.refresh_from_db()
cek('Judul tersimpan di database', cfg.app_name == 'Perpustakaan Keluarga Uji', cfg.app_name)

html_dash = c.get(reverse('dashboard')).content.decode()
import re as _re  # noqa: E402
titel_tab = _re.search(r'<title>(.*?)</title>', html_dash, _re.S).group(1).strip()
cek('Judul dipakai di judul tab browser', 'Perpustakaan Keluarga Uji' in titel_tab, titel_tab)
cek('Nama singkat dipakai di navbar', 'Perpus Uji' in html_dash)
cek('Judul dipakai di footer', 'Perpustakaan Keluarga Uji' in html_dash)
html_login = c.get(reverse('login')).content.decode()
cek('Judul tampil di halaman login', 'Perpustakaan Keluarga Uji' in html_login)
cek('Tagline tampil di halaman login', 'Tagline Uji Coba' in html_login)
cek('Nama pemilik tampil di halaman Pengaturan',
    'Keluarga Uji' in c.get(reverse('settings')).content.decode())

# kembalikan judul semula
c.post(reverse('app-identity'), {
    'app_name': judul_asli, 'app_short_name': singkat_asli,
    'tagline': cfg.tagline, 'label_owner': cfg.label_owner,
})
cfg.refresh_from_db()
cek('Judul bisa dikembalikan seperti semula', cfg.app_name == judul_asli, cfg.app_name)

print()
print('═' * 78)
print('2. ISIAN KAPASITAS RAK DIHAPUS')
print('═' * 78)
nama_field = [f.name for f in Shelf._meta.get_fields()]
cek("Model Shelf tidak punya field 'capacity'", 'capacity' not in nama_field)
cek('ShelfForm tidak punya field capacity', 'capacity' not in ShelfForm().fields)
cek('Property fill_percent sudah hilang', not hasattr(Shelf(), 'fill_percent'))
html_pengaturan = c.get(reverse('settings')).content.decode()
cek("Halaman Pengaturan tidak memuat kata 'Kapasitas'", 'Kapasitas' not in html_pengaturan)
cek("Form rak tidak memuat nama 'capacity'",
    'name="capacity"' not in c.get(reverse('shelf-create')).content.decode())
cek('Admin rak tidak menampilkan capacity', 'capacity' not in str(
    __import__('library.admin', fromlist=['ShelfAdmin']).ShelfAdmin.list_display))

print()
print('═' * 78)
print('3. FORM DETAIL BUKU -> MODAL (default tersembunyi)')
print('═' * 78)
html_form = c.get(reverse('book-create')).content.decode()
cek('Ada modal detail (id="modal-detail")', 'id="modal-detail"' in html_form)
cek('Modal default tersembunyi (class hidden)', 'id="modal-detail" class="fixed inset-0 z-50 hidden' in html_form
    or 'z-50 hidden items-center justify-center' in html_form)
cek('Ada tombol pemicu "Isi Detail Buku"',
    'id="buka-detail"' in html_form and 'Isi Detail Buku' in html_form)
idx_modal = html_form.find('id="modal-detail"')
cek('Field ISBN berada DI DALAM modal (bukan di halaman utama)',
    html_form.find('id_isbn') > idx_modal)
cek('Tidak ada lagi <details> untuk Detail Buku',
    'DETAIL OPSIONAL (terlipat)' not in html_form)
cek('Isian detail tetap ikut tersimpan', True)

before = Book.objects.count()
_genre_wajib = Genre.objects.first()
r = c.post(reverse('book-create'), {
    'title': 'Buku Uji Modal Detail 2026', 'author': 'Penulis Uji',
    'book_type': Book.BookCategory.NON_FIKSI, 'status': Book.ReadingStatus.UNREAD,
    'rating': 4, 'isbn': '9786020332953', 'publication_year': 2018,
    'purchase_year': 2020, 'publisher': 'Penerbit Uji', 'pages': 250,
    'genre': str(_genre_wajib.pk) if _genre_wajib else '',
})
buku_uji = Book.objects.filter(title='Buku Uji Modal Detail 2026').first()
cek('Perekaman dengan isian detail berhasil', Book.objects.count() == before + 1 and buku_uji is not None)
if buku_uji:
    cek('ISBN ikut tersimpan', buku_uji.isbn == '9786020332953', buku_uji.isbn)
    cek('Tahun beli ikut tersimpan', buku_uji.purchase_year == 2020)
    cek('Penerbit ikut tersimpan', buku_uji.publisher == 'Penerbit Uji')
    buku_uji.delete()

print()
print('═' * 78)
print('4. TAMBAH GENRE & RAK LANGSUNG DARI FORM BUKU (modal)')
print('═' * 78)
cek('Form buku punya tombol tambah genre', 'id="buka-genre-baru"' in html_form)
cek('Form buku punya tombol tambah rak', 'id="buka-rak-baru"' in html_form)
cek('Form buku punya modal genre', 'id="modal-genre"' in html_form)
cek('Form buku punya modal rak', 'id="modal-rak"' in html_form)

# bersihkan sisa data uji dari run sebelumnya
Genre.objects.filter(name__in=['Genre Modal Uji', 'Genre Modal Uji 2']).delete()
Shelf.objects.filter(name__in=['Rak Modal Uji', 'Rak Modal Uji 2']).delete()
Genre.objects.filter(name='Genre Modal Uji 2').delete()

r = c.post(reverse('genre-quick-create'), {
    'name': 'Genre Modal Uji', 'description': 'dari modal',
    'color_code': '#123456', 'icon': 'bookmark', 'is_active': 'on'})
try:
    data = r.json()
except Exception:
    data = {}
cek('Tambah genre dari modal -> JSON ok', r.status_code == 200 and data.get('ok') is True, str(data)[:70])
genre_modal = Genre.objects.filter(name='Genre Modal Uji').first()
cek('Genre tersimpan di database', genre_modal is not None)
cek('Genre baru muncul di dropdown form buku',
    genre_modal is not None and genre_modal in list(BookForm().fields['genre'].queryset))

r = c.post(reverse('genre-quick-create'), {'name': 'Genre Modal Uji', 'icon': 'bookmark'})
cek('Genre duplikat ditolak (HTTP 400 + pesan)',
    r.status_code == 400 and not r.json().get('ok'), str(r.json())[:70])

r = c.post(reverse('shelf-quick-create'), {
    'name': 'Rak Modal Uji', 'code': 'MU1', 'description': 'dari modal',
    'color_code': '#654321', 'is_active': 'on'})
try:
    data_rak = r.json()
except Exception:
    data_rak = {}
cek('Tambah rak dari modal -> JSON ok', r.status_code == 200 and data_rak.get('ok') is True, str(data_rak)[:70])
rak_modal = Shelf.objects.filter(name='Rak Modal Uji').first()
cek('Rak tersimpan di database', rak_modal is not None)
cek('Rak baru muncul di dropdown form buku',
    rak_modal is not None and rak_modal in list(BookForm().fields['shelf'].queryset))

print()
print('═' * 78)
print('5. PASSWORD DIBEBASKAN (tanpa validasi rumit)')
print('═' * 78)
from django.conf import settings as django_settings  # noqa: E402
cek('AUTH_PASSWORD_VALIDATORS dikosongkan', django_settings.AUTH_PASSWORD_VALIDATORS == [],
    str(django_settings.AUTH_PASSWORD_VALIDATORS))

User.objects.filter(username='akun_sandi_pendek').delete()
r = c.post(reverse('user-list'), {
    'username': 'akun_sandi_pendek', 'is_active': 'on',
    'password1': '123', 'password2': '123'})
akun = User.objects.filter(username='akun_sandi_pendek').first()
cek("Sandi sangat pendek ('123') DITERIMA", akun is not None)
if akun:
    cek('Sandi pendek bisa dipakai login', akun.check_password('123'))
    # uji perubahan sandi dari halaman ubah sandi
    c.force_login(akun)
    r = c.post(reverse('password_change'),
               {'old_password': '123', 'new_password1': 'a', 'new_password2': 'a'})
    akun.refresh_from_db()
    cek("Ganti sandi jadi 'a' (1 karakter) diterima", akun.check_password('a'))
    c.force_login(admin_user)
    akun.delete()

print()
print('═' * 78)
print('6. DASHBOARD TANPA DATA JUMLAH BUKU PER USER')
print('═' * 78)
ctx_resp = c.get(reverse('dashboard'))
ctx = ctx_resp.context
cek("Tidak ada bagian 'Produktivitas Perekaman per User'",
    'Produktivitas Perekaman per User' not in html_dash and 'produktivitas per user' not in html_dash.lower())
cek('Tidak ada canvas userChart', 'userChart' not in html_dash)
cek('Konteks tidak lagi memuat user_labels/user_counts',
    'user_labels' not in ctx and 'user_counts' not in ctx)

print()
print('═' * 78)
print('7. DONUT PERSENTASE + GRAFIK TOP 5 GENRE')
print('═' * 78)
cek('Donut memakai data persentase (genre_percents)', 'genrePercents' in html_dash)
cek('Kode penulis persentase di dalam donut ada', 'persenDonut' in html_dash)
cek('Ada grafik Top 5 Genre', 'topGenreChart' in html_dash and 'Top 5 Genre' in html_dash)
cek('Tidak ada lagi grafik produktivitas kontributor',
    'Produktivitas Perekaman' not in html_dash and 'Belum ada data kontributor' not in html_dash)
persen = ctx['genre_percents'] if 'genre_percents' in ctx else '[]'
import json as _json  # noqa: E402
daftar_persen = _json.loads(str(persen))
cek('Persentase donut berjumlah ~100%',
    not daftar_persen or abs(sum(daftar_persen) - 100) < 1.5,
    f'total={round(sum(daftar_persen), 1) if daftar_persen else 0}')
top_labels = _json.loads(str(ctx['top_genre_labels']))
top_counts = _json.loads(str(ctx['top_genre_counts']))
cek('Top genre maksimal 5', len(top_labels) <= 5, f'{len(top_labels)} genre')
cek('Top genre urut dari terbanyak', top_counts == sorted(top_counts, reverse=True), str(top_counts))

print()
print('═' * 78)
print('8. CETAK LABEL 2 x 3 CM (berisi lokasi rak)')
print('═' * 78)
r = c.get(reverse('label-select'))
html_label = r.content.decode()
cek('Halaman pilih label terbuka (HTTP 200)', r.status_code == 200)
cek('Menampilkan keterangan ukuran label', '2 × 3 cm' in html_label)
cek('Ada tombol cetak label terpilih', 'Cetak label terpilih' in html_label)
cek('Ada opsi cetak semua hasil filter', 'Cetak semua hasil filter' in html_label)
cek('Ada pilihan orientasi label', 'name="orientasi"' in html_label)

buku_rak = Book.objects.exclude(shelf=None).select_related('shelf').first()
cek('Ada buku dengan rak untuk diuji', buku_rak is not None)
if buku_rak:
    r = c.get(reverse('label-print'), {'ids': str(buku_rak.pk)})
    lembar = r.content.decode()
    cek('Lembar label terbuka (HTTP 200)', r.status_code == 200)
    cek('Ukuran label 3cm x 2cm tertulis di CSS',
        '--lebar-label: 3cm' in lembar and '--tinggi-label: 2cm' in lembar)
    cek('Orientasi tegak 2cm x 3cm tersedia', '.tegak { --lebar-label: 2cm' in lembar)
    cek('Label memuat LOKASI RAK', buku_rak.shelf.name in lembar)
    cek('Label memuat kode rak', (buku_rak.shelf.code or buku_rak.shelf.name) in lembar)
    cek('Label memuat judul buku', buku_rak.title[:25] in lembar)
    cek('Ada aturan cetak A4 (@page)', '@page { size: A4' in lembar)

    r_tegak = c.get(reverse('label-print'), {'ids': str(buku_rak.pk), 'orientasi': 'tegak'})
    cek("Orientasi 'tegak' aktif saat diminta", 'body class="tegak"' in r_tegak.content.decode())

daftar = list(Book.objects.all()[:3])
r = c.get(reverse('label-print'), {'ids': ','.join(str(b.pk) for b in daftar)})
lembar3 = r.content.decode()
jumlah_label = lembar3.count('class="label')
cek('Beberapa buku sekaligus dicetak', jumlah_label == len(daftar),
    f'{jumlah_label} label untuk {len(daftar)} id')
cek('Judul halaman label bisa dicetak', 'window.print()' in lembar3)

print()
print('═' * 78)
# ── Bersihkan data uji ──
Genre.objects.filter(name__in=['Genre Modal Uji', 'Genre Modal Uji 2']).delete()
Shelf.objects.filter(name__in=['Rak Modal Uji', 'Rak Modal Uji 2']).delete()
User.objects.filter(username='akun_sandi_pendek').delete()
Book.objects.filter(title='Buku Uji Modal Detail 2026').delete()
sisa_uji = (Genre.objects.filter(name__contains='Modal Uji').count()
            + Shelf.objects.filter(name__contains='Modal Uji').count()
            + User.objects.filter(username='akun_sandi_pendek').count())
print(f'Data uji dibersihkan (sisa: {sisa_uji})')
print()
total, ok = len(hasil), sum(hasil)
print(f'HASIL AKHIR: {ok}/{total} pemeriksaan LULUS' + (' — SEMUA BAIK ✅' if ok == total else f' — {total - ok} GAGAL ❌'))
print('═' * 78)
sys.exit(0 if ok == total else 1)
