# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Verifikasi menyeluruh 4 perbaikan Hirunaza's Library Information System.

Jalankan: .venv/Scripts/python.exe verify_features.py
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.template.loader import get_template  # noqa: E402
from django.test import Client  # noqa: E402

from library.forms import BookForm  # noqa: E402
from library.models import Book, BookType, Shelf, normalize_text  # noqa: E402

PASS, FAIL = "[OK]  ", "[GAGAL]"
hasil = []


def cek(nama, kondisi, detail=""):
    hasil.append(bool(kondisi))
    print(f"  {PASS if kondisi else FAIL} {nama}{(' — ' + detail) if detail else ''}")


TEMPLATES = [
    "base.html", "dashboard.html",
    "books/book_list.html", "books/book_form.html", "books/book_detail.html", "books/book_confirm_delete.html",
    "accounts/profile.html", "accounts/profile_form.html", "accounts/settings.html",
    "settings/shelf_form.html", "settings/booktype_form.html", "settings/confirm_delete.html",
    "registration/login.html",
]

print("═" * 78)
print("1. COMPILE SELURUH TEMPLATE")
print("═" * 78)
for t in TEMPLATES:
    try:
        get_template(t)
        cek(t, True)
    except Exception as e:
        cek(t, False, f"{type(e).__name__}: {e}")

c = Client()
c.login(username="user1", password="password123")
user = User.objects.get(username="user1")
shelf = Shelf.objects.first()
btype = BookType.objects.first()
buku = Book.objects.first()

print()
print("═" * 78)
print("2. PERBAIKAN #1 — HALAMAN LOGIN (Hirunaza's + gambar perpustakaan)")
print("═" * 78)
r = c.get("/login/")
html = r.content.decode()
cek("Halaman login HTTP 200 di /login/", r.status_code == 200, f"HTTP {r.status_code}")
cek("Judul 'Hirunaza's Library Information System' tampil", "Hirunaza" in html and "Library Information System" in html)
cek("Judul di tag <title>", "Hirunaza" in html.split("<title>")[1].split("</title>")[0])
cek("Gambar perpustakaan (library-hero.svg) dipakai", "library-hero.svg" in html)
cek("Palet ungu tua (kelas ink-900 / plum-900)", "bg-ink-900" in html and "plum-900" in html)
cek("Form login ber-styling (input punya class kustom)", "placeholder-purple-200/50" in html)
cek("File SVG hero ada di disk", os.path.exists("static/img/library-hero.svg"))
svg = open("static/img/library-hero.svg", encoding="utf-8").read()
cek("SVG valid & berisi rak buku", "<svg" in svg and "rect" in svg and len(svg) > 5000)
r2 = c.get("/accounts/login/")
cek("Tautan lama /accounts/login/ dialihkan", r2.status_code in (301, 302), f"HTTP {r2.status_code}")

print()
print("═" * 78)
print("3. PERBAIKAN #2 — FORM: DETAIL OPSIONAL TERLIPAT + TOMBOL SIMPAN STICKY")
print("═" * 78)
r = c.get("/buku/tambah/")
html = r.content.decode()
jumlah_details = html.count("<details")
cek("Ada 3 section <details> (detail, sampul, sinopsis)", jumlah_details == 3, f"ditemukan {jumlah_details}")
cek("Section opsional TERTUTUP by default (tanpa atribut open)", 'class="group rounded-xl border' in html and " open>" not in html)
cek("Tombol simpan sticky (sticky bottom-0)", "sticky bottom-0" in html)
cek("Field Rak & Jenis ada di form", 'name="shelf"' in html and 'name="book_type"' in html)
cek("Info 'Field bertanda * wajib diisi' tampil", "wajib diisi" in html)

