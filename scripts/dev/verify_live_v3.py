# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
VERIFIKASI LIVE v3 — lewat HTTP sungguhan (server benar-benar berjalan)
======================================================================
Menguji tiga perbaikan pada BUILD yang sedang berjalan:
  1. Form login: input memakai kelas `pl-11` dan CSS lokal benar-benar
     menyediakan `padding-left` (ikon tidak tertimpa teks). Kelas itu ditulis
     di library/forms.py — dulu tidak pernah tergenerate ke output.css.
  2. Halaman baru "Label Rak" ada di navbar dan dilindungi login.
  3. API FastAPI (port 8001) sehat — semua endpoint `def`, bukan `async def`.

Jalankan: .venv\\Scripts\\python.exe scripts\\dev\\verify_live_v3.py
"""
import json
import sys
import urllib.error
import urllib.request

DJA = "http://127.0.0.1:8000"
API = "http://127.0.0.1:8001"

lulus, gagal = 0, []


def cek(nama, kondisi, detail=""):
    global lulus
    if kondisi:
        lulus += 1
        print(f"  [OK  ] {nama}" + (f" — {detail}" if detail else ""))
    else:
        gagal.append(nama)
        print(f"  [GAGAL] {nama}" + (f" — {detail}" if detail else ""))


def ambil(url):
    """Kembalikan (status, teks). Redirect TIDAK diikuti."""
    class TanpaRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    op = urllib.request.build_opener(TanpaRedirect)
    try:
        with op.open(url, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


print("=" * 78)
print("  VERIFIKASI LIVE v3 — HTTP sungguhan ke aplikasi yang berjalan")
print("=" * 78)

# ── 1. Halaman login & CSS lokal ─────────────────────────────────────────────
st, html = ambil(f"{DJA}/login/")
cek("GET /login/ → 200", st == 200, f"status={st}")
cek("input login memuat kelas pl-11 (ruang untuk ikon)",
    "pl-11" in html and 'id="id_username"' in html and 'id="id_password"' in html)
cek("halaman memuat static/css/output.css",
    "/static/css/output.css" in html)

st, css = ambil(f"{DJA}/static/css/output.css")
cek("GET /static/css/output.css → 200", st == 200, f"status={st}")
cek("CSS menyediakan aturan .pl-11 (padding-left:2.75rem)",
    "pl-11" in css and "padding-left:2.75rem" in css,
    f"panjang css={len(css)}")
cek("CSS memuat warna placeholder login (placeholder-purple-200)",
    "placeholder-purple-200" in css)

# ── 2. Halaman baru "Label Rak" ──────────────────────────────────────────────
st, html = ambil(f"{DJA}/label-rak/")
cek("GET /label-rak/ (tamu) → dialihkan ke login", st in (301, 302), f"status={st}")
st, html = ambil(f"{DJA}/label-rak/cetak/")
cek("GET /label-rak/cetak/ (tamu) → dialihkan ke login", st in (301, 302), f"status={st}")
st, html = ambil(f"{DJA}/")
cek("GET / (tamu) → dialihkan ke login", st in (301, 302), f"status={st}")

# ── 3. API FastAPI ───────────────────────────────────────────────────────────
st, badan = ambil(f"{API}/api/health")
cek("GET /api/health → 200", st == 200, f"status={st}")
st, badan = ambil(f"{API}/api/stats")
ok_json = False
try:
    data = json.loads(badan)
    ok_json = st == 200 and isinstance(data, dict) and "total_books" in data
except Exception:
    data = {}
cek("GET /api/stats → 200 JSON (ORM sinkron, bukan 500)", ok_json,
    f"status={st} kunci={sorted(data)[:6] if data else None}")
st, badan = ambil(f"{API}/api/shelves")
cek("GET /api/shelves → 200", st == 200, f"status={st}")

print()
total = lulus + len(gagal)
print(f"HASIL: {lulus}/{total} pemeriksaan LULUS" + ("" if gagal else " — SEMUA BAIK"))
for g in gagal:
    print(f"  - GAGAL: {g}")
print("=" * 78)
sys.exit(0 if not gagal else 1)
