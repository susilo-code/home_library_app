# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Verifikasi v2 — perubahan lanjutan Hirunaza's Library Information System:
  1. Jenis buku dikunci: hanya Fiksi & Non-Fiksi
  2. Genre/Kategori dinamis (CRUD dari Pengaturan)
  3. Field baru: Tahun Beli (+validasi)
  4. Tombol simpan terlihat tanpa scroll (bar aksi melayang)
  5. Kutipan Imam Syafi'i di halaman login

Jalankan: .venv/Scripts/python.exe verify_features_v2.py
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.utils.html import escape as html_escape  # noqa: E402
from django.template.loader import get_template  # noqa: E402
from django.test import Client  # noqa: E402

import library.models as models  # noqa: E402
from library.forms import BookForm  # noqa: E402
from library.models import Book, Genre, Shelf  # noqa: E402

hasil = []


def cek(nama, kondisi, detail=""):
    hasil.append(bool(kondisi))
    print(f"  {'[OK]  ' if kondisi else '[GAGAL]'} {nama}{(' — ' + detail) if detail else ''}")


c = Client()
# Jangan terpaku pada username tertentu: pakai akun yang benar-benar ada
# (username bisa diganti dari panel admin, mis. user1 -> hirunaza).
_akun = User.objects.filter(is_superuser=True).first() or User.objects.first()
if _akun:
    c.force_login(_akun)
    print(f"Login sebagai: {_akun.username} (superuser={_akun.is_superuser})\n")
else:
    print("PERINGATAN: belum ada akun di database — jalankan seed_data atau create_user\n")

buku = Book.objects.first()
genre_contoh = Genre.objects.first()
shelf_contoh = Shelf.objects.first()

print("═" * 78)
print("1. TEMPLATE COMPILE (regresi)")
print("═" * 78)
for t in ["base.html", "dashboard.html", "books/book_list.html", "books/book_form.html",
          "books/book_detail.html", "books/book_confirm_delete.html", "accounts/profile.html",
          "accounts/profile_form.html", "accounts/settings.html", "settings/genre_form.html",
          "settings/shelf_form.html", "settings/confirm_delete.html",
          "registration/login.html", "registration/password_change.html"]:
    try:
        get_template(t)
        cek(t, True)
    except Exception as e:
        cek(t, False, f"{type(e).__name__}: {e}")

print()
print("═" * 78)
print("2. JENIS BUKU HANYA FIKSI & NON-FIKSI")
print("═" * 78)
choices = Book.BookCategory.choices
cek("Hanya ada 2 pilihan jenis buku", len(choices) == 2, str(choices))
cek("Nilainya FIKSI & NON_FIKSI",
    [v for v, _ in choices] == ['FIKSI', 'NON_FIKSI'],
    str([v for v, _ in choices]))
cek("Label 'Fiksi' & 'Non-Fiksi'",
    [l for _, l in choices] == ['Fiksi', 'Non-Fiksi'],
    str([l for _, l in choices]))
cek("Model BookType sudah dihapus", not hasattr(models, 'BookType'))
cek("Semua buku punya jenis valid",
    Book.objects.exclude(book_type__in=['FIKSI', 'NON_FIKSI']).count() == 0,
    f"Fiksi={Book.objects.filter(book_type='FIKSI').count()} "
    f"NonFiksi={Book.objects.filter(book_type='NON_FIKSI').count()}")

f = BookForm()
pilihan_form = [v for v, _ in f.fields['book_type'].choices if v]
cek("Dropdown form hanya 2 opsi (tanpa opsi kosong)", len(pilihan_form) == 2, str(pilihan_form))
f2 = BookForm(data={"title": "Uji Jenis", "author": "Penulis Uji", "genre": genre_contoh.pk,
                    "status": "UNREAD", "rating": 4, "book_type": "SALAH"})
f2.is_valid()
cek("Nilai jenis di luar daftar ditolak", 'book_type' in f2.errors,
    f2.errors.get('book_type', [''])[0] if 'book_type' in f2.errors else '')

