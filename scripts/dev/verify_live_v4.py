# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
VERIFIKASI LIVE v4 — SESI lewat HTTP sungguhan (server benar-benar berjalan)
==========================================================================
Melengkapi verify_sesi.py (yang memakai test client) dengan jalur nyata:
  • tamu membuka aplikasi → halaman LOGIN (bukan dashboard)
  • login sungguhan (POST + CSRF) → 302 ke dashboard, cookie sesi diterima
  • cookie sesi TIDAK punya Expires -> tertutup saat browser ditutup
  • /api/sesi/ping/ 200 untuk sesi aktif, 302 untuk tamu
  • halaman login memuat info batas idle & pesan "sesi berakhir" pada ?timeout=1

Membuat akun uji sementara (zz_sesi_uji) lalu MENGHAPUSNYA kembali.

Jalankan: .venv\\Scripts\\python.exe scripts/dev/verify_live_v4.py
"""
import http.cookiejar
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DJA = "http://127.0.0.1:8000"
PY = str(Path(".venv/Scripts/python.exe").resolve())
USER = "zz_sesi_uji"
SANDI = "zz_sesi_123"

lulus, gagal = 0, []


def cek(nama, kondisi, detail=""):
    global lulus
    if kondisi:
        lulus += 1
        print(f"  [OK  ] {nama}" + (f" — {detail}" if detail else ""))
    else:
        gagal.append(nama)
        print(f"  [GAGAL] {nama}" + (f" — {detail}" if detail else ""))


def mg(*args) -> subprocess.CompletedProcess:
    return subprocess.run([PY, "manage.py", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


class TanpaRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def ambil(op, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with op.open(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace"), r
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), e


print("=" * 78)
print("  VERIFIKASI LIVE v4 — SESI (HTTP sungguhan)")
print("=" * 78)

# ── siapkan akun uji ─────────────────────────────────────────────────────────
mg("ensure_superuser", "--username", USER, "--password", SANDI, "--email", "")
print(f"  akun uji: {USER}")

try:
    # ── 1. Tamu → halaman login ──────────────────────────────────────────────
    op_tamu = urllib.request.build_opener(TanpaRedirect)
    st, html, resp = ambil(op_tamu, f"{DJA}/")
    cek("tamu membuka / → 302 ke /login/",
        st == 302 and "/login/" in resp.headers.get("Location", ""),
        f"status={st} tujuan={resp.headers.get('Location')}")

    st, html, _ = ambil(op_tamu, f"{DJA}/login/")
    cek("halaman login tampil (200)", st == 200, f"status={st}")
    cek("halaman login menyebut batas 10 menit tanpa aktivitas",
        "10 menit tanpa aktivitas" in html)
    cek("halaman login TIDAK memuat skrip penjaga sesi",
        "/api/sesi/ping/" not in html)

    st, html, _ = ambil(op_tamu, f"{DJA}/login/?timeout=1")
    cek("login?timeout=1 menampilkan pesan sesi berakhir",
        st == 200 and "Sesi Anda berakhir" in html, f"status={st}")

    st, _, _ = ambil(op_tamu, f"{DJA}/api/sesi/ping/")
    cek("ping oleh tamu → dialihkan ke login", st == 302, f"status={st}")

    # ── 2. Login sungguhan lewat HTTP (cookie + CSRF) ────────────────────────
    jambu = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jambu))
    st, html, _ = ambil(op, f"{DJA}/login/")
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    cek("token CSRF terbaca dari halaman login", m is not None)
    data = urllib.parse.urlencode({
        "csrfmiddlewaretoken": m.group(1) if m else "",
        "username": USER, "password": SANDI, "next": "",
    }).encode()
    st, html, resp = ambil(op, f"{DJA}/login/", data=data,
                           headers={"Referer": f"{DJA}/login/",
                                    "Content-Type": "application/x-www-form-urlencoded"})
    # Catatan: opener ini MENGIKUTI redirect, jadi status akhir 200 (halaman dashboard).
    # Yang membuktikan login berhasil adalah URL akhir + penanda di dalam halaman.
    cek("login (POST) berhasil → berakhir di dashboard",
        resp.geturl().rstrip("/") == DJA and 'id="user-menu"' in html,
        f"url_akhir={resp.geturl()}")

    st, html, resp = ambil(op, f"{DJA}/")
    cek("setelah login, dashboard terbuka (200 + navbar pengguna)",
        st == 200 and 'id="user-menu"' in html, f"status={st} url={resp.geturl()}")
    cek("halaman dalam aplikasi memuat skrip penjaga sesi",
        "/api/sesi/ping/" in html and "const MENIT = 10" in html)

    # ── 3. Cookie sesi: hilang saat browser ditutup ──────────────────────────
    sesi = [c for c in jambu if c.name == "sessionid"]
    cek("cookie sessionid diterima", bool(sesi))
    if sesi:
        cek("cookie sesi tanpa Expires (tertutup saat browser ditutup)",
            sesi[0].expires is None and sesi[0].discard is True,
            f"expires={sesi[0].expires} discard={sesi[0].discard}")

    # ── 4. Ping menjaga sesi ─────────────────────────────────────────────────
    st, badan, _ = ambil(op, f"{DJA}/api/sesi/ping/",
                         headers={"X-Requested-With": "XMLHttpRequest"})
    data_ping = {}
    if st == 200:
        try:
            data_ping = json.loads(badan)
        except Exception:
            data_ping = {}
    cek("ping sesi aktif → 200 JSON {'ok': true}",
        st == 200 and data_ping.get("ok") is True, f"status={st} {data_ping}")
    cek("ping melaporkan sisa sesi ± 600 detik",
        abs(int(data_ping.get("sisa_detik", 0)) - 600) < 60,
        f"sisa={data_ping.get('sisa_detik')}")

    # ── 5. Logout → kembali ke halaman login ─────────────────────────────────
    st, html, _ = ambil(op, f"{DJA}/logout/")
    cek("GET /logout/ tidak diizinkan (Django 5: logout wajib POST)",
        st == 405, f"status={st}")
    st, html, _ = ambil(op, f"{DJA}/login/")
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    data = urllib.parse.urlencode({"csrfmiddlewaretoken": m.group(1) if m else ""}).encode()
    st, html, resp = ambil(op, f"{DJA}/logout/", data=data,
                           headers={"Referer": f"{DJA}/", 
                                    "Content-Type": "application/x-www-form-urlencoded"})
    cek("logout (POST) → berakhir di halaman login",
        "/login" in resp.geturl(), f"url_akhir={resp.geturl()}")
    st, html, resp = ambil(op, f"{DJA}/")
    cek("setelah logout, membuka / → diarahkan ke login",
        "/login" in resp.geturl(), f"url_akhir={resp.geturl()}")
    st, _, _ = ambil(op_tamu, f"{DJA}/api/sesi/ping/")
    cek("tanpa sesi (setelah logout), ping → dialihkan ke login", st == 302, f"status={st}")
finally:
    hapus = mg("shell", "-c",
               f"from django.contrib.auth.models import User; "
               f"print('dihapus:', User.objects.filter(username='{USER}').delete()[0])")
    print(f"  bersih-bersih akun uji: {hapus.stdout.strip() or hapus.stderr.strip()[:80]}")

print()
total = lulus + len(gagal)
print(f"HASIL: {lulus}/{total} pemeriksaan LULUS" + ("" if gagal else " — SEMUA BAIK"))
for g in gagal:
    print(f"  - GAGAL: {g}")
print("=" * 78)
sys.exit(0 if not gagal else 1)
