"""
Middleware khusus PENGEMBANGAN: larang browser men-cache apa pun.

Kenapa ada: nama berkas `output.css` tidak pernah berubah dan server pengembangan
tidak mengirim `Cache-Control`, sehingga browser memakai umur cache heuristik
(10% dari usia berkas) dan bisa menyajikan halaman/styleshett LAMA walaupun kode
di server sudah diperbarui. Gejala nyatanya: perbaikan tampilan "tidak terlihat"
sampai pengguna menekan Ctrl+Shift+R — pernah terjadi pada perbaikan ikon form
login yang tertimpa teks.

Hanya dipasang saat DEBUG=True (lihat config/settings.py); di produksi middleware
ini tidak dipakai sama sekali, jadi tetap memakai caching normal.
"""


class TanpaCacheDevMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response
