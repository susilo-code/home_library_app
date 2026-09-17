# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
VERIFIKASI — SESI: keluar otomatis setelah 10 menit tanpa aktivitas
==================================================================
Yang diperiksa (semuanya perilaku nyata, bukan pembacaan konfigurasi saja):
  1. Pengaturan: SESSION_COOKIE_AGE = SESSION_IDLE_MINUTES × 60,
     SESSION_SAVE_EVERY_REQUEST, SESSION_EXPIRE_AT_BROWSER_CLOSE
  2. Halaman default saat aplikasi dibuka = LOGIN (tamu diarahkan ke /login/)
  3. Sesi dibuat dengan masa berlaku ± 10 menit
  4. Jendela bergeser: permintaan berikutnya MEMPERPANJANG masa berlaku
     (tanpa ini pengguna ter-logout 10 menit setelah login walau sedang aktif)
  5. Sesi yang sudah lewat masa berlakunya (disimulasikan di DB)
     -> pengguna otomatis diminta login lagi
  6. /api/sesi/ping/ (penjaga sesi dari browser): 200 untuk yang masuk,
     302 untuk tamu, dan benar-benar memperbarui masa berlaku
  7. Template: pengingat di base.html ada (hanya untuk pengguna yang sudah masuk)
     dan halaman login menampilkan pesan "sesi berakhir" hanya saat ?timeout=1

