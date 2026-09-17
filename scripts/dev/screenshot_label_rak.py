# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Tangkapan layar untuk dua perbaikan terbaru:
  • preview/label-rak-3x4.png / -4x6.png  — lembar label RAK tiap ukuran
  • preview/login-ikon.png                — form login (ikon tidak tertimpa teks)

Jalankan: .venv\\Scripts\\python.exe scripts\\dev\\screenshot_label_rak.py
"""
import os
import subprocess
import sys
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402
from library.models import Shelf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "preview"
PREVIEW.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8000"
KANDIDAT_CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                   r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]


def cari_chrome() -> str | None:
    if os.environ.get("CHROME_PATH") and Path(os.environ["CHROME_PATH"]).exists():
        return os.environ["CHROME_PATH"]
    for kandidat in KANDIDAT_CHROME:
        if Path(kandidat).exists():
            return kandidat
    return None


def tangkap(chrome: str, berkas: Path, png: Path, ukuran: str) -> None:
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", f"--window-size={ukuran}",
                    "--virtual-time-budget=6000",
                    f"--screenshot={png}", berkas.resolve().as_uri()],
                   capture_output=True, text=True, timeout=180)
    print(f"  {png.name}: {'OK' if png.exists() else 'GAGAL'}"
          f" ({png.stat().st_size // 1024} KB)" if png.exists() else "  GAGAL")


chrome = cari_chrome()
if not chrome:
    print("[GAGAL] Chrome tidak ditemukan")
    sys.exit(1)

c = Client()
pengguna = User.objects.filter(is_superuser=True).first() or User.objects.first()
c.force_login(pengguna)
print(f"Render sebagai: {pengguna.username}")

# ── 1. Lembar label rak, dua ukuran ─────────────────────────────────────────
rak = list(Shelf.objects.order_by("name")[:6])
ids = ",".join(str(r.pk) for r in rak)
print(f"Rak contoh: {[r.name for r in rak]}")
for ukuran in ("3x4", "4x6"):
    html = c.get(reverse("shelf-label-print"),
                 {"ids": ids, "ukuran": ukuran, "orientasi": "mendatar"}).content.decode()
    berkas = PREVIEW / f"label-rak-{ukuran}.html"
    berkas.write_text(html, encoding="utf-8")
    tangkap(chrome, berkas, PREVIEW / f"label-rak-{ukuran}.png", "1100,700")

# ── 2. Halaman login (ikon vs teks) ────────────────────────────────────────
anon = Client()
html = anon.get(reverse("login")).content.decode()
html = html.replace('="/static/', f'="{BASE}/static/').replace("url('/static/", f"url('{BASE}/static/")
berkas = PREVIEW / "login-ikon.html"
berkas.write_text(html, encoding="utf-8")
tangkap(chrome, berkas, PREVIEW / "login-ikon.png", "1280,900")