r = c.get("/pengaturan/")
html = r.content.decode()
cek("Section 'Jenis Buku' lama TIDAK ada lagi di Pengaturan", 'id="jenis-buku"' not in html)

print()
print("═" * 78)
print("3. GENRE / KATEGORI DINAMIS (bisa disetting)")
print("═" * 78)
cek("Halaman Pengaturan memuat section Genre/Kategori", 'id="genre-kategori"' in html)
cek("Form cepat tambah genre ada", 'action="/pengaturan/genre/tambah/"' in html)
cek("Nama genre dari DB tampil", html_escape(genre_contoh.name) in html, genre_contoh.name)
cek("Kolom slug genre tampil", f"/{genre_contoh.slug}/" in html)

# CREATE
r = c.post("/pengaturan/genre/tambah/", {"name": "Genre UJI-99", "description": "uji dinamis",
                                         "color_code": "#123ABC", "icon": "book", "is_active": "on"})
baru = Genre.objects.filter(name="Genre UJI-99").first()
cek("POST tambah genre → tersimpan di DB", baru is not None)
if baru:
    cek("Slug otomatis dibuat dari nama", baru.slug == 'genre-uji-99', baru.slug)
    cek("Warna tersimpan", baru.color_code == '#123ABC', baru.color_code)

    # Genre baru langsung muncul di dropdown form buku
    f3 = BookForm()
    slug_ids = [str(v) for v in f3.fields['genre'].queryset.values_list('pk', flat=True)]
    cek("Genre baru muncul di dropdown form perekaman", str(baru.pk) in slug_ids)

    # UPDATE
    r = c.post(f"/pengaturan/genre/{baru.pk}/edit/", {"name": "Genre UJI-99 (edit)", "description": "diubah",
                                                      "color_code": "#654321", "icon": "book", "is_active": "on"})
    baru.refresh_from_db()
    cek("POST edit genre → berubah di DB", baru.name == "Genre UJI-99 (edit)" and baru.color_code == '#654321')

    # Duplikat nama ditolak
    r = c.post("/pengaturan/genre/tambah/", {"name": "genre uji-99 (edit)", "color_code": "#000000",
                                             "is_active": "on", "_inline": "1"})
    cek("Nama genre duplikat (beda kapitalisasi) ditolak",
        Genre.objects.filter(name__iexact="genre uji-99 (edit)").count() == 1)

    # DELETE
    r = c.post(f"/pengaturan/genre/{baru.pk}/hapus/")
    cek("POST hapus genre → hilang dari DB", not Genre.objects.filter(pk=baru.pk).exists())

# Nonaktifkan genre → hilang dari dropdown tapi data tetap ada
g_off = Genre.objects.create(name="Genre NONAKTIF UJI", color_code="#000000", is_active=False)
f4 = BookForm()
ids_aktif = [str(v) for v in f4.fields['genre'].queryset.values_list('pk', flat=True)]
cek("Genre nonaktif tidak muncul di dropdown", str(g_off.pk) not in ids_aktif)
g_off.delete()

print()
print("═" * 78)
print("4. FIELD BARU: TAHUN BELI")
print("═" * 78)
cek("Model Book punya field purchase_year", hasattr(Book, 'purchase_year'))
r = c.get("/buku/tambah/")
html_form = r.content.decode()
cek("Field 'Tahun Beli' tampil di form", 'name="purchase_year"' in html_form and 'Tahun Beli' in html_form)

r = c.get("/buku/tambah/")
f5 = BookForm(data={"title": "Uji Tahun Beli Masa Depan", "author": "Penulis Uji",
                    "genre": genre_contoh.pk, "status": "UNREAD", "rating": 4,
                    "book_type": "FIKSI", "purchase_year": 2099})
f5.is_valid()
cek("Tahun beli di masa depan ditolak", 'purchase_year' in f5.errors,
    f5.errors.get('purchase_year', [''])[0] if 'purchase_year' in f5.errors else '')

