# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""Render halaman ber-login menjadi HTML siap-screenshot (URL statik dibuat absolut)."""
import os
import re

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client  # noqa: E402

os.makedirs("preview", exist_ok=True)
c = Client()
c.login(username="user1", password="password123")

PAGES = {
    "form-buku": "/buku/tambah/",
    "pengaturan": "/pengaturan/",
    "katalog": "/buku/",
    "dashboard": "/",
    "login": "/login/",
}

for nama, url in PAGES.items():
    html = c.get(url).content.decode()
    # URL absolut agar aset (CSS/JS/gambar) tetap termuat saat dibuka dari file
    html = html.replace('="/static/', '="http://127.0.0.1:8000/static/')
    html = html.replace('="/media/', '="http://127.0.0.1:8000/media/')
    html = html.replace("url('/static/", "url('http://127.0.0.1:8000/static/")
    path = f"preview/{nama}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{url:16s} -> {path}  ({len(html)} chars)")
