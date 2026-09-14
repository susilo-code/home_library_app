# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
AUDIT KONTRAS MODE GELAP (BROWSER SUNGGUHAN)
============================================
Mengukur rasio kontras WCAG memakai **computed style** dari Chrome, sehingga
warna hasil kompilasi Tailwind v4 (oklch + var(--color-*)) ikut benar — hal yang
tidak bisa ditebak dari pembacaan CSS secara statis.

Alur:
 1. Halaman dirender lewat Django test client (sudah login), lalu disisipi skrip
    audit yang: memaksa kelas `dark`, menghitung kontras SEMUA elemen berteks
    (latar efektif diwarisi, alpha di-blend, gradien dinilai per stop), lalu
    menulis hasilnya ke DOM dalam bentuk base64.
 2. Chrome headless dijalankan dengan `--dump-dom`; hasil audit dibaca dari DOM.
 3. Ringkasan dicetak; keluar dengan kode 1 bila ada pelanggaran.

Jalankan:  .venv\\Scripts\\python.exe scripts\\dev\\audit_kontras_browser.py [--rinci]
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402
from library.models import Book  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "preview"
RINCI = "--rinci" in sys.argv

HALAMAN = [
    ("Dashboard", "dashboard"),
    ("Katalog Buku", "book-list"),
    ("Cetak Label (pilih)", "label-select"),
    ("Pengaturan", "settings"),
    ("Identitas Aplikasi", "app-identity"),
    ("Kelola Pengguna", "user-list"),
    ("Tambah Buku", "book-create"),
    ("Profil Saya", "profile"),
]
_buku = Book.objects.first()
if _buku:
    HALAMAN.append(("Detail Buku", _buku.get_absolute_url()))

KANDIDAT_CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def cari_chrome() -> str | None:
    for kunci in ("CHROME_PATH", "CHROME_EXECUTABLE"):
        nilai = os.environ.get(kunci)
        if nilai and Path(nilai).exists():
            return nilai
    if shutil.which("chrome"):
        return shutil.which("chrome")
    for p in KANDIDAT_CHROME:
        if Path(p).exists():
            return p
    return None