f6 = BookForm(data={"title": "Uji Tahun Beli Terlalu Awal", "author": "Penulis Uji",
                    "genre": genre_contoh.pk, "status": "UNREAD", "rating": 4,
                    "book_type": "FIKSI", "publication_year": 2015, "purchase_year": 2000})
f6.is_valid()
cek("Tahun beli < tahun terbit ditolak", 'purchase_year' in f6.errors,
    f6.errors.get('purchase_year', [''])[0] if 'purchase_year' in f6.errors else '')

f7 = BookForm(data={"title": "Uji Tahun Beli Valid", "author": "Penulis Uji",
                    "genre": genre_contoh.pk, "status": "UNREAD", "rating": 4,
                    "book_type": "FIKSI", "publication_year": 2015, "purchase_year": 2020})
valid = f7.is_valid()
cek("Tahun beli valid diterima", valid and not f7.errors.get('purchase_year'),
    str(f7.errors) if not valid else 'purchase_year=2020')

# Simpan nyata lewat HTTP
before = Book.objects.count()
r = c.post("/buku/tambah/", {
    "title": "Buku Uji Tahun Beli 2026", "author": "Penulis Tahun Beli",
    "genre": str(genre_contoh.pk), "shelf": str(shelf_contoh.pk), "book_type": "NON_FIKSI",
    "status": "UNREAD", "rating": "4", "purchase_year": "2023",
})
b_buat = Book.objects.filter(title="Buku Uji Tahun Beli 2026").first()
cek("Perekaman menyimpan tahun beli",
    b_buat is not None and b_buat.purchase_year == 2023,
    f"count {before} → {Book.objects.count()}, purchase_year={getattr(b_buat, 'purchase_year', None)}")
if b_buat:
    b_buat.delete()

# Detail buku menampilkan tahun beli
if buku.purchase_year:
    r = c.get(f"/buku/{buku.pk}/")
    cek("Halaman detail menampilkan Tahun Beli", "Tahun Beli" in r.content.decode())

print()
print("═" * 78)
print("5. TOMBOL SIMPAN TERLIHAT TANPA SCROLL")
print("═" * 78)
cek("Ada bar aksi melayang (fixed bottom-0)", "fixed bottom-0" in html_form)
cek("Tombol simpan di bar melayang menunjuk form",
    'form="book-form"' in html_form and 'type="submit"' in html_form)
idx_tombol = html_form.find('form="book-form"')
idx_detail = html_form.find("Detail Buku")
cek("Tombol simpan (bar atas) muncul SEBELUM section opsional",
    idx_tombol != -1 and idx_detail != -1 and idx_tombol < idx_detail,
    f"index tombol={idx_tombol}, index section detail={idx_detail}")
n_tombol = html_form.count('form="book-form"')
cek("Jumlah tombol simpan = 2 (atas + melayang)", n_tombol == 2, f"ditemukan {n_tombol}")
cek("Halaman punya padding bawah agar tidak tertutup bar (pb-28)", "pb-28" in html_form)

print()
print("═" * 78)
print("6. KUTIPAN DI HALAMAN LOGIN")
print("═" * 78)
html_login = c.get("/login/").content.decode()
cek("Nama Imam Syafi'i tampil", "Imam Syafi" in html_login)
cek("Frasa 'Rahimahullah berkata' tampil", "Rahimahullah berkata" in html_login)
cek("Isi kutipan lengkap",
    "tak sanggup menahan lelahnya belajar" in html_login
    and "perihnya kebodohan" in html_login)
cek("Kalimat lama sudah hilang", "Kelola koleksi buku rumah secara kolaboratif" not in html_login)

print()
print("═" * 78)
print("7. REGRESI FITUR SEBELUMNYA")
print("═" * 78)
# Duplikat case-insensitive + spasi ganda
for t, a, label in [
    (buku.title.upper(), buku.author.upper(), "kapitalisasi beda"),
    (buku.title.replace(" ", "   "), buku.author, "spasi ganda"),
]:
    fx = BookForm(data={"title": t, "author": a, "genre": genre_contoh.pk,
                        "status": "UNREAD", "rating": 5, "book_type": "FIKSI"})
    fx.is_valid()
    cek(f"Deteksi duplikat — {label}", bool(fx.duplicate_warning))

