# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Render 4 varian halaman login untuk dibandingkan dengan tangkapan layar pengguna:
    {css SEKARANG, css LAMA} x {kolom kosong, kolom terisi}

css SEKARANG = static/css/output.css setelah perbaikan (ada .pl-11)
css LAMA     = versi sebelum perbaikan (git show HEAD~1:static/css/output.css) —
               dipakai untuk membuktikan tampilan mana yang di-render browser pengguna.
"""
import subprocess
from pathlib import Path

import django

_os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "preview"
PREVIEW.mkdir(exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# ── CSS lama (versi sebelum perbaikan pl-11) ─────────────────────────────────
lama = subprocess.run(["git", "show", "HEAD~1:static/css/output.css"], cwd=ROOT,
                      capture_output=True, text=True, encoding="utf-8")
if lama.returncode != 0:
    print("GAGAL mengambil CSS lama:", lama.stderr[:300])
    sys.exit(1)
(PREVIEW / "_css_lama.css").write_text(lama.stdout, encoding="utf-8")
(PREVIEW / "_css_sekarang.css").write_text(
    (ROOT / "static/css/output.css").read_text(encoding="utf-8"), encoding="utf-8")
print(f"CSS lama: {len(lama.stdout)} chars (pl-11: {'pl-11' in lama.stdout})")
print(f"CSS sekarang: {(ROOT / 'static/css/output.css').stat().st_size} bytes (pl-11: "
      f"{'pl-11' in (ROOT / 'static/css/output.css').read_text(encoding='utf-8')})")

SKRIP_ISI = """
<script>
window.addEventListener('load', function () {
  var u = document.getElementById('id_username');
  var p = document.getElementById('id_password');
  if (u) { u.value = 'hirunaza'; }
  if (p) { p.value = 'rahasia123'; }
});
</script>
"""

anon = Client()
html_dasar = anon.get(reverse("login")).content.decode()

for nama_css, berkas_css in (("sekarang", "_css_sekarang.css"), ("lama", "_css_lama.css")):
    for nama_isi, isi in (("terisi", True), ("kosong", False)):
        html = html_dasar
        # arahkan <link rel=stylesheet> ke berkas CSS lokal yang dipilih
        html = html.replace('href="/static/css/output.css"',
                            f'href="{(PREVIEW / berkas_css).resolve().as_uri()}"')
        # pastikan font/gambar tidak menahan render (offline-safe)
        html = html.replace("</body>", (SKRIP_ISI if isi else "") + "</body>")
        berkas = PREVIEW / f"_varian_{nama_css}_{nama_isi}.html"
        berkas.write_text(html, encoding="utf-8")
        png = PREVIEW / f"_varian_{nama_css}_{nama_isi}.png"
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                        "--hide-scrollbars", "--window-size=1280,900",
                        "--force-device-scale-factor=1",
                        "--virtual-time-budget=8000",
                        f"--screenshot={png}", berkas.resolve().as_uri()],
                       capture_output=True, text=True, timeout=180)
        print(f"  {png.name}: {'OK' if png.exists() else 'GAGAL'}")
