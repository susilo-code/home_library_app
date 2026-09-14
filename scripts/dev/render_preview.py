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

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402

os.makedirs("preview", exist_ok=True)
c = Client()
_pengguna = User.objects.filter(is_superuser=True).first() or User.objects.first()
if _pengguna:
    c.force_login(_pengguna)
    print(f"Render sebagai: {_pengguna.username} (superuser={_pengguna.is_superuser})")

PAGES = {
    "form-buku": "/buku/tambah/",
    "pengaturan": "/pengaturan/",
    "katalog": "/buku/",
    "dashboard": "/",
    "login": "/login/",
    "kelola-pengguna": "/pengguna/",
    "identitas": "/pengaturan/identitas/",
    "label-pilih": "/label/",
}

from library.models import Book  # noqa: E402

_buku_rak = Book.objects.exclude(shelf=None).select_related("shelf")[:12]
PAGES["label-cetak"] = "/label/cetak/?ids=" + ",".join(str(b.pk) for b in _buku_rak)

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

# ── Versi khusus: modal detail & modal tambah genre dibuka paksa (untuk pratinjau) ──
html_form = open("preview/form-buku.html", encoding="utf-8").read()
html_modal = html_form.replace(
    'id="modal-detail" class="fixed inset-0 z-50 hidden items-center justify-center p-4"',
    'id="modal-detail" class="fixed inset-0 z-50 flex items-center justify-center p-4"'
).replace(
    'id="modal-genre" class="fixed inset-0 z-50 hidden items-center justify-center p-4"',
    'id="modal-genre" class="fixed inset-0 z-50 flex items-center justify-center p-4"'
)
with open("preview/form-buku-modal.html", "w", encoding="utf-8") as f:
    f.write(html_modal)
print("modal dipaksa terbuka -> preview/form-buku-modal.html")