# Autocomplete
r = c.get("/api/titles/", {"q": buku.title[:10].swapcase()})
d = r.json()
cek("Autocomplete API berfungsi", r.status_code == 200 and len(d['results']) > 0,
    f"{len(d['results'])} saran, exact={d['exact_match']}")
if d['results']:
    it = d['results'][0]
    cek("Saran autocomplete memuat jenis buku & genre", 'book_type' in it and 'genre' in it,
        f"jenis={it.get('book_type')}, genre={it.get('genre')}")

# Filter katalog jenis buku — verifikasi presisi lewat API (data JSON, bukan HTML)
r = c.get("/buku/", {"book_type": "FIKSI"})
body = r.content.decode()
total_fiksi = Book.objects.filter(book_type='FIKSI').count()

d_fiksi = c.get("/api/books/", {"book_type": "FIKSI", "per_page": 100}).json()
semua_fiksi = all(b['book_type'] == 'Fiksi' for b in d_fiksi['books'])
cek("Filter katalog jenis=FIKSI berhasil (HTTP 200)", r.status_code == 200, f"HTTP {r.status_code}")
cek("Filter FIKSI hanya mengembalikan buku Fiksi",
    semua_fiksi and d_fiksi['pagination']['total_items'] == total_fiksi,
    f"{d_fiksi['pagination']['total_items']} item, semua Fiksi={semua_fiksi}, DB={total_fiksi}")

d_non = c.get("/api/books/", {"book_type": "NON_FIKSI", "per_page": 100}).json()
semua_non = all(b['book_type'] == 'Non-Fiksi' for b in d_non['books'])
cek("Filter NON_FIKSI hanya mengembalikan buku Non-Fiksi", semua_non,
    f"{d_non['pagination']['total_items']} item")
cek("Halaman katalog menampilkan label jenis", "Fiksi" in body)

# Navigasi: Pengaturan hanya lewat menu klik-user (tidak di top bar)
html_dash = c.get("/").content.decode()
_nav = html_dash.split('hidden md:flex items-center gap-6', 1)[-1][:700]
cek("Top bar TIDAK memuat menu 'Pengaturan'", 'Pengaturan' not in _nav,
    f"cuplikan nav: {_nav[:60].strip()}")
cek("Top bar tetap memuat Dashboard & Katalog",
    'Dashboard' in _nav and 'Katalog Buku' in _nav)
cek("'Pengaturan' tetap tersedia di dropdown user", 'Pengaturan' in html_dash)

PAGES = [
    ("/", "Dashboard"), ("/buku/", "Katalog"), ("/buku/tambah/", "Form tambah"),
    (f"/buku/{buku.pk}/", "Detail"), (f"/buku/{buku.pk}/edit/", "Form edit"),
    ("/login/", "Login"), ("/pengaturan/", "Pengaturan"),
    ("/pengaturan/genre/tambah/", "Form genre"), ("/pengaturan/rak/tambah/", "Form rak"),
    ("/profil/", "Profil"), ("/api/stats/", "API stats"), ("/api/books/", "API books"),
    ("/password-change/", "Ubah sandi"),
]
for url, nama in PAGES:
    r = c.get(url)
    cek(f"{nama:16s} {url:30s}", r.status_code == 200, f"HTTP {r.status_code}")

# API stats memuat distribusi jenis buku
d = c.get("/api/stats/").json()
cek("API stats memuat book_type_distribution", 'book_type_distribution' in d,
    str(d.get('book_type_distribution')))

print()
print("═" * 78)
total, ok = len(hasil), sum(hasil)
print(f"HASIL AKHIR: {ok}/{total} pemeriksaan LULUS" + (" — SEMUA BAIK ✅" if ok == total else f" — {total - ok} GAGAL ❌"))
print("═" * 78)

# Keluar dengan kode status agar bisa dipakai di CI / .bat
sys.exit(0 if ok == total else 1)
