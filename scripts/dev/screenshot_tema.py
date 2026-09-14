# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Tangkapan layar halaman dalam DUA mode (terang & gelap) untuk dokumentasi.

Halaman dirender lewat Django test client (sudah login), URL aset dibuat absolut,
lalu kelas tema dipaksa sebelum Chrome mengambil gambar.

Jalankan:  .venv\\Scripts\\python.exe scripts\\dev\\screenshot_tema.py
Hasil:     preview/<halaman>-terang.png dan preview/<halaman>-gelap.png
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

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "preview"
HALAMAN = [("dashboard", "dashboard"), ("katalog", "book-list"),
           ("pengaturan", "settings"), ("label", "label-select")]

KANDIDAT = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]


def cari_chrome() -> str | None:
    if os.environ.get("CHROME_PATH") and Path(os.environ["CHROME_PATH"]).exists():
        return os.environ["CHROME_PATH"]
    for c in KANDIDAT:
        if Path(c).exists():
            return c
    return None


def skrip_tema(mode: str) -> str:
    return """
<script>
(function () {
  const tt = document.createElement('style');
  tt.textContent = '*,*::before,*::after{transition:none!important;animation:none!important}';
  document.head.appendChild(tt);
  document.documentElement.classList.%s('dark');
})();
</script>
""" % ("add" if mode == "gelap" else "remove")


def main() -> int:
    chrome = cari_chrome()
    if not chrome:
        print("[!] Chrome tidak ditemukan (set CHROME_PATH).")
        return 1
    klien = Client()
    u = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if u:
        klien.force_login(u)
    PREVIEW.mkdir(exist_ok=True)

    for nama, url_name in HALAMAN:
        html = klien.get(reverse(url_name)).content.decode()
        html = html.replace('="/static/', '="http://127.0.0.1:8000/static/')
        html = html.replace('="/media/', '="http://127.0.0.1:8000/media/')
        for mode in ("terang", "gelap"):
            berkas = PREVIEW / f"_{nama}-{mode}.html"
            berkas.write_text(html.replace("</body>", skrip_tema(mode) + "</body>"),
                              encoding="utf-8")
            png = PREVIEW / f"{nama}-{mode}.png"
            url = "file:///" + str(berkas).replace("\\", "/").replace(" ", "%20")
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox",
                            "--hide-scrollbars", "--virtual-time-budget=8000",
                            "--run-all-compositor-stages-before-draw",
                            "--window-size=1440,1200",
                            f"--screenshot={png}", url],
                           capture_output=True, text=True, timeout=180)
            ukuran = png.stat().st_size // 1024 if png.exists() else 0
            print(f"  {png.name:26s} {ukuran:>4} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
