# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
VERIFIKASI — IKON FORM LOGIN TIDAK LAGI TERTIMPA TEKS
=====================================================
Bug yang diperbaiki: ikon user/gembok pada form login bertumpuk dengan teks
yang diketik pengguna. Penyebabnya bukan template, melainkan CSS:
kelas `pl-11` (padding kiri untuk memberi ruang ikon) ditulis di
library/forms.py, sedangkan `content` di tailwind.config.js hanya memindai
template → kelas itu TIDAK pernah masuk ke static/css/output.css.

Skrip ini mengukur LANGSUNG DI BROWSER (Chrome headless, --dump-dom):
  • computed padding-left kedua input (harus ≥ 40px, bukan 0)
  • jarak tepi kanan ikon ke titik awal teks (harus > 0 → tidak bertimpa)
  • jarak tepi kanan ikon ke tepi kiri kotak input (harus > 0)

Jalankan: .venv\\Scripts\\python.exe scripts\\dev\\verify_login_ikon.py
"""
import base64
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import django

_os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402

BASE = "http://127.0.0.1:8000"
PREVIEW = Path("preview")
PREVIEW.mkdir(exist_ok=True)

SKRIP = """
<script>
window.addEventListener('load', function () {
  function ukur(id) {
    var el = document.getElementById(id);
    if (!el) return {ada: false};
    var cs = getComputedStyle(el);
    var r = el.getBoundingClientRect();
    var svg = el.parentElement ? el.parentElement.querySelector('svg') : null;
    var sr = svg ? svg.getBoundingClientRect() : null;
    var pad = parseFloat(cs.paddingLeft) || 0;
    return {
      ada: true,
      paddingLeftPx: pad,
      fontFamily: cs.fontFamily,
      inputLeft: r.left,
      inputWidth: r.width,
      iconLeft: sr ? sr.left : null,
      iconRight: sr ? sr.right : null,
      teksMulaiPx: r.left + pad,
      jarakIkonKeTeksPx: sr ? (r.left + pad - sr.right) : null,
      jarakIkonKeTepiInputPx: sr ? (sr.left - r.left) : null,
    };
  }
  var hasil = {
    cssTerpasang: document.styleSheets.length,
    username: ukur('id_username'),
    password: ukur('id_password'),
  };
  var pre = document.createElement('pre');
  pre.id = 'HASIL-IKON';
  pre.textContent = btoa(unescape(encodeURIComponent(JSON.stringify(hasil))));
  document.body.appendChild(pre);
});
</script>
"""


def cari_chrome() -> str | None:
    for kandidat in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                     r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
        if Path(kandidat).exists():
            return kandidat
    return shutil.which("chrome") or shutil.which("chrome.exe")


# ── 1. Ambil halaman login & absolutkan aset statik ───────────────────────────
c = Client()
html = c.get(reverse("login")).content.decode()
html = html.replace('="/static/', f'="{BASE}/static/').replace("url('/static/", f"url('{BASE}/static/")
html = html.replace("</body>", SKRIP + "</body>")
berkas = PREVIEW / "login_ikon.html"
berkas.write_text(html, encoding="utf-8")
print(f"Halaman login disimpan: {berkas} ({len(html)} chars)")

# ── 2. Jalankan Chrome headless ───────────────────────────────────────────────
chrome = cari_chrome()
if not chrome:
    print("  [GAGAL] Chrome tidak ditemukan — tidak bisa mengukur di browser.")
    sys.exit(1)
print(f"Chrome: {chrome}")
proc = subprocess.run(
    [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
     "--window-size=1440,1000", "--virtual-time-budget=9000", "--dump-dom",
     berkas.resolve().as_uri()],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)

m = re.search(r'<pre id="HASIL-IKON">(.*?)</pre>', proc.stdout, flags=re.S)
if not m:
    print("  [GAGAL] tidak menemukan hasil audit di DOM — halaman tidak jalan?")
    print(proc.stderr[-800:])
    sys.exit(1)
data = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))

lulus, gagal = 0, []


def cek(nama: str, kondisi: bool, detail: str = "") -> None:
    global lulus
    if kondisi:
        lulus += 1
        print(f"  [OK  ] {nama}" + (f" — {detail}" if detail else ""))
    else:
        gagal.append(nama)
        print(f"  [GAGAL] {nama}" + (f" — {detail}" if detail else ""))


print("=" * 78)
print("  VERIFIKASI IKON FORM LOGIN (pengukuran di browser)")
print("=" * 78)
cek("stylesheet halaman termuat", data.get("cssTerpasang", 0) >= 1,
    f"jumlah stylesheet={data.get('cssTerpasang')}")
for kunci, label in (("username", "Nama Pengguna"), ("password", "Kata Sandi")):
    d = data.get(kunci) or {}
    if not d.get("ada"):
        cek(f"input {label} ada di halaman", False)
        continue
    cek(f"{label}: padding-left input ≥ 40px (ruang untuk ikon)",
        d["paddingLeftPx"] >= 40, f"padding-left={d['paddingLeftPx']}px")
    cek(f"{label}: ikon di dalam kotak input",
        d["jarakIkonKeTepiInputPx"] is not None and d["jarakIkonKeTepiInputPx"] >= 0,
        f"ikon-ke-tepi={d['jarakIkonKeTepiInputPx']}px")
    cek(f"{label}: teks mulai SETELAH tepi kanan ikon (tidak bertimpa)",
        d["jarakIkonKeTeksPx"] is not None and d["jarakIkonKeTeksPx"] > 0,
        f"jarak ikon→teks={d['jarakIkonKeTeksPx']}px "
        f"(ikon right={d['iconRight']}, teks mulai={d['teksMulaiPx']})")

print()
total = lulus + len(gagal)
print(f"HASIL: {lulus}/{total} pemeriksaan LULUS" +
      ("" if gagal else " — IKON & TEKS TIDAK BERTIMPA"))
for g in gagal:
    print(f"  - GAGAL: {g}")
print("=" * 78)
sys.exit(0 if not gagal else 1)