print()
print("═" * 78)
print("4. PERBAIKAN #3 — AUTOCOMPLETE JUDUL + VALIDASI TIDAK CASE-SENSITIVE")
print("═" * 78)
judul = buku.title
# a. Autocomplete: cari potongan judul (huruf kecil semua, huruf besar semua)
for q, label in [(judul[:12].lower(), "query huruf kecil"), (judul[:12].upper(), "query HURUF BESAR"),
                 ("  " + judul[:12].lower() + "  ", "query dengan spasi berlebih")]:
    r = c.get("/api/titles/", {"q": q})
    data = r.json()
    ada = any(judul.lower() in item["title"].lower() for item in data["results"])
    cek(f"Autocomplete API — {label}", r.status_code == 200 and len(data["results"]) > 0 and ada,
        f"{len(data['results'])} saran")

# b. Exact match terdeteksi walau beda huruf besar/kecil
r = c.get("/api/titles/", {"q": judul.swapcase()})
data = r.json()
cek("Autocomplete menandai exact_match (beda kapitalisasi)", data.get("exact_match") is True)

# c. Duplikat terdeteksi untuk variasi kapitalisasi & spasi ganda
variasi = [
    (judul.upper(), buku.author.upper(), "UPPER semua"),
    (judul.lower(), buku.author.lower(), "lower semua"),
    (judul.title(), buku.author.title(), "Title Case"),
    (f"  {judul}  ", f"  {buku.author}  ", "spasi di ujung"),
    (judul.replace(" ", "   "), buku.author, "spasi ganda di judul"),
    (" ".join(judul.split()), " ".join(buku.author.split()).upper(), "spasi rapi + kapital beda"),
]
for t, a, label in variasi:
    f = BookForm(data={"title": t, "author": a, "genre": buku.genre_id, "status": "UNREAD", "rating": 5})
    f.is_valid()
    cek(f"Duplikat terdeteksi — {label}", bool(f.duplicate_warning))

# d. Buku benar-benar baru tidak kena warning
f = BookForm(data={"title": "Buku Sungguh Baru XYZ-9911", "author": "Penulis Baru QQQ",
                   "genre": buku.genre_id, "status": "UNREAD", "rating": 4})
f.is_valid()
cek("Buku baru TIDAK kena warning duplikat", not f.duplicate_warning)

# e. Field normalisasi tersimpan konsisten
buku.refresh_from_db()
cek("title_normalized sinkron dengan judul",
    buku.title_normalized == normalize_text(buku.title), repr(buku.title_normalized))
cek("author_normalized sinkron dengan penulis",
    buku.author_normalized == normalize_text(buku.author))

print()
print("═" * 78)
print("5. PERBAIKAN #4 — RAK & JENIS BUKU DINAMIS (dari DATABASE)")
print("═" * 78)
cek("Model Shelf punya data", Shelf.objects.count() > 0, f"{Shelf.objects.count()} rak")
cek("Model BookType punya data", BookType.objects.count() > 0, f"{BookType.objects.count()} jenis")
cek("Buku tersambung ke rak", Book.objects.filter(shelf__isnull=False).count() > 0,
    f"{Book.objects.filter(shelf__isnull=False).count()}/{Book.objects.count()} buku punya rak")
cek("Buku tersambung ke jenis", Book.objects.filter(book_type__isnull=False).count() > 0,
    f"{Book.objects.filter(book_type__isnull=False).count()}/{Book.objects.count()} buku punya jenis")

# Halaman pengaturan memuat daftar rak & jenis
r = c.get("/pengaturan/")
html = r.content.decode()
cek("Halaman pengaturan HTTP 200", r.status_code == 200)
cek("Section 'Lokasi Rak Buku' tampil", "Lokasi Rak Buku" in html and 'id="rak-buku"' in html)
cek("Section 'Jenis Buku' tampil", "Jenis Buku" in html and 'id="jenis-buku"' in html)
cek("Nama rak dari DB muncul di halaman", shelf.name in html)
cek("Nama jenis dari DB muncul di halaman", btype.name in html)
cek("Form cepat tambah rak ada", 'action="/pengaturan/rak/tambah/"' in html)
cek("Form cepat tambah jenis ada", 'action="/pengaturan/jenis/tambah/"' in html)

