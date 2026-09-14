# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
VERIFIKASI v1.8 — PILIHAN UKURAN LABEL CETAK (2×3, 3×4, 4×5 cm)
=============================================================
Menguji bahwa ukuran label benar-benar berubah di CSS hasil render (lebar,
tinggi, dan skala huruf), orientasi bekerja, nilai tak dikenal jatuh ke default,
dan pilihan pada halaman "Cetak Label" sepadan dengan halaman cetak.
"""

import re
import sys
from pathlib import Path

import django

_os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402
from library.models import Book  # noqa: E402

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
if pengguna:
    c.force_login(pengguna)

buku = Book.objects.exclude(shelf=None).select_related("shelf").first()
if buku is None:
    buku = Book.objects.first()

print("=" * 78)
print("  VERIFIKASI PILIHAN UKURAN LABEL")
print("=" * 78)
cek("ada buku untuk diuji", buku is not None)
if buku is None:
    sys.exit(1)

# Harapan: (kode, mendatar = (lebar, tinggi), tegak = (lebar, tinggi), skala)
UKURAN = [
    ("2x3", (3, 2), (2, 3), "1"),
    ("3x4", (4, 3), (3, 4), "1.25"),
    ("4x5", (5, 4), (4, 5), "1.5"),
]

# ── 1. UKURAN DI CSS HASIL RENDER ─────────────────────────────────────────
bagian("1. Ukuran label benar-benar berubah di lembar cetak")

for kode, mendatar, tegak, skala in UKURAN:
    for nama_orientasi, (lebar, tinggi) in (("mendatar", mendatar), ("tegak", tegak)):
        html = c.get(reverse("label-print"),
                     {"ids": str(buku.pk), "ukuran": kode, "orientasi": nama_orientasi}
                     ).content.decode()
        css_lebar = f"--lebar-label: {lebar}cm" in html
        css_tinggi = f"--tinggi-label: {tinggi}cm" in html
        cek(f"{kode} {nama_orientasi} → {lebar} × {tinggi} cm",
            css_lebar and css_tinggi,
            f"lebar={css_lebar} tinggi={css_tinggi}")
        cek(f"{kode} {nama_orientasi} memakai skala huruf {skala}",
            f"--skala: {skala}" in html)
        # Penjaga regresi: LANGUAGE_CODE='id' bisa mencetak "1,25" sehingga
        # calc(11pt * 1,25) tidak valid dan skala huruf diam-diam gagal.
        m_skala = re.search(r"--skala:\s*([^;]+);", html)
        nilai_skala = (m_skala.group(1).strip() if m_skala else "")
        cek(f"{kode} {nama_orientasi}: angka CSS pakai titik desimal (bukan koma)",
            bool(nilai_skala) and "," not in nilai_skala and nilai_skala == skala,
            f"--skala: {nilai_skala}")
        cek(f"{kode} {nama_orientasi} tetap memuat label buku",
            html.count('class="label') >= 1 and buku.title[:20] in html)

# ── 2. DEFAULT & NILAI TAK DIKENAL ────────────────────────────────────────
bagian("2. Default & ketahanan terhadap nilai tak dikenal")

html_default = c.get(reverse("label-print"), {"ids": str(buku.pk)}).content.decode()
cek("tanpa parameter → default 2×3 mendatar (3 × 2 cm, seperti sebelumnya)",
    "--lebar-label: 3cm" in html_default and "--tinggi-label: 2cm" in html_default)

for aneh in ["99x99", "abc", "", "2X3", "-1"]:
    html = c.get(reverse("label-print"),
                 {"ids": str(buku.pk), "ukuran": aneh}).content.decode()
    cek(f"ukuran tak valid {aneh!r} → jatuh ke default aman",
        "--lebar-label: 3cm" in html and "--tinggi-label: 2cm" in html)

html_orientasi_aneh = c.get(reverse("label-print"),
                            {"ids": str(buku.pk), "orientasi": "miring"}).content.decode()
cek("orientasi tak dikenal → mendatar (default)",
    "--lebar-label: 3cm" in html_orientasi_aneh)

# ── 3. JUMLAH LABEL TIDAK TERPENGARUH UKURAN ──────────────────────────────
bagian("3. Jumlah label konsisten untuk semua ukuran")

tiga = list(Book.objects.all()[:3])
ids = ",".join(str(b.pk) for b in tiga)
for kode, *_ in UKURAN:
    html = c.get(reverse("label-print"),
                 {"ids": ids, "ukuran": kode}).content.decode()
    jumlah = html.count('class="label')
    cek(f"{kode}: 3 buku → 3 label", jumlah == len(tiga), f"{jumlah} label")

# ── 4. PEMILIH DI HALAMAN CETAK (toolbar) ─────────────────────────────────
bagian("4. Pemilih ukuran & orientasi di toolbar halaman cetak")

html = c.get(reverse("label-print"),
             {"ids": str(buku.pk), "ukuran": "4x5", "orientasi": "tegak"}).content.decode()
cek("toolbar punya select ukuran", 'name="ukuran"' in html)
cek("toolbar punya select orientasi", 'name="orientasi"' in html)
cek("ukuran aktif ditandai terpilih",
    re.search(r'<option value="4x5"[^>]*selected', html) is not None)
cek("orientasi aktif ditandai terpilih",
    re.search(r'<option value="tegak"[^>]*selected', html) is not None)
cek("keterangan ukuran aktif tampil", "4 × 5 cm (tegak)" in html)
cek("pilihan buku (ids) ikut dibawa saat ganti ukuran",
    re.search(r'<input type="hidden" name="ids" value="' + str(buku.pk), html) is not None)
cek("ukuran/orientasi TIDAK diduplikasi sebagai input tersembunyi",
    html.count('<input type="hidden" name="ukuran"') == 0
    and html.count('<input type="hidden" name="orientasi"') == 0)

# ── 5. HALAMAN PILIH BUKU ─────────────────────────────────────────────────
bagian("5. Halaman 'Cetak Label' (pilih buku)")

pilih = c.get(reverse("label-select")).content.decode()
cek("ada select ukuran", 'name="ukuran"' in pilih)
cek("tiga ukuran ditawarkan",
    all(f'value="{k}"' in pilih for k, *_ in UKURAN)
    and "2 × 3 cm" in pilih and "3 × 4 cm" in pilih and "4 × 5 cm" in pilih)
cek("ada select orientasi", 'name="orientasi"' in pilih)
cek("keterangan halaman menyebut ketiga ukuran",
    pilih.count("×") >= 3)

# ── 6. SKALA HURUF MASUK AKAL ─────────────────────────────────────────────
bagian("6. Skala huruf label")

levant, lega = [], []
for kode, _, _, skala in UKURAN:
    html = c.get(reverse("label-print"),
                 {"ids": str(buku.pk), "ukuran": kode}).content.decode()
    m = re.search(r"\.label \.rak \{\s*font-size: calc\(11pt \* var\(--skala\)\)", html)
    (levant if m else lega).append(kode)
cek("ukuran huruf memakai calc(...) + --skala (ikut membesar)", not lega,
    f"lolos: {', '.join(levant)}")
skala_naik = [s for _, _, _, s in UKURAN]
cek("skala makin besar untuk label makin besar",
    skala_naik == sorted(skala_naik) and len(set(skala_naik)) == len(skala_naik),
    str(skala_naik))

# ── RINGKASAN ─────────────────────────────────────────────────────────────
print()
print("=" * 78)
print(f"  RINGKASAN: {lulus} LULUS, {len(gagal)} GAGAL")
for g in gagal:
    print(f"    - {g}")
print("=" * 78)
sys.exit(0 if not gagal else 1)