# Skrip yang disuntikkan ke halaman: mengukur kontras dalam mode gelap.
SKRIP_AUDIT = r"""
<script>
(function () {
  // MODE diisi oleh penulis skrip: 'gelap' atau 'terang'.
  const MODE = '__MODE__';
  // Matikan transisi: `<body>` memakai `transition-colors duration-300`, sehingga
  // getComputedStyle yang dibaca tepat sesudah kelas tema diganti masih bernilai
  // lama (nilai tengah transisi) dan menghasilkan kontras palsu.
  const tanpaTransisi = document.createElement('style');
  tanpaTransisi.textContent =
    '*,*::before,*::after{transition:none!important;animation:none!important}';
  document.head.appendChild(tanpaTransisi);
  if (MODE === 'gelap') {
    document.documentElement.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  } else {
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme', 'light');
  }
  const lum = (c) => {
    const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  const rasionya = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    const hi = Math.max(l1, l2), lo = Math.min(l1, l2);
    return (hi + 0.05) / (lo + 0.05);
  };
  const parseWarna = (s) => {
    const m = String(s).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].replace(/[\/,]/g, ' ').split(/\s+/).filter(Boolean).map(parseFloat);
    if (p.length < 3 || p.some(isNaN)) return null;
    return [p[0], p[1], p[2], (p.length > 3 && !isNaN(p[3])) ? p[3] : 1];
  };
  const blend = (f, b) => f[3] >= 1 ? [f[0], f[1], f[2]]
      : [0, 1, 2].map((i) => Math.round(f[i] * f[3] + b[i] * (1 - f[3])));
  function latar(el) {
    const tumpuk = [];
    let node = el;
    while (node && node.nodeType === 1) {
      const cs = getComputedStyle(node);
      const img = cs.backgroundImage;
      if (img && img !== 'none' && img.indexOf('gradient') >= 0) {
        const cols = (img.match(/rgba?\([^)]+\)/g) || []).map(parseWarna)
          .filter(Boolean).map((c) => c.slice(0, 3));
        if (cols.length) return { warna: cols, jen: 'gradien' };
      }
      const c = parseWarna(cs.backgroundColor);
      if (c && c[3] > 0.01) { tumpuk.push(c); if (c[3] >= 0.99) break; }
      node = node.parentElement;
    }
    let dasar = [255, 255, 255];
    for (let i = tumpuk.length - 1; i >= 0; i--) dasar = blend(tumpuk[i], dasar);
    return { warna: [dasar], jen: 'solid' };
  }

  let hasil = [];
  let warnaGrafik = null;

  function ukur() {
  hasil = [];
  document.querySelectorAll('*').forEach((el) => {
    const buang = ['SCRIPT', 'STYLE', 'SVG', 'PATH', 'CANVAS', 'IMG', 'INPUT',
                   'SELECT', 'TEXTAREA', 'OPTION', 'BR', 'SOURCE', 'MAP'];
    if (buang.indexOf(el.tagName) >= 0) return;
    if (el.closest('svg')) return;
    if (el.closest('#modal-tentang') && !el.closest('#modal-tentang').classList.contains('flex')) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return;
    const teks = Array.from(el.childNodes)
      .filter((n) => n.nodeType === 3 && n.textContent.trim())
      .map((n) => n.textContent.trim().replace(/\s+/g, ' ')).join(' ');
    if (!teks) return;
    const fg = parseWarna(cs.color);
    if (!fg) return;
    const bg = latar(el);
    const besar = parseFloat(cs.fontSize) >= 24 ||
                  (parseFloat(cs.fontSize) >= 18.66 && parseInt(cs.fontWeight, 10) >= 700);
    const ambang = besar ? 3.0 : 4.5;
    let r = 99;
    bg.warna.forEach((b) => { r = Math.min(r, rasionya(blend(fg, b), b)); });
    if (r < ambang) {
      hasil.push({
        tag: el.tagName.toLowerCase(), teks: teks.slice(0, 48),
        rasio: Math.round(r * 100) / 100, ambang: ambang,
        kelas: (el.getAttribute('class') || '').slice(0, 70),
        fg: cs.color, bg: bg.warna.map((c) => 'rgb(' + c.join(' ') + ')').join(' | '),
        jen: bg.jen
      });
    }
  });
  hasil.sort((a, b) => a.rasio - b.rasio);

  // Warna grafik Chart.js: dibaca lewat fungsi/fungsi-nilai yang dipakai chart.
  try {
    if (window.__grafik && window.__grafik.length) {
      warnaGrafik = window.__grafik.map((g, i) => {
        const jenis = g.config.type;
        let label = null, tick = null;
        try { label = g.options.plugins.legend.labels.color; } catch (e) {}
        try { tick = g.options.scales.x.ticks.color; } catch (e) {}
        const nilai = (v) => (typeof v === 'function' ? v() : v);
        return { i: i, jenis: jenis, legend: nilai(label), tick: nilai(tick) };
      });
    }
  } catch (e) { warnaGrafik = 'error: ' + e.message; }

  // Uji khusus (hanya berarti di halaman ber-grafik): setelah tombol tema
  // diklik TANPA refresh, warna grafik harus sudah mengikuti tema baru.
  let ujiToggle = null;
  function cekToggle() {
    const tombol = document.getElementById('theme-toggle');
    if (!tombol || !window.__grafik || !window.__grafik.length) return;
    tombol.click();
    const basis = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-text-secondary').trim();
    const g = window.__grafik[0];
    let nilai = null;
    try { nilai = g.options.plugins.legend.labels.color; } catch (e) {}
    const pakai = (typeof nilai === 'function') ? nilai() : nilai;
    ujiToggle = {
      modeSesudahKlik: document.documentElement.classList.contains('dark') ? 'gelap' : 'terang',
      varTeksSekunder: basis,
      warnaGrafik: String(pakai).trim(),
      cocok: String(pakai).trim() === basis
    };
  }

  const data = {
    judul: document.title,
    gelap: document.documentElement.classList.contains('dark'),
    pelanggaran: hasil,
    warnaGrafik: warnaGrafik,
    ujiToggle: (cekToggle(), ujiToggle),
    variabel: {
      teksUtama: getComputedStyle(document.documentElement).getPropertyValue('--color-text-primary').trim(),
      teksSekunder: getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim(),
      latarKartu: getComputedStyle(document.documentElement).getPropertyValue('--color-bg-secondary').trim()
    }
  };
  const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(data))));
  const pre = document.createElement('pre');
  pre.id = 'AUDIT-KONTRAS';
  pre.textContent = b64;
  document.body.appendChild(pre);
  }

  // Beri kesempatan satu siklus render sebelum mengukur.
  setTimeout(ukur, 400);
})();
</script>
"""


def render(nama: str, url: str, klien: Client, mode: str) -> Path | None:
    jawab = klien.get(url)
    if jawab.status_code != 200:
        print(f"  [!] {nama}: HTTP {jawab.status_code} — dilewati")
        return None
    html = jawab.content.decode()
    html = html.replace('="/static/', '="http://127.0.0.1:8000/static/')
    html = html.replace('="/media/', '="http://127.0.0.1:8000/media/')
    html = html.replace("url('/static/", "url('http://127.0.0.1:8000/static/")
    skrip = SKRIP_AUDIT.replace("__MODE__", mode)
    if "</body>" in html:
        html = html.replace("</body>", skrip + "</body>")
    else:
        html += skrip
    PREVIEW.mkdir(exist_ok=True)
    tujuan = PREVIEW / f"audit-{nama.lower().replace(' ', '-')}-{mode}.html"
    tujuan.write_text(html, encoding="utf-8")
    return tujuan


