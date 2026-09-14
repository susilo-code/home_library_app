"""
Context processor: menyediakan identitas aplikasi (judul, nama singkat, tagline)
ke SEMUA template, sehingga judul dapat diubah dari halaman Pengaturan tanpa
menyentuh kode.

Dipakai di: judul tab browser, navbar, footer, halaman login, dan label cetak.
"""
from .models import SiteConfig


def identitas_aplikasi(request):
    """Kembalikan dict berisi objek SiteConfig (singleton)."""
    try:
        return {'app_config': SiteConfig.get_solo()}
    except Exception:
        # Jangan sampai seluruh situs error hanya karena tabel belum ada
        # (mis. saat migrasi pertama kali dijalankan).
        return {'app_config': None}
