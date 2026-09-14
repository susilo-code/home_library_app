# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
AUDIT KONTRAS MODE GELAP
========================
Menghitung rasio kontras WCAG 2.1 (teks vs latar) untuk setiap elemen berteks
pada halaman aplikasi DALAM MODE GELAP — bukan menebak dari nama kelas.

Cara kerja (offline, tanpa browser):
 1. `output.css` dibaca untuk mengetahui warna asli tiap kelas Tailwind
    (`text-purple-800`, `dark:bg-purple-slate-900`, termasuk varian `/opacity`).
 2. `input.css` dibaca untuk membuka kelas komponen (`card`, `badge-purple`, …)
    menjadi daftar utilitas Tailwind lewat `@apply`.
 3. HTML halaman (Django test client, sudah login) diurai menjadi pohon; tiap
    elemen ditentukan warna teks dan latar efektifnya (mewarisi leluhur,
    alpha di-blend, gradien dinilai per stop warna).
 4. Rasio kontras dihitung; ambang 4.5:1 (teks normal) dan 3.0:1 (teks besar).

Jalankan:  .venv\\Scripts\\python.exe scripts\\dev\\audit_kontras_gelap.py [--rinci]
Keluar dengan kode 1 bila ada pelanggaran (dipakai sebagai gerbang di verifikasi).
"""

import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402
from library.models import Book  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "static/css/output.css"
INPUT_CSS = ROOT / "static/css/input.css"

AMBANG_NORMAL = 4.5
AMBANG_BESAR = 3.0
RINCI = "--rinci" in sys.argv

# Halaman cetak label DIKECUALIKAN: media kertas putih dengan warna tetap.
HALAMAN = [
    ("Dashboard", "/"),
    ("Katalog Buku", "/buku/"),
    ("Cetak Label (pilih)", "/label/"),
    ("Pengaturan", "/pengaturan/"),
    ("Identitas Aplikasi", "/pengaturan/identitas/"),
    ("Kelola Pengguna", "/pengguna/"),
    ("Tambah Buku", "/buku/tambah/"),
]
_buku = Book.objects.first()
if _buku:
    HALAMAN.append(("Detail Buku", _buku.get_absolute_url()))


# ───────────────────────── warna & kontras ─────────────────────────
def dalam_rentang(h: str, awal: str, akhir: str) -> bool:
    return awal <= h <= akhir


def ke_rgba(nilai: str):
    """'rgb(107 33 168 / 0.2)' | '#8a4fff' -> (r, g, b, a) atau None."""
    nilai = nilai.strip()
    m = re.match(r"rgba?\(([^)]+)\)", nilai)
    if m:
        isi = m.group(1).replace("/", " ").replace(",", " ").split()
        try:
            r, g, b = (float(x) for x in isi[:3])
        except (ValueError, IndexError):
            return None
        a = 1.0
        if len(isi) >= 4:
            try:
                a = float(isi[3])
            except ValueError:
                a = 1.0
        return (round(r), round(g), round(b), a)
    m = re.match(r"#([0-9a-fA-F]{3,8})", nilai)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
        if len(h) == 8:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16),
                    int(h[6:8], 16) / 255)
    return None


def luminance(rgb) -> float:
    kanal = []
    for c in rgb[:3]:
        c = c / 255
        kanal.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kanal[0] + 0.7152 * kanal[1] + 0.0722 * kanal[2]


def kontras(fg, bg) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def blend(fg, bg):
    """fg (mungkin transparan) di atas bg solid -> warna solid."""
    a = fg[3] if len(fg) > 3 else 1.0
    if a >= 1.0:
        return tuple(fg[:3])
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3))


def hex_dari(rgb) -> str:
    return "#%02x%02x%02x" % tuple(rgb[:3])


# ───────────────────────── membaca CSS hasil build ─────────────────────────
ISI_CSS = CSS.read_text(encoding="utf-8", errors="replace") if CSS.exists() else ""

# Karakter yang di-escape Tailwind pada nama kelas
PERLU_ESCAPE = set(":/.%[]()#,+*'>~=&!$")


def escape_kelas(kelas: str) -> str:
    return "".join(("\\" + c) if c in PERLU_ESCAPE else c for c in kelas)


def blok_aturan(kelas: str) -> str:
    """Isi deklarasi CSS untuk kelas Tailwind ('' bila tidak ditemukan)."""
    pola = "." + escape_kelas(kelas)
    pos = 0
    while True:
        i = ISI_CSS.find(pola, pos)
        if i == -1:
            return ""
        j = ISI_CSS.find("{", i)
        k = ISI_CSS.find("}", j)
        if j == -1 or k == -1:
            return ""
        lanjutan = ISI_CSS[i + len(pola): j].strip()
        if lanjutan in ("", ":", ",", ">*"):
            return ISI_CSS[j + 1:k]
        pos = i + 1


def warna_kelas(kelas: str, properti: str):
    blok = blok_aturan(kelas)
    if not blok:
        return None
    if properti == "color":
        m = re.search(r"(?<![-\w])color:([^;]+)", blok)
    else:
        m = re.search(r"background-color:([^;]+)", blok)
    return ke_rgba(m.group(1)) if m else None


def stop_gradien(kelas: str):
    blok = blok_aturan(kelas)
    if not blok:
        return None
    m = re.search(r"--tw-gradient-(?:from|via|to):([^;]+)", blok)
    if not m:
        return None
    return ke_rgba(m.group(1).rsplit(" ", 1)[0])


def peta_komponen() -> dict:
    """Kelas komponen di input.css -> daftar utilitas Tailwind (@apply)."""
    if not INPUT_CSS.exists():
        return {}
    isi = INPUT_CSS.read_text(encoding="utf-8", errors="replace")
    peta = {}
    for m in re.finditer(r"\.([a-z0-9-]+)\s*\{([^}]*)\}", isi, re.S):
        ap = re.search(r"@apply\s+([^;]+);", m.group(2))
        if ap:
            peta[m.group(1)] = ap.group(1).split()
    for _ in range(3):  # buka rujukan bertingkat (btn-primary -> btn)
        for nama, daftar in list(peta.items()):
            baru = []
            for t in daftar:
                baru.extend(peta.get(t, [t]))
            peta[nama] = baru
    return peta


KOMPONEN = peta_komponen()


def kelas_efektif(attrs: dict) -> list:
    mentah = attrs.get("class", "") or ""
    if "{{" in mentah or "{%" in mentah:
        mentah = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", "", mentah)
    hasil = []
    for t in mentah.split():
        hasil.extend(KOMPONEN.get(t, [t]))
    return hasil


# ───────────────────────── penguraian HTML ─────────────────────────
class Simpul:
    __slots__ = ("tag", "attrs", "anak", "teks", "induk")

    def __init__(self, tag, attrs, induk=None):
        self.tag, self.attrs, self.induk = tag, attrs, induk
        self.anak, self.teks = [], []


class Pengurai(HTMLParser):
    DILEWATI = {"script", "style", "svg", "head"}
    TANPA_PENUTUP = {"br", "img", "input", "meta", "link", "hr", "source"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.akar = Simpul("root", {})
        self.tumpukan = [self.akar]
        self.buang = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.DILEWATI:
            self.buang += 1
            return
        if self.buang:
            return
        if tag in self.TANPA_PENUTUP:
            self.tumpukan[-1].anak.append(Simpul(tag, dict(attrs), self.tumpukan[-1]))
            return
        simpul = Simpul(tag, dict(attrs), self.tumpukan[-1])
        self.tumpukan[-1].anak.append(simpul)
        self.tumpukan.append(simpul)

    def handle_startendtag(self, tag, attrs):
        if not self.buang and tag not in self.DILEWATI:
            self.tumpukan[-1].anak.append(Simpul(tag, dict(attrs), self.tumpukan[-1]))

    def handle_endtag(self, tag):
        if tag in self.DILEWATI:
            self.buang = max(0, self.buang - 1)
            return
        if self.buang:
            return
        # HTML memakai tag penutup opsional (<p>, <li>, <td>, …). Hanya pop bila
        # tag cocok dengan atas tumpukan, ATAU bila ada pembuka yang cocok lebih
        # dalam (pemulihan standar). Tanpa ini pohon HTML jadi acak dan leluhur
        # (sumber warna latar) terbaca salah -> rasio kontras palsu.
        if len(self.tumpukan) > 1 and self.tumpukan[-1].tag == tag:
            self.tumpukan.pop()
            return
        for i in range(len(self.tumpukan) - 1, 0, -1):
            if self.tumpukan[i].tag == tag:
                del self.tumpukan[i:]
                return

    def handle_data(self, data):
        if self.buang:
            return
        teks = " ".join(data.split())
        if teks:
            self.tumpukan[-1].teks.append(teks)


def rantai(simpul: Simpul):
    """[simpul, induk, kakek, …]"""
    hasil, s = [], simpul
    while s is not None:
        hasil.append(s)
        s = s.induk
    return hasil


# ───────────────────────── analisis satu halaman ─────────────────────────
def latar_efektif(simpul: Simpul, default_bg):
    """(warna_dasar, daftar_stop_gradien) dalam mode gelap."""
    dasar, stops = default_bg, []
    for s in reversed(rantai(simpul)):  # dari akar ke simpul
        gaya = s.attrs.get("style", "") or ""
        m = re.search(r"background-color:\s*([^;\"']+)", gaya)
        if m:
            w = ke_rgba(m.group(1))
            if w and w[3] >= 0.99:
                dasar, stops = w[:3], []
        kelas = kelas_efektif(s.attrs)
        # Mode gelap: varian dark: SELALU menang atas versi terang, apa pun
        # urutannya di atribut class.
        kelas_latar = ([k for k in kelas if re.match(r"dark:bg-(?!gradient)", k)]
                       or [k for k in kelas if re.match(r"bg-(?!gradient)", k)])
        ada_gradien = any(k.startswith(("bg-gradient", "dark:bg-gradient")) for k in kelas)
        if ada_gradien:
            stops = []
            for pre in ("dark:", ""):
                for arah in ("from", "via", "to"):
                    for k in kelas:
                        if k.startswith(f"{pre}{arah}-"):
                            w = stop_gradien(k if k.startswith("dark:") else "dark:" + k)
                            if w is None and pre == "":
                                w = stop_gradien(k)
                            if w:
                                stops.append(w[:3])
                if stops:
                    break
            if not stops:
                stops = [(128, 128, 128)]
        elif kelas_latar:
            for k in kelas_latar:
                w = warna_kelas(k, "background-color")
                if w:
                    if w[3] >= 0.99:
                        dasar, stops = w[:3], []
                    else:
                        dasar = blend(w, dasar)
                    break
    return dasar, stops


def teks_efektif(simpul: Simpul, default_fg):
    for s in rantai(simpul):
        gaya = s.attrs.get("style", "") or ""
        m = re.search(r"(?<![-\w])color:\s*([^;\"']+)", gaya)
        if m:
            w = ke_rgba(m.group(1))
            if w:
                return w
        kelas = kelas_efektif(s.attrs)
        pilih = next((k for k in reversed(kelas) if k.startswith("dark:text-")), None)
        if pilih is None:
            pilih = next((k for k in reversed(kelas) if k.startswith("text-")), None)
        if pilih:
            w = warna_kelas(pilih, "color")
            if w:
                return w
    return default_fg


def teks_besar(simpul: Simpul) -> bool:
    kelas = " ".join(" ".join(kelas_efektif(s.attrs)) for s in rantai(simpul))
    if re.search(r"text-(3xl|4xl|5xl|6xl|7xl)", kelas):
        return True
    return bool(re.search(r"text-(xl|2xl)", kelas)
                and re.search(r"font-(bold|black|extrabold|semibold)", kelas))


def periksa(nama: str, html: str, default_bg, default_fg) -> list:
    p = Pengurai()
    p.feed(html)
    temuan = []

    def turun(simpul: Simpul):
        if simpul.tag not in ("canvas",) and simpul.teks:
            teks = " ".join(simpul.teks)
            bg, stops = latar_efektif(simpul, default_bg)
            fg = teks_efektif(simpul, default_fg)
            if stops:
                rasio = min(kontras(blend(fg, st), st) for st in stops)
            else:
                rasio = kontras(blend(fg, bg), bg)
            ambang = AMBANG_BESAR if teks_besar(simpul) else AMBANG_NORMAL
            if rasio < ambang:
                temuan.append({
                    "halaman": nama, "teks": teks[:60], "rasio": round(rasio, 2),
                    "ambang": ambang, "kelas": (simpul.attrs.get("class") or "")[:90],
                    "tag": simpul.tag,
                })
        for a in simpul.anak:
            turun(a)

    for a in p.akar.anak:
        turun(a)
    return temuan


def debug_teks(kunci: str) -> int:
    """Tampilkan resolusi warna untuk elemen berteks tertentu (validasi auditor)."""
    default_bg = warna_kelas("dark:bg-purple-slate-950", "background-color") or (18, 11, 28)
    default_fg = warna_kelas("dark:text-purple-slate-50", "color") or (245, 240, 255)
    c = Client()
    u = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if u:
        c.force_login(u)
    print(f"Mencari teks mengandung: {kunci!r}")
    tampil = 0
    for nama, url in HALAMAN:
        jawab = c.get(url)
        if jawab.status_code != 200:
            continue
        p = Pengurai()
        p.feed(jawab.content.decode())

        def turun(s):
            nonlocal tampil
            if tampil >= 3:
                return
            if s.teks and kunci.lower() in " ".join(s.teks).lower():
                bg, stops = latar_efektif(s, default_bg)
                fg = teks_efektif(s, default_fg)
                rasa = kontras(blend(fg, bg), bg)
                print(f"  [{nama}] <{s.tag}> \"{' '.join(s.teks)[:50]}\"")
                print(f"      kelas    : {(s.attrs.get('class') or '')[:100]}")
                print(f"      teks     : {hex_dari(fg)}   latar: {hex_dari(bg)}"
                      f"{'  (gradien: ' + ', '.join(hex_dari(x) for x in stops) + ')' if stops else ''}")
                print(f"      kontras  : {rasa:.2f}:1")
                tampil += 1
            for a in s.anak:
                turun(a)

        for a in p.akar.anak:
            turun(a)
        if tampil >= 3:
            break
    return 0


def main() -> int:
    if "--debug" in sys.argv:
        i = sys.argv.index("--debug")
        return debug_teks(sys.argv[i + 1] if len(sys.argv) > i + 1 else "Dashboard")
    if not CSS.exists():
        print("[!] static/css/output.css tidak ada — jalankan: npm run build")
        return 1

    default_bg = warna_kelas("dark:bg-purple-slate-950", "background-color") or (18, 11, 28)
    default_fg = warna_kelas("dark:text-purple-slate-50", "color") or (245, 240, 255)

    c = Client()
    u = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if u:
        c.force_login(u)

    print("=" * 78)
    print("  AUDIT KONTRAS MODE GELAP — ambang 4.5:1 (normal) / 3.0:1 (teks besar)")
    print(f"  latar dasar mode gelap: {hex_dari(default_bg)}   teks dasar: {hex_dari(default_fg)}")
    print("=" * 78)

    semua = []
    for nama, url in HALAMAN:
        jawab = c.get(url)
        if jawab.status_code != 200:
            print(f"  {nama:22s} [!] HTTP {jawab.status_code} — dilewati")
            continue
        temuan = periksa(nama, jawab.content.decode(), default_bg, default_fg)
        semua.extend(temuan)
        print(f"  {nama:22s} {'OK' if not temuan else str(len(temuan)) + ' pelanggaran'}")

    if semua:
        print()
        print("-" * 78)
        print(f"  RINCIAN PELANGGARAN ({len(semua)}) — diurut dari yang terburuk")
        print("-" * 78)
        semua.sort(key=lambda t: t["rasio"])
        for t in semua[: (len(semua) if RINCI else 28)]:
            print(f"  {t['rasio']:>5.2f}:1 (min {t['ambang']}) [{t['halaman']}] "
                  f"<{t['tag']}> \"{t['teks']}\"")
            if RINCI:
                print(f"          kelas: {t['kelas']}")
    print()
    print("=" * 78)
    print(f"  HASIL: {len(semua)} elemen berteks di bawah ambang kontras")
    print("=" * 78)
    return 1 if semua else 0


if __name__ == "__main__":
    sys.exit(main())
