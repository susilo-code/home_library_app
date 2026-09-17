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
PY_DIRS = [Path("library")]          # kelas Tailwind juga ditulis di dalam kode Python
# Prefiks kelas Tailwind yang dikenal — dipakai untuk menyaring string Python
# (pesan Bahasa Indonesia) supaya tidak dianggap daftar kelas.
PREFIKS_TW = re.compile(
    r"^(?:[a-z0-9]+:)*-?"
    r"(?:w|h|min|max|p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|"
    r"text|bg|border|rounded|shadow|ring|outline|divide|space|gap|grid|flex|items|justify|"
    r"content|self|order|col|row|font|leading|tracking|list|underline|line|whitespace|break|"
    r"overflow|object|opacity|transition|duration|delay|ease|animate|transform|translate|rotate|scale|"
    r"origin|cursor|select|pointer|resize|appearance|placeholder|caret|accent|fill|stroke|"
    r"block|inline|hidden|relative|absolute|fixed|sticky|static|z|top|bottom|left|right|inset|"
    r"float|clear|table|aspect|columns|indent|align|vertical|truncate|uppercase|lowercase|"
    r"capitalize|normal|italic|antialiased|subpixel|backdrop|filter|blur|brightness|contrast|"
    r"saturate|grayscale|invert|sepia|drop|mix|isolation|sr|group|peer|container|first|last|odd|"
    r"even|only|empty|checked|disabled|enabled|visited|target|active|focus|"
    r"sm|md|lg|xl|2xl|dark|print|motion)"
    r"(?:-|$)"
)

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
    #   pilih-rak     → hook JS di halaman pilih rak (label cetak)
    #   autofill-none → penanda pada widget login (gaya autofill ada di <style>)
    "pilih-rak", "autofill-none",
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


def kelas_gaya_lokal() -> set[str]:
    """
    Kelas yang punya CSS-nya SENDIRI (bukan utility Tailwind): blok <style>
    di template (mis. lembar cetak label) dan definisi di static/css/input.css.
    Kelas seperti ini memang tidak perlu ada di output.css.
    """
    lokal: set[str] = set()
    sumber: list[str] = []
    for folder in TEMPLATE_DIRS:
        for f in sorted(folder.rglob("*.html")):
            teks = f.read_text(encoding="utf-8", errors="replace")
            sumber.extend(re.findall(r"<style[^>]*>(.*?)</style>", teks, flags=re.S))
    css_input = Path("static/css/input.css")
    if css_input.exists():
        sumber.append(css_input.read_text(encoding="utf-8", errors="replace"))
    for blok in sumber:
        lokal.update(re.findall(r"\.([a-zA-Z][\w\-]*)", blok))
    return lokal


def kelas_python() -> Counter:
    """
    Kelas Tailwind yang ditulis di kode Python (widget attrs, konstanta
    INPUT_CLASS, …). Inilah yang dulu LUPA dipindai: `pl-11` pada input login
    tidak pernah tergenerate ke output.css sehingga ikon & teks bertimpa.
    """
    dipakai: Counter = Counter()
    for folder in PY_DIRS:
        for f in sorted(folder.rglob("*.py")):
            teks = f.read_text(encoding="utf-8", errors="replace")
            # gabungkan literal yang disambung implisit: 'a ' 'b'
            teks = re.sub(r"(['\"])\s*\n?\s*\1", "", teks)
            for literal in re.findall(r"'([^'\n]*)'|\"([^\"\n]*)\"", teks):
                isi = literal[0] or literal[1]
                if " " not in isi:
                    continue
                kandidat = isi.split()
                tw = [k for k in kandidat if PREFIKS_TW.match(k)]
                # hanya anggap daftar kelas bila ada >=2 token berbau Tailwind
                if len(tw) < 2:
                    continue
                for k in kandidat:
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
    jumlah_template = len(dipakai)
    dipakai_py = kelas_python()
    for k, n in dipakai_py.items():
        dipakai[k] += n
    gaya_lokal = kelas_gaya_lokal()
    hilang: list[tuple[str, int, bool]] = []

    # Mode uji-diri: sisipkan kelas yang pasti tidak ada, untuk membuktikan
    # audit ini memang BISA gagal (kalau tidak, hasil hijau tidak berarti).
    uji_diri = "--uji-diri" in sys.argv
    if uji_diri:
        dipakai["pl-300"] = 1

    for kelas, jumlah in dipakai.most_common():
        if kelas in DIABAIKAN or kelas in gaya_lokal:
            continue
        if kelas.startswith(("data-", "aria-", "www", "http")):
            continue
        if ("." + kelas) not in css_normal:
            hilang.append((kelas, jumlah, kelas in dipakai_py))

    print("=" * 74)
    print("  AUDIT CAKUPAN CSS LOKAL (static/css/output.css)")
    print("=" * 74)
    print(f"  Kelas unik dari template        : {jumlah_template}")
    print(f"  Kelas unik dari kode Python     : {len(dipakai_py)}")
    print(f"  Kelas punya CSS sendiri (<style>): {len(gaya_lokal)}")
    print(f"  Belum tergenerate               : {len(hilang)}")
    print()
    if hilang:
        print("  Daftar kelas yang belum ada di output.css (maks 40):")
        for kelas, jumlah, dari_py in hilang[:40]:
            asal = "kode Python" if dari_py else "template"
            print(f"    - {kelas}  ({asal}, {jumlah}x)")
        print()
        print("  [!] Ada kelas yang tidak punya CSS lokal — di PC tanpa Node.js")
        print("      (tanpa Tailwind CDN) elemen itu kehilangan gayanya.")
        print("      Perbaiki: tambahkan folder sumber ke `content` di")
        print("      tailwind.config.js lalu jalankan: npm run build")
        print("=" * 74)
        return 1
    if uji_diri:
        print("  [GAGAL] uji-diri: kelas palsu 'pl-300' TIDAK terdeteksi —")
        print("          audit ini tidak bisa gagal, jadi hasilnya tidak sah.")
        print("=" * 74)
        return 1
    print("  Semua kelas (template + kode Python) tersedia di CSS lokal ✅")
    print("  Artinya: PC tanpa Node.js/npm tetap tampil benar (tanpa internet pun).")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