def jalankan_chrome(chrome: str, berkas: Path) -> str:
    url = "file:///" + str(berkas).replace("\\", "/").replace(" ", "%20")
    perintah = [
        chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--virtual-time-budget=9000", "--run-all-compositor-stages-before-draw",
        "--window-size=1440,1200", "--dump-dom", url,
    ]
    hasil = subprocess.run(perintah, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
    return hasil.stdout or ""


def ambil_data(dom: str) -> dict | None:
    m = re.search(r'<pre id="AUDIT-KONTRAS">([A-Za-z0-9+/=]+)</pre>', dom)
    if not m:
        return None
    try:
        return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    except Exception:
        return None


def main() -> int:
    chrome = cari_chrome()
    if not chrome:
        print("[!] Chrome tidak ditemukan. Set CHROME_PATH atau lewati audit ini.")
        return 1
    print(f"Chrome: {chrome}")

    klien = Client()
    pengguna = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if pengguna:
        klien.force_login(pengguna)

    print("=" * 78)
    print("  AUDIT KONTRAS DUA MODE (computed style Chrome) — ambang 4.5 / 3.0 : 1")
    print("=" * 78)

    semua, gagal_render, toggle_hasil = [], [], []
    for nama, nama_url in HALAMAN:
        url = nama_url if nama_url.startswith("/") else reverse(nama_url)
        baris = []
        for mode in ("gelap", "terang"):
            berkas = render(nama, url, klien, mode)
            if berkas is None:
                gagal_render.append(f"{nama} ({mode})")
                continue
            dom = jalankan_chrome(chrome, berkas)
            data = ambil_data(dom)
            if data is None:
                print(f"  {nama:22s} [!] hasil audit tidak terbaca dari DOM ({mode})")
                gagal_render.append(f"{nama} ({mode})")
                continue
            if bool(data.get("gelap")) != (mode == "gelap"):
                print(f"  {nama:22s} [!] kelas tema tidak sesuai mode {mode}")
                gagal_render.append(f"{nama} ({mode}): kelas tema salah")
                continue
            for p in data.get("pelanggaran", []):
                p["halaman"] = nama
                p["mode"] = mode
            semua.extend(data.get("pelanggaran", []))
            jumlah = len(data.get("pelanggaran", []))
            baris.append(f"{mode}: {'OK' if not jumlah else str(jumlah) + ' pelanggaran'}")
            # Uji toggle tema (hanya ada di halaman ber-grafik)
            ket = data.get("ujiToggle")
            if ket:
                ket["halaman"] = nama
                ket["modeAwal"] = mode
                toggle_hasil.append(ket)
        print(f"  {nama:22s} " + " | ".join(baris) if baris else f"  {nama:22s} — gagal")

    if toggle_hasil:
        print()
        print("-" * 78)
        print("  UJI TOGGLE TEMA (warna grafik TANPA refresh)")
        print("-" * 78)
        for t in toggle_hasil:
            tanda = "OK " if t.get("cocok") else "GAGAL"
            print(f"  [{tanda}] [{t['halaman']}] sesudah klik -> {t.get('modeSesudahKlik')}: "
                  f"warna grafik {t.get('warnaGrafik')} vs variabel {t.get('varTeksSekunder')}")

    if semua:
        print()
        print("-" * 78)
        print(f"  RINCIAN ({len(semua)}) — terburuk lebih dulu")
        print("-" * 78)
        semua.sort(key=lambda t: t["rasio"])
        for t in semua[: (len(semua) if RINCI else 30)]:
            print(f"  {t['rasio']:>5.2f}:1 (min {t['ambang']}) [{t['halaman']}] "
                  f"<{t['tag']}> \"{t['teks']}\"")
            if RINCI:
                print(f"          fg={t['fg']}  bg={t['bg']} ({t['jen']})")
                print(f"          kelas: {t['kelas']}")

    PREVIEW.mkdir(exist_ok=True)
    (PREVIEW / "audit-kontras.json").write_text(
        json.dumps(semua, indent=2, ensure_ascii=False), encoding="utf-8")

    toggle_gagal = [t for t in toggle_hasil if not t.get("cocok")]
    print()
    print("=" * 78)
    print(f"  HASIL: {len(semua)} elemen berteks di bawah ambang kontras (dua mode), "
          f"{len(toggle_gagal)} uji toggle gagal dari {len(toggle_hasil)}"
          f"{' | halaman gagal: ' + ', '.join(gagal_render) if gagal_render else ''}")
    print("  Rincian JSON: preview/audit-kontras.json")
    print("=" * 78)
    return 1 if (semua or gagal_render or toggle_gagal) else 0


if __name__ == "__main__":
    sys.exit(main())