Jalankan: .venv\\Scripts\\python.exe scripts\\dev\\verify_sesi.py
"""
import json
import sys
import time
from datetime import timedelta

import django

_os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.contrib.sessions.models import Session  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402
from django.urls import reverse  # noqa: E402
from django.utils import timezone  # noqa: E402

setup_test_environment()   # WAJIB di luar TestCase agar response.context tidak None

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


print("=" * 78)
print("  VERIFIKASI SESI — otomatis logout setelah tidak ada aktivitas")
print("=" * 78)

MENIT = getattr(settings, "SESSION_IDLE_MINUTES", None)
print(f"  SESSION_IDLE_MINUTES = {MENIT}")

# ══════════════════════════════════════════════════════════════════════════════
bagian("1. PENGATURAN SESI")
# ══════════════════════════════════════════════════════════════════════════════
cek("SESSION_IDLE_MINUTES = 10 (bawaan)", MENIT == 10, f"nilai={MENIT}")
cek("SESSION_COOKIE_AGE = menit × 60", settings.SESSION_COOKIE_AGE == (MENIT or 0) * 60,
    f"{settings.SESSION_COOKIE_AGE} detik")
cek("SESSION_SAVE_EVERY_REQUEST aktif (jendela bergeser)",
    getattr(settings, "SESSION_SAVE_EVERY_REQUEST", False) is True)
cek("SESSION_EXPIRE_AT_BROWSER_CLOSE aktif (tutup browser = keluar)",
    getattr(settings, "SESSION_EXPIRE_AT_BROWSER_CLOSE", False) is True)
cek("LOGIN_URL menunjuk ke 'login'", settings.LOGIN_URL == "login")
cek("LOGOUT_REDIRECT_URL menunjuk ke 'login'",
    getattr(settings, "LOGOUT_REDIRECT_URL", "") == "login")

# ══════════════════════════════════════════════════════════════════════════════
bagian("2. HALAMAN DEFAULT SAAT APLIKASI DIBUKA = LOGIN")
# ══════════════════════════════════════════════════════════════════════════════
tamu = Client()
r = tamu.get("/")
cek("tamu membuka / → dialihkan ke halaman login",
    r.status_code == 302 and reverse("login") in r.headers.get("Location", ""),
    f"status={r.status_code} tujuan={r.headers.get('Location')}")
for nama_url in ("book-list", "shelf-label-select", "label-select", "settings", "user-list"):
    r = tamu.get(reverse(nama_url))
    cek(f"tamu membuka /{nama_url.replace('-', '/')}/ → login",
        r.status_code == 302 and reverse("login") in r.headers.get("Location", ""),
        f"status={r.status_code}")
r = tamu.get(reverse("login"))
cek("halaman login tampil tanpa riwayat sesi", r.status_code == 200)

# ══════════════════════════════════════════════════════════════════════════════
bagian("3. MASA BERLAKU SESI & JENDELA BERGESER")
# ══════════════════════════════════════════════════════════════════════════════
pengguna = User.objects.filter(is_superuser=True).first() or User.objects.first()
if pengguna is None:
    print("Tidak ada akun di database — jalankan create_user/seed_data dulu.")
    sys.exit(1)
print(f"  Login sebagai: {pengguna.username}")

c = Client()
c.force_login(pengguna)
kunci = c.session.session_key
baris = Session.objects.filter(session_key=kunci).first()
cek("sesi tersimpan di database", baris is not None, f"key={kunci[:8]}…")
if baris:
    sisa = (baris.expire_date - timezone.now()).total_seconds()
    cek(f"masa berlaku ± {MENIT} menit", abs(sisa - settings.SESSION_COOKIE_AGE) < 60,
        f"sisa={sisa:.0f} detik")

r = c.get(reverse("dashboard"))
cek("permintaan halaman (ada aktivitas) → tetap 200", r.status_code == 200)
kunci2 = c.session.session_key
b1 = Session.objects.filter(session_key=kunci2).first()
waktu1 = b1.expire_date if b1 else None
time.sleep(1.2)
c.get(reverse("dashboard"))
b2 = Session.objects.filter(session_key=kunci2).first()
waktu2 = b2.expire_date if b2 else None
cek("aktivitas MEMPERPANJANG masa berlaku (jendela bergeser)",
    waktu1 is not None and waktu2 is not None and waktu2 > waktu1,
    f"{waktu1} → {waktu2}")

# ══════════════════════════════════════════════════════════════════════════════
bagian("4. SESI HABIS (disimulasikan: 10 menit tanpa aktivitas)")
# ══════════════════════════════════════════════════════════════════════════════
Session.objects.filter(session_key=c.session.session_key).update(
    expire_date=timezone.now() - timedelta(minutes=1))
r = c.get(reverse("dashboard"))
cek("sesi kedaluwarsa → pengguna diminta login lagi",
    r.status_code == 302 and reverse("login") in r.headers.get("Location", ""),
    f"status={r.status_code} tujuan={r.headers.get('Location')}")
r = c.get(reverse("dashboard"))
cek("setelah itu tetap harus login (tidak otomatis masuk kembali)", r.status_code == 302)

# ══════════════════════════════════════════════════════════════════════════════
bagian("5. PENJAGA SESI DARI BROWSER (/api/sesi/ping/)")
# ══════════════════════════════════════════════════════════════════════════════
c2 = Client()
c2.force_login(pengguna)
r = c2.get(reverse("sesi-ping"))
cek("ping (sudah login) → 200 JSON", r.status_code == 200, f"status={r.status_code}")
data = {}
if r.status_code == 200:
    try:
        data = json.loads(r.content.decode())
    except Exception:
        data = {}
cek("balasan ping berisi ok/sisa_detik/menit_idle",
    data.get("ok") is True and "sisa_detik" in data and data.get("menit_idle") == MENIT,
    f"{data}")
cek("sisa_detik mendekati batas idle",
    abs(int(data.get("sisa_detik", 0)) - settings.SESSION_COOKIE_AGE) < 60,
    f"sisa={data.get('sisa_detik')} detik")

kunci3 = c2.session.session_key
# Buat masa berlaku seolah hampir habis (30 detik), lalu pastikan ping
# MENGEMBALIKANNYA ke ± 10 menit — inilah yang menjaga sesi pengguna yang
# sedang mengetik lama di satu formulir.
rendah = timezone.now() + timedelta(seconds=30)
Session.objects.filter(session_key=kunci3).update(expire_date=rendah)
c2.get(reverse("sesi-ping"))
sesudah = Session.objects.get(session_key=kunci3).expire_date
cek("ping memperbarui masa berlaku sesi (30 detik → ± 10 menit)",
    sesudah > rendah + timedelta(minutes=5),
    f"diatur={rendah} → sesudah ping={sesudah}")

tamu2 = Client()
r = tamu2.get(reverse("sesi-ping"))
cek("ping oleh tamu → dialihkan ke login", r.status_code == 302, f"status={r.status_code}")

# ══════════════════════════════════════════════════════════════════════════════
bagian("6. TEMPLATE: PENGINGAT & PESAN SESI BERAKHIR")
# ══════════════════════════════════════════════════════════════════════════════
h_login = tamu.get(reverse("login")).content.decode()
cek("halaman login memberi tahu batas idle (informasi ke pengguna)",
    f"{MENIT} menit tanpa aktivitas" in h_login)
cek("halaman login TIDAK memuat skrip penjaga sesi (belum masuk)",
    reverse("sesi-ping") not in h_login)

h_timeout = tamu.get(reverse("login") + "?timeout=1").content.decode()
cek("login?timeout=1 menampilkan pesan 'sesi berakhir'",
    "Sesi Anda berakhir" in h_timeout)
cek("tanpa ?timeout=1 pesan itu tidak muncul (bukan alarm palsu)",
    "Sesi Anda berakhir" not in h_login)

h_dash = c2.get(reverse("dashboard")).content.decode()
cek("halaman dalam aplikasi memuat skrip penjaga sesi",
    reverse("sesi-ping") in h_dash and f"const MENIT = {MENIT}" in h_dash)
cek("skrip memuat pengalihan ke login dengan penanda timeout",
    f'{reverse("login")}?timeout=1' in h_dash)
cek("skrip memuat pengingat 60 detik terakhir", "PERINGATAN" in h_dash)

# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 78)
total = lulus + len(gagal)
print(f"HASIL AKHIR: {lulus}/{total} pemeriksaan LULUS"
      + (" — SEMUA BAIK" if not gagal else f" — {len(gagal)} GAGAL"))
for g in gagal:
    print(f"  - GAGAL: {g}")
print("=" * 78)
sys.exit(0 if not gagal else 1)
