# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Audit cakupan CSS lokal (static/css/output.css).

Menjawab pertanyaan: "kalau PC baru TIDAK punya Node.js/npm, apakah tampilan
masih benar?" — karena tanpa Node, `npm run build` dilewati dan aplikasi
memakai output.css yang sudah ikut ter-commit.

Skrip ini membandingkan kelas Tailwind yang dipakai di template dengan kelas
yang benar-benar ada di output.css, lalu melaporkan yang belum tergenerate.

Jalankan:  .venv\\Scripts\\python.exe scripts\\dev\\cek_css_lokal.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

CSS = Path("static/css/output.css")
TEMPLATE_DIRS = [Path("templates")]

# Kelas yang memang bukan milik Tailwind (komponen kustom di input.css) atau
# sengaja diabaikan karena ditangani CSS lain / hanya efek runtime.
DIABAIKAN = {
    "group", "peer", "dark", "hidden", "sr-only",
    "animate-in", "glass", "glow-ring", "rise", "rise-1", "rise-2", "rise-3", "rise-4",
    "float-slow", "hero-panel", "hero-scrim", "hero-scrim", "badge-red", "badge-green",
    "badge-yellow", "badge-blue", "badge-purple", "btn-primary", "btn-secondary",
    "card", "card-header", "card-body", "input", "input-error", "table", "stat-card",
    "chart-container", "dropdown-item", "nav-item", "sidebar-item", "form-error",
    "section-title", "kbd", "chip", "skeleton", "tooltip", "modal", "modal-open",
    "label", "sheet", "lembar", "tegak", "mendatar", "tanpa-rak", "toolbar",
    "utama", "info", "kosong", "atas", "rak", "nama-rak", "judul", "penulis",
    "kaki", "pemilik", "jenis", "pilih-buku",
    # Kelas "penanda" (hook) yang memang tanpa CSS sendiri — gayanya dari
    # utility Tailwind atau dari JS. Bukan bug kalau tidak ada di output.css.
    "toast", "ac-item",
}

def escape_css(kelas: str) -> str:
    """Ubah nama kelas Tailwind menjadi bentuk ter-escape seperti di CSS."""
    keluaran = []
    for ch in kelas:
        if ch in ":/[]().%#,+*~!@$&'\"<>=?^`{|}\\ ":
            keluaran.append("\\" + ch)
        else:
            keluaran.append(ch)
    return "".join(keluaran)


def kelas_dipakai() -> Counter:
    dipakai: Counter = Counter()
    for folder in TEMPLATE_DIRS:
        for f in sorted(folder.rglob("*.html")):
            teks = f.read_text(encoding="utf-8", errors="replace")
            for atribut in re.findall(r'class="([^"]*)"', teks):
                # buang ekspresi template Django ({{ }}, {% %}).
                # Catatan: blok {% if %} juga membuang kelas di dalamnya, jadi
                # skrip ini bersifat konservatif (tidak menuduh salah).
                bersih = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", " ", atribut, flags=re.S)
                for k in bersih.split():
                    if k and not k.startswith("{"):
                        dipakai[k] += 1
    return dipakai


def main() -> int:
    if not CSS.exists():
        print(f"  [GAGAL] {CSS} tidak ada — jalankan: npm run build")
        return 1

    isi_css = CSS.read_text(encoding="utf-8", errors="replace")
    # Normalisasi: Tailwind menulis koma di kelas arbitrary sebagai "\2c "
    # (contoh: .drop-shadow-\[0_4px_18px_rgba\(0\2c 0\2c 0\2c \.9\)\]).
    # Setelah dinormalisasi, pencarian cukup memakai nama kelas apa adanya —
    # menghindari "false positive" karena perbedaan cara escape.
    css_normal = isi_css.replace("\\2c ", ",").replace("\\", "")
    dipakai = kelas_dipakai()
    hilang: list[tuple[str, int]] = []

    for kelas, jumlah in dipakai.most_common():
        if kelas in DIABAIKAN:
            continue
        if kelas.startswith(("data-", "aria-", "www", "http")):
            continue
        if ("." + kelas) not in css_normal:
            hilang.append((kelas, jumlah))

    print("=" * 74)
    print("  AUDIT CAKUPAN CSS LOKAL (static/css/output.css)")
    print("=" * 74)
    print(f"  Kelas unik dipakai di template : {len(dipakai)}")
    print(f"  Kelas tersedia di output.css   : {len(dipakai) - len(hilang)}")
    print(f"  Belum tergenerate              : {len(hilang)}")
    print()
    if hilang:
        print("  Daftar kelas yang belum ada di output.css (maks 40):")
        for kelas, jumlah in hilang[:40]:
            print(f"    - {kelas}  (dipakai {jumlah}x)")
        print()
        print("  [!] Ada kelas yang tidak punya CSS lokal — di PC tanpa Node.js")
        print("      (tanpa Tailwind CDN) elemen itu kehilangan gayanya.")
        print("      Perbaiki dengan memperluas theme di tailwind.config.js atau")
        print("      mengganti kelas tersebut, lalu jalankan: npm run build")
        print("=" * 74)
        return 1
    print("  Semua kelas template sudah tersedia di CSS lokal ✅")
    print("  Artinya: PC tanpa Node.js/npm tetap tampil benar (tanpa internet pun).")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
