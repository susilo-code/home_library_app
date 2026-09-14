# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
VERIFIKASI v1.7 — LOGIKA WARNA FONT TERPUSAT (mode terang & gelap)
=================================================================
Memeriksa bahwa warna teks TIDAK lagi ditulis per elemen, melainkan diambil
dari satu tempat (variabel CSS di input.css), dan bahwa nilainya kontras
di kedua mode. Pengukuran kontras sesungguhnya di browser ada di
`scripts/dev/audit_kontras_browser.py`.

  .venv\\Scripts\\python.exe scripts\\dev\\verify_perbaikan_v7.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT_CSS = ROOT / "static/css/input.css"
OUTPUT_CSS = ROOT / "static/css/output.css"
TEMPLATES = ROOT / "templates"

lulus = 0
gagal: list[str] = []


def cek(nama: str, kondisi: bool, detail: str = "") -> None:
    global lulus
    if kondisi:
        lulus += 1
        print(f"  [OK  ] {nama}" + (f" — {detail}" if detail else ""))
    else:
        gagal.append(nama)
        print(f"  [GAGAL] {nama}" + (f" — {detail}" if detail else ""))


def bagian(judul: str) -> None:
    print()
    print("=" * 78)
    print(f"  {judul}")
    print("=" * 78)


# ── warna & kontras (WCAG 2.1) ────────────────────────────────────────────
def ke_rgb(hexstr: str):
    h = hexstr.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(rgb) -> float:
    kanal = []
    for c in rgb:
        c = c / 255
        kanal.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kanal[0] + 0.7152 * kanal[1] + 0.0722 * kanal[2]


def kontras(fg, bg) -> float:
    l1, l2 = luminance(ke_rgb(fg)), luminance(ke_rgb(bg))
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


css = INPUT_CSS.read_text(encoding="utf-8")
css_build = OUTPUT_CSS.read_text(encoding="utf-8") if OUTPUT_CSS.exists() else ""


def blok_var(selektor: str) -> dict:
    m = re.search(re.escape(selektor) + r"\s*\{([^}]*)\}", css, re.S)
    if not m:
        return {}
    return {k: v.strip() for k, v in re.findall(r"(--color-[\w-]+)\s*:\s*([^;]+);", m.group(1))}


# ── 1. SATU TEMPAT UNTUK DUA MODE ─────────────────────────────────────────
bagian("1. Logika warna terpusat (satu definisi per mode)")

terang = blok_var(":root")
gelap = blok_var(".dark")

cek("blok :root (mode terang) berisi variabel warna", len(terang) >= 12,
    f"{len(terang)} variabel")
cek("blok .dark (mode gelap) berisi variabel warna", len(gelap) >= 12,
    f"{len(gelap)} variabel")
kurang = sorted(set(terang) - set(gelap))
cek("setiap variabel mode terang punya pasangan mode gelap", not kurang,
    ", ".join(kurang) if kurang else "seimbang")
cek("tidak ada variabel gelap tanpa pasangan terang",
    not (set(gelap) - set(terang)),
    ", ".join(sorted(set(gelap) - set(terang))) or "seimbang")

for wajib in ["--color-text-primary", "--color-text-secondary", "--color-text-muted",
              "--color-bg-primary", "--color-bg-secondary", "--color-accent",
              "--color-danger-text", "--color-success-text", "--color-warning-text"]:
    cek(f"variabel {wajib} ada di kedua mode",
        wajib in terang and wajib in gelap)

# ── 2. KONTRAS TERUKUR DARI VARIABEL ──────────────────────────────────────
bagian("2. Kontras teks terhadap latar (dihitung dari variabel)")

pasangan = [
    ("teks utama", "--color-text-primary", "--color-bg-primary"),
    ("teks utama di kartu", "--color-text-primary", "--color-bg-secondary"),
    ("teks kedua di kartu", "--color-text-secondary", "--color-bg-secondary"),
    ("teks samar di kartu", "--color-text-muted", "--color-bg-secondary"),
    ("teks kedua di header kartu", "--color-text-secondary", "--color-bg-tertiary"),
    ("teks bahaya di kartu", "--color-danger-text", "--color-bg-secondary"),
    ("teks sukses di kartu", "--color-success-text", "--color-bg-secondary"),
    ("teks peringatan di kartu", "--color-warning-text", "--color-bg-secondary"),
    ("teks aksen di kartu", "--color-accent", "--color-bg-secondary"),
    ("teks aksen-2 di kartu", "--color-accent-2", "--color-bg-secondary"),
]
for mode, himpunan in (("terang", terang), ("gelap", gelap)):
    for label, var_teks, var_latar in pasangan:
        fg, bg = himpunan.get(var_teks), himpunan.get(var_latar)
        if not fg or not bg:
            cek(f"[{mode}] {label}", False, "variabel tidak lengkap")
            continue
        rasio = kontras(fg, bg)
        cek(f"[{mode}] {label} ≥ 4.5:1", rasio >= 4.5,
            f"{rasio:.2f}:1 ({fg} di {bg})")