# CRUD via HTTP
r = c.post("/pengaturan/rak/tambah/", {"name": "Rak UJI-COBA-99", "code": "U99",
                                       "capacity": 25, "color_code": "#123456", "is_active": "on"})
baru = Shelf.objects.filter(name="Rak UJI-COBA-99").first()
cek("POST tambah rak → tersimpan di DB", baru is not None and baru.capacity == 25)

if baru:
    r = c.post(f"/pengaturan/rak/{baru.pk}/edit/", {"name": "Rak UJI-COBA-99 (edit)", "code": "U99",
                                                    "capacity": 30, "color_code": "#654321", "is_active": "on"})
    baru.refresh_from_db()
    cek("POST edit rak → berubah di DB", baru.name == "Rak UJI-COBA-99 (edit)" and baru.capacity == 30)

    r = c.post(f"/pengaturan/rak/{baru.pk}/hapus/")
    cek("POST hapus rak → hilang dari DB", not Shelf.objects.filter(pk=baru.pk).exists())

r = c.post("/pengaturan/jenis/tambah/", {"name": "Jenis UJI-COBA-99", "description": "uji",
                                         "color_code": "#abcdef", "is_active": "on"})
baru_t = BookType.objects.filter(name="Jenis UJI-COBA-99").first()
cek("POST tambah jenis buku → tersimpan", baru_t is not None)
if baru_t:
    r = c.post(f"/pengaturan/jenis/{baru_t.pk}/hapus/")
    cek("POST hapus jenis buku → hilang", not BookType.objects.filter(pk=baru_t.pk).exists())

# Rak & jenis benar-benar tersimpan saat perekaman buku baru
before = Book.objects.count()
r = c.post("/buku/tambah/", {
    "title": "Buku Uji Rak Jenis 2026", "author": "Penulis Uji Rak",
    "genre": str(buku.genre_id), "status": "UNREAD", "rating": "4",
    "shelf": str(shelf.pk), "book_type": str(btype.pk),
})
b_buat = Book.objects.filter(title="Buku Uji Rak Jenis 2026").first()
cek("Perekaman buku menyimpan pilihan rak & jenis",
    b_buat is not None and b_buat.shelf_id == shelf.pk and b_buat.book_type_id == btype.pk,
    f"count {before} → {Book.objects.count()}")
if b_buat:
    b_buat.delete()

print()
print("═" * 78)
print("6. HALAMAN LAIN (regresi)")
print("═" * 78)
PAGES = [
    ("/", "Dashboard"), ("/buku/", "Katalog"), ("/buku/tambah/", "Form tambah"),
    (f"/buku/{buku.pk}/", "Detail"), (f"/buku/{buku.pk}/edit/", "Form edit"),
    ("/login/", "Login"), ("/pengaturan/", "Pengaturan"),
    ("/pengaturan/rak/tambah/", "Form rak"), ("/pengaturan/jenis/tambah/", "Form jenis"),
    ("/password-change/", "Ubah kata sandi"),
    ("/profil/", "Profil"), ("/profil/edit/", "Edit profil"),
    ("/api/stats/", "API stats"), ("/api/books/", "API books"),
    ("/api/titles/?q=pra", "API autocomplete"),
    ("/buku/?shelf=" + str(shelf.pk), "Katalog filter rak"),
    ("/buku/?book_type=" + str(btype.pk), "Katalog filter jenis"),
]
for url, nama in PAGES:
    r = c.get(url)
    cek(f"{nama:22s} {url:34s}", r.status_code == 200, f"HTTP {r.status_code}")

# 404 untuk id tidak ada
r = c.get("/buku/999999/")
cek("Buku tidak ada → 404", r.status_code == 404, f"HTTP {r.status_code}")

print()
print("═" * 78)
total, ok = len(hasil), sum(hasil)
print(f"HASIL AKHIR: {ok}/{total} pemeriksaan LULUS" + (" — SEMUA BAIK ✅" if ok == total else f" — {total - ok} GAGAL ❌"))
print("═" * 78)
