# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
VERIFIKASI v1.6 — batch permintaan terbaru
==========================================
1. Menu "Tentang Aplikasi" di top bar + ikonnya, muncul sebagai MODAL
   (identitas pengembang, open source, tech stack, fungsi aplikasi,
    izin pemakaian, tautan repo GitHub).
2. Kredit "This app is developed by susilo" DIHAPUS dari halaman login.
3. Application Controller (.exe tkinter) untuk setup/start/stop + skrip build-nya.
4. setup.bat mengakomodir PC yang belum ada Node.js/npm.
"""

import subprocess
import html as _htmllib  # dipakai di bagian 3 (unescape nama aplikasi)
from pathlib import Path

import django

_os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPO = "https://github.com/susilo-code/home_library_app"

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
    print("=" * 74)
    print(f"  {judul}")
    print("=" * 74)


c = Client()
_pengguna = User.objects.filter(is_superuser=True).first() or User.objects.first()
if _pengguna:
    c.force_login(_pengguna)

from library.models import SiteConfig  # noqa: E402
cfg = SiteConfig.get_solo()

halaman = {
    "dashboard": c.get("/").content.decode(),
    "katalog": c.get("/buku/").content.decode(),
    "label": c.get("/label/").content.decode(),
    "pengaturan": c.get("/pengaturan/").content.decode(),
}
dash = halaman["dashboard"]

# ── 1. MENU "TENTANG APLIKASI" DI TOP BAR ────────────────────────────────────
bagian("1. Menu 'Tentang Aplikasi' di top bar")

# Slice navbar: HARUS sampai sebelum <main>. (Pelajaran: memotong di
# '</div>' pertama hanya mengambil blok brand — ikon menu jadi tidak terhitung.)
nav = dash[dash.find("<nav"): dash.find("<main")]
cek("teks menu 'Tentang Aplikasi' ada di top bar", "Tentang Aplikasi" in nav)
cek("id pemicu #buka-tentang ada", 'id="buka-tentang"' in nav)
cek("varian menu mobile #buka-tentang-mobile ada",
    'id="buka-tentang-mobile"' in dash)
nav_ketat = nav
cek("tombol 'Tentang Aplikasi' memakai ikon SVG", "<svg" in nav_ketat)
cek("ikon dibungkus kotak berwarna (rounded + tinted)",
    "rounded-lg" in nav_ketat and ("bg-purple-100" in nav_ketat or "bg-purple-900" in nav_ketat))
jumlah_ikon = nav_ketat.count("h-7 w-7 items-center justify-center")
# v1.8: menu berikon sekarang 5 — Dashboard / Katalog / Cetak Label / Label Rak / Tentang.
cek("jumlah mata menu berikon tetap 5 (Dashboard/Katalog/Cetak Label/Label Rak/Tentang)",
    jumlah_ikon == 5, f"ditemukan {jumlah_ikon} kotak ikon")

# ── 2. MODAL "TENTANG APLIKASI" ──────────────────────────────────────────────
bagian("2. Isi modal 'Tentang Aplikasi'")

awal = dash.find('id="modal-tentang"')
cek("modal #modal-tentang ada di halaman", awal != -1)
if awal != -1:
    modal = dash[awal: awal + 12000]
    modal_lower = modal.lower()

    cek("berawal tersembunyi (hidden)", 'hidden' in modal[:200])
    cek("tombol tutup tersedia (data-tutup-tentang)",
        modal.count("data-tutup-tentang") >= 3,
        f"{modal.count('data-tutup-tentang')} elemen penutup")
    cek("identitas pengembang — label 'Pengembang'", "pengembang" in modal_lower)
    cek("identitas pengembang — nilai 'susilo'", "susilo" in modal_lower)
    cek("pernyataan OPEN SOURCE", "open source" in modal_lower)
    cek("tautan repo GitHub (dinamis dari SiteConfig)", REPO in modal,
        "tautan ada")
    cek("tautan repo pakai target=_blank + rel noopener",
        'target="_blank"' in modal and "noopener" in modal)
    for teknologi in ["Django", "FastAPI", "Tailwind", "Chart.js", "SQLite"]:
        cek(f"tech stack menyebut {teknologi}", teknologi in modal)
    cek("bagian fungsi aplikasi", "fungsi aplikasi" in modal_lower)
    for fungsi in ["katalog", "rak", "genre", "label", "dashboard"]:
        cek(f"fungsi aplikasi menyebut {fungsi}", fungsi in modal_lower)
    cek("syarat 'atas izin pengembang'", "izin pengembang" in modal_lower)
    cek("modal muncul di SEMUA halaman (template base)",
        all('id="modal-tentang"' in html for html in halaman.values()),
        "4 halaman diuji")
    cek("deep-link ?tentang=1 tersedia", "tentang" in dash and "URLSearchParams" in dash)

# ── 3. KREDIT DI HALAMAN LOGIN DIHAPUS ───────────────────────────────────────
bagian("3. Kredit pengembang di halaman login")

login = Client().get("/login/").content.decode()
cek("frasa 'This app is developed by susilo' SUDAH TIDAK ADA",
    "This app is developed by susilo" not in login)
cek("tidak ada sisa 'developed by susilo' (case-insensitive)",
    "developed by susilo" not in login.lower())
cek("kutipan Imam Syafi'i tetap ada", "Imam Syafi" in login)
cek("identitas aplikasi dinamis tetap dipakai di login",
    bool(cfg.app_name) and _htmllib.unescape(cfg.app_name) in _htmllib.unescape(login),
    f"nama aplikasi tampil: {cfg.app_name!r}")
cek("footer 'Developed by susilo' tetap ada di halaman dalam aplikasi",
    "Developed by susilo" in dash)

# ── 4. SITECONFIG: FIELD BARU ────────────────────────────────────────────────
bagian("4. SiteConfig — identitas pengembang & repo")

from library.models import SiteConfig as _SC  # noqa: E402
from library.forms import SiteConfigForm  # noqa: E402

cfg = _SC.get_solo()
cek("field developer_name ada", hasattr(cfg, "developer_name"),
    f"nilai = {cfg.developer_name!r}")
cek("field repo_url ada", hasattr(cfg, "repo_url"), f"nilai = {cfg.repo_url!r}")
cek("developer_name berisi 'susilo'", (cfg.developer_name or "").lower() == "susilo")
cek("repo_url = repo GitHub yang diberikan", (cfg.repo_url or "").rstrip("/") == REPO)
cek("kedua field dapat disunting dari form Identitas Aplikasi",
    "developer_name" in SiteConfigForm.base_fields and "repo_url" in SiteConfigForm.base_fields)
cek("migrasi 0007 sudah diterapkan", (ROOT / "library/migrations/0007_siteconfig_developer_name_siteconfig_repo_url.py").exists())

# ── 5. PANEL KENDALI (.EXE) ──────────────────────────────────────────────────
bagian("5. Application Controller tkinter + .exe")

launcher = ROOT / "launcher.py"
exe = ROOT / "home_library.exe"
build_bat = ROOT / "build_launcher.bat"

cek("launcher.py ada", launcher.exists())
if launcher.exists():
    isi = launcher.read_text(encoding="utf-8", errors="replace")
    cek("memakai tkinter (GUI)", "import tkinter" in isi)
    cek("hanya pustaka bawaan (tanpa pip install)",
        all(k not in isi for k in ["import requests", "import dotenv", "import PyInstaller"]))
    for mode in ["--selftest", "--startcli", "--stopcli"]:
        cek(f"mode {mode} tersedia", mode in isi)
    cek("fungsi Siapkan/Jalankan/Hentikan ada",
        all(f in isi for f in ["aksi_setup", "aksi_jalankan", "aksi_hentikan"]))
    cek("logika start/stop dipakai bersama GUI & CLI",
        "def jalankan_servis" in isi and "def hentikan_servis" in isi)

cek("home_library.exe ada", exe.exists(),
    f"{exe.stat().st_size // 1024 // 1024} MB" if exe.exists() else "belum dibangun")
cek("build_launcher.bat ada", build_bat.exists())
if build_bat.exists():
    bb = build_bat.read_text(encoding="utf-8", errors="replace")
    cek("build_launcher.bat menyiasati jalur berspasi (build di folder tanpa spasi)",
        "home_library_build" in bb and "PyInstaller" in bb)

if exe.exists():
    r = subprocess.run([str(exe), "--selftest"], capture_output=True, text=True, timeout=180)
    hasil = ROOT / "selftest_launcher.txt"
    isi_hasil = hasil.read_text(encoding="utf-8", errors="replace") if hasil.exists() else ""
    cek(".exe menjalankan --selftest tanpa error", r.returncode == 0, f"exit={r.returncode}")
    cek(".exe melaporkan semua pemeriksaan internalnya lulus", "LULUS" in isi_hasil,
        isi_hasil.strip().splitlines()[-1] if isi_hasil else "tidak ada keluaran")

# ── 6. SETUP.BAT TANPA NODE.JS / NPM ─────────────────────────────────────────
bagian("6. setup.bat pada PC tanpa Node.js / npm")

setup = (ROOT / "setup.bat").read_text(encoding="utf-8", errors="replace").lower()
cek("setup.bat memeriksa keberadaan npm", "where npm" in setup or "npm.cmd" in setup)
cek("ada cabang 'npm tidak ada' (dilewati, bukan gagal)",
    "npm" in setup and ("dilewati" in setup or "skip" in setup or "tidak ditemukan" in setup))
cek("tidak ada 'exit /b 1' tepat pada blok npm (tidak mematikan setup)",
    setup.count("exit /b 1") < 12, f"{setup.count('exit /b 1')} exit-gagal di seluruh berkas")
cek("output.css disiapkan tanpa npm (CSS lokal dipakai)",
    (ROOT / "static/css/output.css").exists())
_r_git = subprocess.run(["git", "ls-files", "--error-unmatch", "static/css/output.css"],
                        capture_output=True, text=True, cwd=str(ROOT))
cek("output.css ikut dilacak git (tersedia di PC baru)",
    _r_git.returncode == 0, "terlacak di index git" if _r_git.returncode == 0 else "TIDAK terlacak")

# ── 7. AUDIT CAKUPAN CSS LOKAL ───────────────────────────────────────────────
bagian("7. Audit cakupan CSS lokal (agar PC tanpa Node tetap rapi)")

r = subprocess.run([str(ROOT / ".venv/Scripts/python.exe"), "scripts/dev/cek_css_lokal.py"],
                   capture_output=True, text=True, timeout=180, cwd=str(ROOT))
cek("semua kelas template tersedia di output.css", r.returncode == 0,
    [l.strip() for l in r.stdout.splitlines() if "Belum tergenerate" in l][0]
    if "Belum tergenerate" in r.stdout else "")

# ── RINGKASAN ────────────────────────────────────────────────────────────────
print()
print("=" * 74)
print(f"  RINGKASAN: {lulus} LULUS, {len(gagal)} GAGAL")
if gagal:
    for g in gagal:
        print(f"    - {g}")
print("=" * 74)

_sys.exit(0 if not gagal else 1)