# ── 3. KELAS SEMANTIK DIPAKAI, BUKAN PASANGAN dark: ───────────────────────
bagian("3. Template memakai kelas semantik (bukan `text-x dark:text-y`)")

KELAS = ["teks-utama", "teks-kedua", "teks-samar", "teks-aksen", "teks-aksen-dua",
         "teks-bahaya", "teks-sukses", "teks-peringatan", "badge-genre"]
for k in KELAS:
    cek(f"kelas .{k} didefinisikan di input.css", f".{k}" in css)

berkas = list(TEMPLATES.rglob("*.html"))
tanda = {k: 0 for k in KELAS}
pasangan_sisa = []
for f in berkas:
    isi = f.read_text(encoding="utf-8", errors="replace")
    for k in KELAS:
        tanda[k] += isi.count(k)
    for m in re.finditer(r'class="([^"]*)"', isi):
        cls = m.group(1)
        if "{{" in cls or "{%" in cls:
            continue
        if any(t.startswith("text-") and not t.startswith("text-white") for t in cls.split()) \
           and any(t.startswith("dark:text-") for t in cls.split()):
            pasangan_sisa.append(f"{f.name}: {cls[:60]}")
for k in KELAS:
    cek(f"kelas .{k} dipakai di template", tanda[k] > 0, f"{tanda[k]}× dipakai")
cek("tidak ada lagi pasangan `text-… dark:text-…` di template",
    not pasangan_sisa, f"{len(pasangan_sisa)} sisa")

# ── 4. DASAR HALAMAN & SUMBER CSS TUNGGAL ─────────────────────────────────
bagian("4. Dasar halaman & satu sumber CSS")

cek("body memakai variabel (bukan kelas warna)",
    "background-color: var(--color-bg-primary)" in css
    and "color: var(--color-text-primary)" in css)
body_tag = (TEMPLATES / "base.html").read_text(encoding="utf-8")
m_body = re.search(r"<body[^>]*class=\"([^\"]*)\"", body_tag)
cek("tag <body> tidak memuat kelas warna hardcoded",
    bool(m_body) and not re.search(r"(bg-|text-)[a-z]+-[0-9]{2,3}", m_body.group(1)),
    m_body.group(1) if m_body else "tag body tak ditemukan")

cdn = [f.name for f in berkas if "cdn.tailwindcss.com" in f.read_text(encoding="utf-8")]
cek("Tailwind CDN tidak lagi dipakai (satu sumber: output.css)", not cdn,
    ", ".join(cdn) if cdn else "bersih")

var_dipakai = set()
for f in berkas:
    var_dipakai |= set(re.findall(r"var\(--color-[\w-]+", f.read_text(encoding="utf-8")))
for v in sorted(var_dipakai):
    nama = v.split("(")[1]
    cek(f"variabel {nama} yang dipakai template terdefinisi", nama in terang)

# ── 5. GRAFIK MENGIKUTI TEMA (tanpa refresh) ──────────────────────────────
bagian("5. Grafik Chart.js mengikuti perubahan tema")

dash = (TEMPLATES / "dashboard.html").read_text(encoding="utf-8")
base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
cek("warna grafik dibaca sebagai fungsi (saat menggambar), bukan string",
    dash.count("() => css(") >= 10, f"{dash.count('() => css(')} opsi berupa fungsi")
cek("chart didaftarkan di window.__grafik", "window.__grafik" in dash)
cek("variabel grafik di lingkup skrip (bukan di dalam blok if)",
    "let grafikDonut = null" in dash and "let grafikBatang = null" in dash)
cek("chart digambar ulang saat tema berganti",
    "addEventListener('themechange'" in dash)
cek("base.html mengirim event themechange saat tema diganti",
    "dispatchEvent(new CustomEvent('themechange'" in base)

# ── 6. BADGE WARNA DINAMIS ────────────────────────────────────────────────
bagian("6. Badge warna dinamis (genre/rak) dijamin kontras")

css_bersih = css
cek("kelas .badge-genre memakai color-mix (aman untuk warna apa pun)",
    ".badge-genre" in css_bersih and "color-mix" in css_bersih)
inline_badge = []
for f in berkas:
    isi = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'class="badge[^"]*"[^>]*style="[^"]*color:\s*\{\{[^"]*"', isi):
        inline_badge.append(f.name)
cek("tidak ada badge dengan warna teks inline dari database",
    not inline_badge, ", ".join(set(inline_badge)) if inline_badge else "bersih")

# ── RINGKASAN ─────────────────────────────────────────────────────────────
print()
print("=" * 78)
print(f"  RINGKASAN: {lulus} LULUS, {len(gagal)} GAGAL")
for g in gagal:
    print(f"    - {g}")
print("=" * 78)
sys.exit(0 if not gagal else 1)
