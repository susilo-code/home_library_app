"""
Context processor: menyediakan identitas aplikasi (judul, nama singkat, tagline)
ke SEMUA template, sehingga judul dapat diubah dari halaman Pengaturan tanpa
menyentuh kode.

Dipakai di: judul tab browser, navbar, footer, halaman login, dan label cetak.

Juga menyediakan `static_version` — versi aset statik (CSS/JS) untuk parameter
`?v=` pada tautan stylesheet/script.
"""
from pathlib import Path

from django.conf import settings

from .models import SiteConfig


def identitas_aplikasi(request):
    """Kembalikan dict berisi objek SiteConfig (singleton)."""
    try:
        return {'app_config': SiteConfig.get_solo()}
    except Exception:
        # Jangan sampai seluruh situs error hanya karena tabel belum ada
        # (mis. saat migrasi pertama kali dijalankan).
        return {'app_config': None}


def static_version(request):
    """
    Versi aset statik untuk `{% static 'css/output.css' %}?v={{ static_version }}`.

    Kenapa perlu: nama berkas `output.css` TIDAK pernah berubah sejak dibangun,
    sementara server pengembangan tidak mengirim `Cache-Control`. Chrome memakai
    umur cache heuristik (10% dari usia berkas) sehingga perbaikan tampilan bisa
    TIDAK terlihat di browser pengguna walaupun berkasnya sudah diperbarui —
    persis kasus "ikon login masih tertimpa teks" walau CSS-nya sudah benar.
    Dengan `?v=<mtime>`, URL ikut berubah setiap kali CSS/JS dibangun ulang,
    sehingga browser pasti mengambil berkas baru (tanpa perlu hard-refresh).
    """
    global _versi_terakhir
    dasar = Path(settings.BASE_DIR)
    berkas = [dasar / 'static' / 'css' / 'output.css']
    berkas += sorted((dasar / 'static' / 'js').glob('*.js'))
    try:
        versi = str(max(int(b.stat().st_mtime) for b in berkas if b.exists()))
    except Exception:
        versi = ''
    return {'static_version': versi}
