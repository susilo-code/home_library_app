# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
VERIFIKASI — CETAK LABEL RAK (3 × 4 cm dan 4 × 6 cm)
====================================================
Menguji fitur baru "label rak" sekaligus memastikan label buku yang sudah
ada tidak berubah perilakunya.

Yang diperiksa:
  1. Halaman pilih rak (filter, jumlah, tautan menu navbar desktop + mobile)
  2. Lembar cetak: matriks 2 ukuran × 2 orientasi (lebar/tinggi/skala huruf),
     angka CSS netral-locale (titik, bukan koma), aturan @page A4
  3. Nilai parameter tak dikenal / kosong -> kembali ke default (tanpa 500)
  4. Jumlah label = jumlah id, isi label (kode rak, jumlah buku)
  5. "Lompati N label" benar-benar menggeser posisi (slot kosong)
  6. Filter rak: q / status / kosong diuji terhadap hitungan DB, bukan asumsi
  7. Regresi: label buku tetap default 2×3 cm
"""

import re
import sys
from pathlib import Path

import django

_os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.db.models import Count  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402
from django.urls import reverse  # noqa: E402
from django.utils.html import escape  # noqa: E402
from library.models import Shelf  # noqa: E402

# WAJIB di luar TestCase, kalau tidak response.context selalu None
setup_test_environment()

ROOT = Path(__file__).resolve().parents[2]

lulus = 0
gagal: list[str] = []


def cek(nama: str, kondisi: bool, detail: str = "") -> None:
    global lulus
    if kondisi:
        lulus += 1
        print(f"  [OK  ] {nama}" + (f" — {detail}" if detail else ""))
    else:
        gagal.append(nama)
        print(f"  [GAGAL] {nama}" + (f" — {detail}" if detail else ""))


def bagian(judul: str) -> None:
    print()
    print("=" * 78)
    print(f"  {judul}")
    print("=" * 78)


c = Client()
pengguna = User.objects.filter(is_superuser=True).first() or User.objects.first()

print("=" * 78)
print("  VERIFIKASI FITUR — CETAK LABEL RAK (3 × 4 cm & 4 × 6 cm)")
print("=" * 78)
cek("ada akun untuk login", pengguna is not None)
if pengguna is None:
    print("Tidak ada akun di database — jalankan create_user/seed_data dulu.")
    sys.exit(2)
c.force_login(pengguna)
print(f"  Login sebagai: {pengguna.username}")

# ── Fixture: rak uji (idempoten — dibersihkan dulu di awal) ────────────────────
PREFIX = "ZRAK UJI"
Shelf.objects.filter(name__startswith=PREFIX).delete()

rak_kode = Shelf.objects.create(name=f"{PREFIX} Kode A1", code="ZU1",
                                description="rak kayu dekat jendela lantai 2",
                                color_code="#8A4FFF")
rak_tanpa_kode = Shelf.objects.create(name=f"{PREFIX} Tanpa Kode", code="",
                                      description="", color_code="#06B6D4")
rak_nonaktif = Shelf.objects.create(name=f"{PREFIX} Nonaktif", code="ZU3",
                                    description="rak gudang", is_active=False)
RAK_UJI = [rak_kode, rak_tanpa_kode, rak_nonaktif]

print(f"  Fixture: {len(RAK_UJI)} rak uji dibuat (id: {[r.pk for r in RAK_UJI]})")

# ══════════════════════════════════════════════════════════════════════════════
bagian("1. HALAMAN PILIH RAK")
# ══════════════════════════════════════════════════════════════════════════════
r = c.get(reverse("shelf-label-select"))
h = r.content.decode()
cek("pilih rak: HTTP 200", r.status_code == 200, f"status={r.status_code}")
cek("judul halaman 'Cetak Label Rak'", "Cetak Label Rak" in h)
cek("menyebut ukuran 3 × 4 cm", "3 × 4 cm" in h)
cek("menyebut ukuran 4 × 6 cm", "4 × 6 cm" in h)
# Periksa HANYA blok <select name="ukuran"> — halaman ini juga memuat modal
# "Tentang Aplikasi" yang menyebut ukuran label BUKU (2 × 3 cm), jadi memeriksa
# seluruh halaman akan gagal padahal benar.
_blok_ukuran = h.split('name="ukuran"', 1)[-1].split("</select>", 1)[0]
cek("pilihan ukuran label rak hanya 3×4 & 4×6",
    'value="3x4"' in _blok_ukuran and 'value="4x6"' in _blok_ukuran
    and _blok_ukuran.count("<option") == 2,
    f"opsi={_blok_ukuran.count('<option')}")
cek("form memakai action ke lembar cetak", reverse("shelf-label-print") in h)
cek("checkbox pilih-per-rak ada", 'class="pilih-rak' in h)
cek("tombol cetak semua hasil filter ada", 'name="semua" value="1"' in h)
cek("form cetak membawa filter aktif (hidden input q/status)",
    'name="q"' in h and 'name="status"' in h)
_h2 = c.get(reverse("shelf-label-select"),
            {"q": "ZRAK UJI", "status": "aktif"}).content.decode()
cek("nilai filter terisi di hidden input",
    'name="q" value="ZRAK UJI"' in _h2 and 'name="status" value="aktif"' in _h2)
_jml_checkbox = h.count('class="pilih-rak')
cek("jumlah rak di halaman = total_hasil",
    _jml_checkbox == r.context["total_hasil"],
    f"checkbox={_jml_checkbox} total_hasil={r.context['total_hasil']}")
cek("rak uji muncul di daftar", escape(rak_kode.name) in h)
cek("rak tanpa kode ditandai",
    "kode belum diisi" in h and escape(rak_tanpa_kode.name) in h)
cek("rak nonaktif ditandai", "nonaktif" in h and escape(rak_nonaktif.name) in h)

# ── Filter: dibandingkan dengan hitungan DB, bukan asumsi ─────────────────────
kata = "ZRAK UJI Tanpa"
r = c.get(reverse("shelf-label-select"), {"q": kata})
h = r.content.decode()
harap = Shelf.objects.filter(name__icontains=kata).count()
cek(f"filter q='{kata}' → {harap} rak",
    r.context["total_hasil"] == harap and h.count('class="pilih-rak') == harap,
    f"context={r.context['total_hasil']} db={harap}")

harap = Shelf.objects.annotate(n=Count("books")).filter(n=0).count()
r = c.get(reverse("shelf-label-select"), {"kosong": "1"})
cek(f"filter kosong=1 → {harap} rak tanpa buku",
    r.context["total_hasil"] == harap, f"context={r.context['total_hasil']}")

harap = Shelf.objects.filter(is_active=False).count()
r = c.get(reverse("shelf-label-select"), {"status": "nonaktif"})
cek(f"filter status=nonaktif → {harap} rak",
    r.context["total_hasil"] == harap, f"context={r.context['total_hasil']}")

r = c.get(reverse("shelf-label-select"), {"q": "tidak-ada-rak-ini-xyz"})
cek("filter tanpa hasil: halaman tetap tampil", r.status_code == 200)

# ── Sudah login? (halaman ini tidak boleh terbuka untuk tamu) ──────────────────
tamu = Client()
r = tamu.get(reverse("shelf-label-select"))
cek("tamu diarahkan ke login", r.status_code == 302, f"status={r.status_code}")

# ══════════════════════════════════════════════════════════════════════════════
bagian("2. LEMBAR CETAK — MATRIKS 2 UKURAN × 2 ORIENTASI")
# ══════════════════════════════════════════════════════════════════════════════
ids = ",".join(str(x.pk) for x in RAK_UJI)
# (kode, mendatar=(lebar,tinggi), tegak=(lebar,tinggi), skala CSS)
MATRIKS = [
    ("3x4", (4, 3), (3, 4), "1"),
    ("4x6", (6, 4), (4, 6), "1.3"),
]
for kode, mendatar, tegak, skala in MATRIKS:
    for ori, (l, t) in (("mendatar", mendatar), ("tegak", tegak)):
        r = c.get(reverse("shelf-label-print"),
                  {"ids": ids, "ukuran": kode, "orientasi": ori})
        h = r.content.decode()
        cek(f"{kode} {ori}: HTTP 200", r.status_code == 200, f"status={r.status_code}")
        cek(f"{kode} {ori} → {l} × {t} cm",
            f"--lebar-label: {l}cm" in h and f"--tinggi-label: {t}cm" in h)
        m = re.search(r"--skala:\s*([^;]+);", h)
        cek(f"{kode} {ori}: skala CSS '{skala}' (titik, bukan koma)",
            m is not None and m.group(1).strip() == skala,
            f"terbaca={m.group(1).strip() if m else None!r}")
        cek(f"{kode} {ori}: semua calc() pakai var(--skala)",
            "var(--skala)" in h and not re.search(r"calc\([^)]*,\s*\d", h))
        _jml_label = h.count('<span class="aksen">')
        cek(f"{kode} {ori}: jumlah label = jumlah id",
            _jml_label == len(RAK_UJI),
            f"label={_jml_label} id={len(RAK_UJI)}")
        cek(f"{kode} {ori}: ukuran aktif ditandai selected",
            f'value="{kode}" selected' in h and f'value="{ori}" selected' in h)

bawaan = c.get(reverse("shelf-label-print"), {"ids": ids}).content.decode()
cek("tanpa parameter → default 3×4 mendatar (4 × 3 cm)",
    "--lebar-label: 4cm" in bawaan and "--tinggi-label: 3cm" in bawaan)
cek("ada aturan cetak A4", "@page { size: A4" in bawaan)
cek("toolbar disembunyikan saat mencetak",
    ".toolbar { display: none !important; }" in bawaan)
cek("lembar cetak tidak memakai base.html (tanpa navbar)",
    "<nav" not in bawaan and "<!DOCTYPE html>" in bawaan)
cek("kode rak tercetak", "ZU1" in bawaan and "ZU3" in bawaan)
cek("nama rak tanpa kode dipakai sebagai teks utama",
    escape(rak_tanpa_kode.name) in bawaan)
cek("jumlah buku tercetak", "0 buku" in bawaan or " buku" in bawaan)
cek("tanpa rak yang dipilih → pesan kosong, bukan 500",
    "Tidak ada rak yang dipilih" in c.get(reverse("shelf-label-print")).content.decode())

# ── Nilai tak dikenal -> default aman ─────────────────────────────────────────
print()
for aneh in ("99x99", "abc", "", "3X4", "-1", "2x3"):
    r = c.get(reverse("shelf-label-print"), {"ids": ids, "ukuran": aneh})
    h = r.content.decode()
    cek(f"ukuran {aneh!r} → default 4 × 3 cm (HTTP 200)",
        r.status_code == 200 and "--lebar-label: 4cm" in h and "--tinggi-label: 3cm" in h,
        f"status={r.status_code}")
r = c.get(reverse("shelf-label-print"), {"ids": ids, "orientasi": "miring"})
cek("orientasi tak dikenal → mendatar",
    "--lebar-label: 4cm" in r.content.decode())

# ── ids kosong / rusak -> pakai filter (semua rak) ────────────────────────────
r = c.get(reverse("shelf-label-print"), {"semua": "1"})
_jml_label_semua = r.content.decode().count('<span class="aksen">')
cek("semua=1 → semua rak tercetak",
    _jml_label_semua == Shelf.objects.count(),
    f"label={_jml_label_semua} rak={Shelf.objects.count()}")

# ══════════════════════════════════════════════════════════════════════════════
bagian("3. LOMPATI N LABEL & PARAMETER YANG DIBawa SAAT GANTI UKURAN")
# ══════════════════════════════════════════════════════════════════════════════
h = c.get(reverse("shelf-label-print"),
          {"ids": ids, "ukuran": "3x4", "orientasi": "tegak", "mulai": "3"}).content.decode()
_jml_slot = h.count('class="label slot-kosong"')
cek("mulai=3 → 3 slot kosong", _jml_slot == 3,
    f"slot={_jml_slot}")
cek("mulai tidak mengurangi jumlah label",
    h.count('<span class="aksen">') == len(RAK_UJI))
h = c.get(reverse("shelf-label-print"), {"ids": ids, "mulai": "abc"}).content.decode()
_slot_abc = h.count('class="label slot-kosong"')
cek("mulai='abc' → 0 slot (tanpa error)", _slot_abc == 0, f"slot={_slot_abc}")

h = c.get(reverse("shelf-label-print"), {"ids": ids, "ukuran": "4x6"}).content.decode()
cek("pilihan ids tetap dibawa saat ukuran diganti (hidden input)",
    f'name="ids" value="{ids}"' in h)
h = c.get(reverse("shelf-label-print"),
          {"ids": ids, "ukuran": "4x6", "mulai": "2"}).content.decode()
cek("parameter 'mulai' juga dibawa di toolbar", 'name="mulai" value="2"' in h)

# ── "Cetak semua hasil filter" harus mencetak HASIL FILTER, bukan semua rak ───
_harap = Shelf.objects.filter(name__icontains="ZRAK UJI").count()
_lbl = c.get(reverse("shelf-label-print"),
             {"semua": "1", "q": "ZRAK UJI"}).content.decode().count('<span class="aksen">')
cek(f"semua=1 + q → {_harap} label (bukan seluruh rak)",
    _lbl == _harap, f"tercetak={_lbl} harap={_harap}")

_harap = Shelf.objects.filter(is_active=False).count()
_lbl = c.get(reverse("shelf-label-print"),
             {"semua": "1", "status": "nonaktif"}).content.decode().count('<span class="aksen">')
cek(f"semua=1 + status=nonaktif → {_harap} label",
    _lbl == _harap, f"tercetak={_lbl} harap={_harap}")

# ══════════════════════════════════════════════════════════════════════════════
bagian("4. MENU NAVBAR (DESKTOP & MOBILE) + REGRESI LABEL BUKU")
# ══════════════════════════════════════════════════════════════════════════════
dash = c.get(reverse("dashboard")).content.decode()
nav_desktop = dash.split("hidden md:flex items-center gap-6", 1)[-1].split('id="user-menu"', 1)[0]
drawer = dash.split('id="mobile-menu"', 1)[-1].split("<main", 1)[0]
cek("nav desktop memuat tautan label rak",
    "/label-rak/" in nav_desktop and "Label Rak" in nav_desktop,
    f"potongan={nav_desktop[:0]!r}len={len(nav_desktop)}")
cek("drawer mobile memuat tautan label rak",
    "/label-rak/" in drawer and "Label Rak" in drawer, f"len={len(drawer)}")
cek("link label buku tetap ada di kedua nav",
    "/label/cetak/" not in nav_desktop and nav_desktop.count("/label/") >= 1
    and drawer.count("/label/") >= 1)
cek("tidak ada tautan 'label-rak' ganda di nav desktop",
    nav_desktop.count("/label-rak/") == 1, f"jumlah={nav_desktop.count('/label-rak/')}")

# Regresi: label buku tidak boleh ikut berubah
h = c.get(reverse("label-print")).content.decode()
cek("regresi label buku: default tetap 3 × 2 cm (2×3 mendatar)",
    "--lebar-label: 3cm" in h and "--tinggi-label: 2cm" in h)
h = c.get(reverse("label-print"), {"ukuran": "4x5"}).content.decode()
cek("regresi label buku: 4×5 masih 1.5 skala", "--skala: 1.5" in h)

# ══════════════════════════════════════════════════════════════════════════════
bagian("5. BERSIH-BERSIH FIXTURE")
# ══════════════════════════════════════════════════════════════════════════════
dihapus = Shelf.objects.filter(name__startswith=PREFIX).delete()
sisa = Shelf.objects.filter(name__startswith=PREFIX).count()
print(f"  Fixture rak uji dihapus: {dihapus[0]} baris (sisa: {sisa})")
cek("tidak ada sisa rak uji", sisa == 0, f"sisa={sisa}")

print()
print("=" * 78)
total = lulus + len(gagal)
print(f"HASIL AKHIR: {lulus}/{total} pemeriksaan LULUS"
      + (" — SEMUA BAIK" if not gagal else f" — {len(gagal)} GAGAL"))
for g in gagal:
    print(f"  - GAGAL: {g}")
print("=" * 78)
sys.exit(0 if not gagal else 1)
