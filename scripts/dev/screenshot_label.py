# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Tangkapan layar lembar label untuk tiap UKURAN (dokumentasi / perbandingan).

Jalankan:  .venv\\Scripts\\python.exe scripts\\dev\\screenshot_label.py [jumlah_buku]
Hasil:     preview/label-<ukuran>.png  (mis. label-2x3.png, label-4x5.png)
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
from library.models import Book  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "preview"
URUTAN = ("2x3", "3x4", "4x5")
KANDIDAT_CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                   r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]


def cari_chrome() -> str | None:
    if os.environ.get("CHROME_PATH") and Path(os.environ["CHROME_PATH"]).exists():
        return os.environ["CHROME_PATH"]
    for kandidat in KANDIDAT_CHROME:
        if Path(kandidat).exists():
            return kandidat
    return None


def main() -> int:
    chrome = cari_chrome()
    if not chrome:
        print("[!] Chrome tidak ditemukan (set CHROME_PATH).")
        return 1

    jumlah = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12
    klien = Client()
    pengguna = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if pengguna:
        klien.force_login(pengguna)

    buku = list(Book.objects.exclude(shelf=None)[:jumlah]) or list(Book.objects.all()[:jumlah])
    ids = ",".join(str(b.pk) for b in buku)
    print(f"  {len(buku)} buku → {ids}")
    PREVIEW.mkdir(exist_ok=True)

    for kode in URUTAN:
        html = klien.get("/label/cetak/", {"ids": ids, "ukuran": kode}).content.decode()
        html = html.replace('="/static/', '="http://127.0.0.1:8000/static/')
        html = html.replace('="/media/', '="http://127.0.0.1:8000/media/')
        berkas = PREVIEW / f"_label-{kode}.html"
        berkas.write_text(html, encoding="utf-8")

        png = PREVIEW / f"label-{kode}.png"
        url = "file:///" + str(berkas).replace("\\", "/").replace(" ", "%20")
        subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox",
                        "--hide-scrollbars", "--virtual-time-budget=8000",
                        "--run-all-compositor-stages-before-draw",
                        "--window-size=1200,900", f"--screenshot={png}", url],
                       capture_output=True, text=True, timeout=180)
        ukuran = png.stat().st_size // 1024 if png.exists() else 0
        print(f"  {png.name:16s} {ukuran:>4} KB" + ("" if ukuran else "  [!] GAGAL"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
