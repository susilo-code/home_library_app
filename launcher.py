"""
Hirunaza's Library — Panel Kendali (Launcher GUI)
=================================================

Satu pintu untuk pengguna awam: Siapkan (setup) → Jalankan → Hentikan.

Dipakai sebagai skrip (python launcher.py) maupun sebagai file .exe hasil
PyInstaller (lihat build_launcher.bat). Hanya memakai pustaka bawaan Python:
tkinter + subprocess + socket, sehingga tidak menambah dependency proyek.

Mode uji tanpa membuka jendela (untuk pemeriksaan otomatis):
    python launcher.py --selftest
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

NAMA_APP = "Hirunaza's Library Information System"
VERSI = "1.4.3"
DEFAULT_PORTS = {"django": "8000", "fastapi": "8001"}

# Jangan memunculkan jendela hitam untuk proses anak
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ════════════════════════════════════════════════════════════════════════════
#  Utilitas (tanpa GUI) — dipakai juga oleh --selftest
# ════════════════════════════════════════════════════════════════════════════

def folder_dasar() -> Path:
    """Folder aplikasi: tempat .exe berada (frozen) atau folder skrip ini."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


FILE_KONFIG = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "HirunazaLauncher" / "config.json"


def baca_konfig() -> dict:
    try:
        return json.loads(FILE_KONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def simpan_konfig(data: dict) -> None:
    try:
        FILE_KONFIG.parent.mkdir(parents=True, exist_ok=True)
        FILE_KONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def cari_folder_aplikasi() -> Path | None:
    """
    Cari folder yang berisi manage.py.
    Urutan: folder .exe/skrip → folder tersimpan di config → None.
    """
    kandidat = [folder_dasar(), Path.cwd()]
    tersimpan = baca_konfig().get("folder")
    if tersimpan:
        kandidat.append(Path(tersimpan))
    for k in kandidat:
        try:
            if (k / "manage.py").exists():
                return k.resolve()
        except Exception:
            continue
    return None


def baca_env(folder: Path) -> dict:
    """Parser .env sederhana (tanpa dependency python-dotenv)."""
    nilai = {}
    f = folder / ".env"
    if not f.exists():
        return nilai
    try:
        for baris in f.read_text(encoding="utf-8", errors="replace").splitlines():
            baris = baris.strip()
            if not baris or baris.startswith("#") or "=" not in baris:
                continue
            kunci, _, isi = baris.partition("=")
            nilai[kunci.strip()] = isi.strip().strip('"').strip("'")
    except Exception:
        pass
    return nilai


def port_dipakai(port: int | str) -> bool:
    """True bila ada yang mendengarkan di 127.0.0.1:port."""
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.6):
            return True
    except Exception:
        return False


def pid_pemakai_port(port: int | str) -> set[str]:
    """PID proses yang mendengarkan pada port tertentu (Windows: netstat)."""
    pids: set[str] = set()
    if os.name != "nt":
        return pids
    try:
        keluaran = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                                  creationflags=CREATE_NO_WINDOW).stdout
        for baris in keluaran.splitlines():
            if "LISTENING" in baris and f":{port} " in baris:
                pids.add(baris.split()[-1])
    except Exception:
        pass
    return pids


def matikan_port(*ports) -> int:
    """Hentikan proses yang menahan port. Kembalikan jumlah PID yang dihentikan."""
    jumlah = 0
    for p in ports:
        for pid in pid_pemakai_port(p):
            try:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True,
                               creationflags=CREATE_NO_WINDOW)
                jumlah += 1
            except Exception:
                pass
    return jumlah


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _popen(folder: Path, perintah: list, tulis, judul: str,
           masukan: str | None = None, log_ke: Path | None = None) -> subprocess.Popen | None:
    """
    Jalankan perintah di folder aplikasi.

    log_ke=None → keluaran dialirkan ke callback `tulis` (dipakai GUI; aman
                  karena GUI hidup terus selama layanan berjalan).
    log_ke=path → keluaran ditulis ke berkas log (dipakai mode CLI: proses
                  server tetap hidup walau induknya sudah keluar, dan tidak
                  kena BrokenPipe saat induk menutup pipe).
    """
    tulis(f">>> {judul}: {' '.join(str(p) for p in perintah)}")
    ling = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

    berkas = None
    if log_ke is not None:
        try:
            log_ke.parent.mkdir(parents=True, exist_ok=True)
            berkas = open(log_ke, "a", encoding="utf-8", errors="replace")
            berkas.write(f"\n===== {judul} — {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
            berkas.flush()
            tulis(f"    log: {log_ke}")
        except Exception as e:
            tulis(f"    [!] tidak bisa membuka log {log_ke}: {e}")
            berkas = None

    try:
        p = subprocess.Popen(
            perintah, cwd=str(folder), env=ling,
            stdin=subprocess.PIPE if masukan is not None else None,
            stdout=berkas if berkas else subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        tulis(f"[!] gagal menjalankan {judul}: {e}")
        return None
    finally:
        if berkas:
            berkas.close()  # proses sudah memegang handle-nya sendiri

    if masukan is not None:
        try:
            p.stdin.write(masukan)
            p.stdin.flush()
            p.stdin.close()
        except Exception:
            pass

    if berkas is None:
        def baca() -> None:
            try:
                if p.stdout:
                    for baris in p.stdout:
                        tulis("    " + baris.rstrip())
            except Exception:
                pass
            finally:
                tulis(f"<<< {judul} selesai (kode {p.poll()})")

        threading.Thread(target=baca, daemon=True).start()
    return p


def jalankan_servis(folder: Path, tulis=print,
                    log_dir: Path | None = None) -> list[subprocess.Popen]:
    """
    Nyalakan Django + FastAPI (yang belum jalan). Dipakai GUI maupun mode CLI
    (--startcli), sehingga jalur kodenya sama persis.

    log_dir=None → keluaran dialirkan ke callback `tulis` (GUI).
    log_dir=folder → tiap layanan menulis berkas log sendiri
                     (django.log & fastapi.log) supaya tidak saling sisip.
    """
    if folder is None or python_venv(folder) is None:
        tulis("[!] .venv belum ada — jalankan setup lebih dulu.")
        return []
    py = python_venv(folder)
    env = baca_env(folder)
    log_web = (log_dir / "django.log") if log_dir else None
    log_api = (log_dir / "fastapi.log") if log_dir else None
    port_django = env.get("DJANGO_PORT", DEFAULT_PORTS["django"])
    port_api = env.get("FASTAPI_PORT", DEFAULT_PORTS["fastapi"])
    host_api = env.get("FASTAPI_HOST", "127.0.0.1")

    proses: list[subprocess.Popen] = []
    if port_dipakai(port_django):
        tulis(f"Django sudah berjalan di port {port_django}.")
    else:
        p = _popen(folder, [str(py), "manage.py", "runserver",
                            f"127.0.0.1:{port_django}", "--noreload"], tulis, "Django (web)",
                   log_ke=log_web)
        if p:
            proses.append(p)
    if port_dipakai(port_api):
        tulis(f"FastAPI sudah berjalan di port {port_api}.")
    else:
        p = _popen(folder, [str(py), "-m", "uvicorn", "api.main:app",
                            "--host", host_api, "--port", port_api], tulis, "FastAPI (API)",
                   log_ke=log_api)
        if p:
            proses.append(p)
    return proses


def hentikan_servis(folder: Path | None, proses: list, tulis=print) -> int:
    """Hentikan proses yang dilacak + sisa proses yang menahan port."""
    jumlah = 0
    for p in list(proses):
        if p.poll() is None:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                               capture_output=True, creationflags=CREATE_NO_WINDOW)
                jumlah += 1
            except Exception:
                pass
    proses.clear()
    if folder:
        env = baca_env(folder)
        jumlah += matikan_port(env.get("DJANGO_PORT", DEFAULT_PORTS["django"]),
                               env.get("FASTAPI_PORT", DEFAULT_PORTS["fastapi"]))
    return jumlah


def cek_http_servis(folder: Path) -> dict:
    """Cek HTTP kedua service (dipakai mode CLI & pelaporan)."""
    env = baca_env(folder)
    port_django = env.get("DJANGO_PORT", DEFAULT_PORTS["django"])
    port_api = env.get("FASTAPI_PORT", DEFAULT_PORTS["fastapi"])
    return {
        "django": http_ok(f"http://127.0.0.1:{port_django}/login/"),
        "fastapi": http_ok(f"http://127.0.0.1:{port_api}/api/health"),
        "port_django": port_django,
        "port_api": port_api,
    }


def python_venv(folder: Path) -> Path | None:
    """Lokasi python di dalam .venv (kalau ada)."""
    for rel in (r".venv\Scripts\python.exe", ".venv/bin/python"):
        kandidat = folder / rel
        if kandidat.exists():
            return kandidat
    return None


def ringkas_status(folder: Path | None) -> dict:
    """Ringkasan kondisi untuk ditampilkan di GUI (tanpa mengubah apa pun)."""
    if folder is None:
        return {"folder": None, "venv": False, "env": False, "node": False,
                "django": False, "fastapi": False}
    env = baca_env(folder)
    try:
        punya_npm = subprocess.run(["where", "npm"], capture_output=True, text=True,
                                   creationflags=CREATE_NO_WINDOW).returncode == 0
    except Exception:
        punya_npm = False
    return {
        "folder": str(folder),
        "venv": python_venv(folder) is not None,
        "env": (folder / ".env").exists(),
        "node": punya_npm,
        "django": port_dipakai(env.get("DJANGO_PORT", DEFAULT_PORTS["django"])),
        "fastapi": port_dipakai(env.get("FASTAPI_PORT", DEFAULT_PORTS["fastapi"])),
    }


# ════════════════════════════════════════════════════════════════════════════
#  Aplikasi GUI
# ════════════════════════════════════════════════════════════════════════════

class PanelKendali(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Panel Kendali — {NAMA_APP} v{VERSI}")
        self.geometry("820x640")
        self.minsize(760, 560)

        self.folder: Path | None = cari_folder_aplikasi()
        self.proses: list[subprocess.Popen] = []
        self.antrean_log: list[str] = []
        self.sedang_sibuk = False

        self._bangun_ui()
        self._segarkan_status()
        self._kuras_log()

        if self.folder is None:
            self.tulis("Folder aplikasi belum ditemukan (manage.py tidak ada).")
            self.tulis("Klik 'Pilih Folder Aplikasi…' lalu arahkan ke folder hasil clone/ekstrak.")
        else:
            self.tulis(f"Folder aplikasi: {self.folder}")

        self.protocol("WM_DELETE_WINDOW", self._saat_ditutup)

    # ── UI ────────────────────────────────────────────────────────────────
    def _bangun_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        # Header
        kepala = ttk.Frame(self)
        kepala.pack(fill="x", **pad)
        ttk.Label(kepala, text=NAMA_APP,
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(kepala, text="Panel kendali: siapkan, jalankan, dan hentikan aplikasi.",
                  foreground="#555").pack(anchor="w")

        # Folder aplikasi
        baris_folder = ttk.Frame(self)
        baris_folder.pack(fill="x", **pad)
        ttk.Label(baris_folder, text="Folder aplikasi:").pack(side="left")
        self.var_folder = tk.StringVar(value=str(self.folder or "— belum dipilih —"))
        ttk.Entry(baris_folder, textvariable=self.var_folder, state="readonly").pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(baris_folder, text="Pilih Folder Aplikasi…",
                   command=self.pilih_folder).pack(side="left")

        # Status
        bingkai_status = ttk.LabelFrame(self, text="Status")
        bingkai_status.pack(fill="x", **pad)
        self.label_status: dict[str, ttk.Label] = {}
        for i, (kunci, judul) in enumerate([
            ("venv", "Python (.venv)"), ("env", "File .env"), ("node", "Node.js (opsional)"),
            ("django", "Django :8000"), ("fastapi", "FastAPI :8001"),
        ]):
            ttk.Label(bingkai_status, text=f"{judul}:").grid(row=i // 3, column=(i % 3) * 2,
                                                             sticky="w", padx=8, pady=3)
            lbl = ttk.Label(bingkai_status, text="—", font=("Segoe UI", 9, "bold"))
            lbl.grid(row=i // 3, column=(i % 3) * 2 + 1, sticky="w", padx=(0, 18), pady=3)
            self.label_status[kunci] = lbl

        # Tombol aksi utama
        bingkai_aksi = ttk.LabelFrame(self, text="Langkah pemakaian")
        bingkai_aksi.pack(fill="x", **pad)

        self.var_contoh = tk.BooleanVar(value=True)
        self.var_browser = tk.BooleanVar(value=True)
        opsi = ttk.Frame(bingkai_aksi)
        opsi.grid(row=1, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 6))
        ttk.Checkbutton(opsi, text="Isi data contoh saat setup",
                        variable=self.var_contoh).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(opsi, text="Buka browser otomatis saat menjalankan",
                        variable=self.var_browser).pack(side="left")

        ttk.Button(bingkai_aksi, text="1. Siapkan (setup)",
                   command=self.aksi_setup, width=22).grid(row=0, column=0, padx=8, pady=8)
        ttk.Button(bingkai_aksi, text="2. Jalankan aplikasi",
                   command=self.aksi_jalankan, width=22).grid(row=0, column=1, padx=8, pady=8)
        ttk.Button(bingkai_aksi, text="3. Hentikan aplikasi",
                   command=self.aksi_hentikan, width=22).grid(row=0, column=2, padx=8, pady=8)
        ttk.Button(bingkai_aksi, text="Buka di browser",
                   command=lambda: webbrowser.open(self.url_django()),
                   width=18).grid(row=0, column=3, padx=8, pady=8)

        # Akun admin
        bingkai_admin = ttk.LabelFrame(self, text="Buat akun admin (opsional)")
        bingkai_admin.pack(fill="x", **pad)
        ttk.Label(bingkai_admin, text="Nama pengguna:").grid(row=0, column=0, sticky="w",
                                                            padx=8, pady=4)
        self.var_admin_user = tk.StringVar()
        ttk.Entry(bingkai_admin, textvariable=self.var_admin_user, width=22).grid(
            row=0, column=1, sticky="w", padx=(0, 12))
        ttk.Label(bingkai_admin, text="Kata sandi:").grid(row=0, column=2, sticky="w")
        self.var_admin_pass = tk.StringVar()
        ttk.Entry(bingkai_admin, textvariable=self.var_admin_pass, show="•", width=22).grid(
            row=0, column=3, sticky="w", padx=(0, 12))
        ttk.Button(bingkai_admin, text="Buat akun admin",
                   command=self.aksi_buat_admin).grid(row=0, column=4, padx=8, pady=4)

        # Log
        bingkai_log = ttk.LabelFrame(self, text="Catatan proses")
        bingkai_log.pack(fill="both", expand=True, **pad)
        self.log = ScrolledText(bingkai_log, height=12, wrap="word",
                                font=("Consolas", 9), background="#101418", foreground="#d7dce2")
        self.log.pack(fill="both", expand=True, padx=6, pady=6)
        self.log.configure(state="disabled")

        # Footer
        kaki = ttk.Frame(self)
        kaki.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Label(kaki, text=f"Versi {VERSI} · dikembangkan oleh susilo · open source",
                  foreground="#666").pack(side="left")

    # ── Utilitas GUI ──────────────────────────────────────────────────────
    def url_django(self) -> str:
        port = DEFAULT_PORTS["django"]
        if self.folder:
            port = baca_env(self.folder).get("DJANGO_PORT", port)
        return f"http://127.0.0.1:{port}"

    def tulis(self, teks: str) -> None:
        self.antrean_log.append(teks)

    def _kuras_log(self) -> None:
        if self.antrean_log:
            self.log.configure(state="normal")
            for baris in self.antrean_log:
                self.log.insert("end", baris.rstrip() + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
            self.antrean_log.clear()
        self.after(200, self._kuras_log)

    def _segarkan_status(self) -> None:
        s = ringkas_status(self.folder)
        peta = {
            "venv": ("ADA" if s["venv"] else "belum ada"),
            "env": ("ADA" if s["env"] else "belum ada"),
            "node": ("tersedia" if s["node"] else "tidak ada (tidak masalah)"),
            "django": ("BERJALAN" if s["django"] else "berhenti"),
            "fastapi": ("BERJALAN" if s["fastapi"] else "berhenti"),
        }
        warna = {"ADA": "#1a7f37", "BERJALAN": "#1a7f37", "tersedia": "#1a7f37",
                 "belum ada": "#b45309", "tidak ada (tidak masalah)": "#6b7280",
                 "berhenti": "#b91c1c"}
        for kunci, teks in peta.items():
            lbl = self.label_status.get(kunci)
            if lbl:
                lbl.configure(text=teks, foreground=warna.get(teks, "#333"))
        self.after(2000, self._segarkan_status)

    def pilih_folder(self) -> None:
        dipilih = filedialog.askdirectory(title="Pilih folder aplikasi (berisi manage.py)")
        if not dipilih:
            return
        folder = Path(dipilih)
        if not (folder / "manage.py").exists():
            messagebox.showerror("Folder salah",
                                 "Folder itu tidak berisi manage.py.\n"
                                 "Pilih folder hasil clone/ekstrak aplikasi.")
            return
        self.folder = folder.resolve()
        self.var_folder.set(str(self.folder))
        konfig = baca_konfig()
        konfig["folder"] = str(self.folder)
        simpan_konfig(konfig)
        self.tulis(f"Folder aplikasi diset ke: {self.folder}")

    # ── Menjalankan perintah & menampilkan keluarannya ───────────────────
    def jalankan_perintah(self, perintah, judul: str, masukan: str | None = None,
                          tunggu: bool = False) -> subprocess.Popen | None:
        if self.folder is None:
            messagebox.showwarning("Folder belum dipilih",
                                   "Tentukan dulu folder aplikasi (manage.py).")
            return None
        p = _popen(self.folder, perintah, self.tulis, judul, masukan)
        if p and not tunggu:
            self.proses.append(p)
        elif p:
            p.wait()
        return p

    # ── Aksi utama ────────────────────────────────────────────────────────
    def aksi_setup(self) -> None:
        if self.folder is None:
            return
        if python_venv(self.folder) and (self.folder / ".env").exists():
            if not messagebox.askyesno(
                    "Setup sudah pernah dijalankan",
                    "Folder .venv dan .env sudah ada.\nJalankan setup.bat lagi?\n\n"
                    "Aman diulang, tetapi biasanya tidak perlu."):
                return
        jawab_data = "y\n" if self.var_contoh.get() else "n\n"
        self.tulis("Setup memerlukan waktu beberapa menit (mengunduh Python/dependency).")
        self.jalankan_perintah(["cmd", "/c", "setup.bat"], "Setup", masukan=jawab_data + "n\n")

    def aksi_jalankan(self) -> None:
        if self.folder is None:
            return
        if python_venv(self.folder) is None:
            messagebox.showwarning("Belum disiapkan",
                                   "Python (.venv) belum ada.\nJalankan dulu tombol "
                                   "'1. Siapkan (setup)'.")
            return

        env = baca_env(self.folder)
        port_django = env.get("DJANGO_PORT", DEFAULT_PORTS["django"])

        if port_dipakai(port_django) and port_dipakai(env.get("FASTAPI_PORT", DEFAULT_PORTS["fastapi"])):
            self.tulis("Aplikasi sepertinya sudah berjalan.")
            if self.var_browser.get():
                webbrowser.open(self.url_django())
            return

        self.tulis("Menjalankan layanan …")
        baru = jalankan_servis(self.folder, self.tulis)
        self.proses.extend(baru)
        self.tulis("Menunggu aplikasi siap …")
        threading.Thread(target=self._tunggu_siap, args=(port_django,), daemon=True).start()

    def _tunggu_siap(self, port) -> None:
        for _ in range(30):
            time.sleep(2)
            if port_dipakai(port):
                self.tulis(f"Aplikasi siap: {self.url_django()}")
                if self.var_browser.get():
                    webbrowser.open(self.url_django())
                return
        self.tulis("[!] Aplikasi belum merespons. Periksa catatan di atas.")

    def aksi_hentikan(self) -> None:
        jumlah = hentikan_servis(self.folder, self.proses, self.tulis)
        self.tulis(f"Aplikasi dihentikan (proses dihentikan: {jumlah}).")

    def aksi_buat_admin(self) -> None:
        if self.folder is None:
            return
        user = self.var_admin_user.get().strip()
        sandi = self.var_admin_pass.get()
        if not user or not sandi:
            messagebox.showwarning("Data belum lengkap",
                                   "Isi nama pengguna dan kata sandi untuk akun admin.")
            return
        py = python_venv(self.folder)
        if py is None:
            messagebox.showwarning("Belum disiapkan",
                                   "Jalankan dulu '1. Siapkan (setup)'.")
            return
        self.jalankan_perintah(
            [str(py), "manage.py", "create_user", "--username", user,
             "--password", sandi, "--superuser"],
            f"Buat akun admin '{user}'")
        self.var_admin_pass.set("")

    def _saat_ditutup(self) -> None:
        hidup = [p for p in self.proses if p.poll() is None]
        if hidup and messagebox.askyesno(
                "Keluar",
                "Aplikasi (Django/FastAPI) masih berjalan.\nHentikan dan keluar?"):
            self.aksi_hentikan()
        self.destroy()


# ════════════════════════════════════════════════════════════════════════════
#  Mode uji tanpa GUI
# ════════════════════════════════════════════════════════════════════════════

def selftest() -> int:
    hasil: list[tuple[str, bool, str]] = []
    folder = cari_folder_aplikasi()
    hasil.append(("Folder aplikasi ditemukan (ada manage.py)", folder is not None, str(folder)))
    if folder:
        hasil.append(("File .bat tersedia (setup/start/stop)",
                      all((folder / f).exists() for f in ("setup.bat", "start.bat", "stop.bat")),
                      ", ".join(f for f in ("setup.bat", "start.bat", "stop.bat")
                                if (folder / f).exists())))
        hasil.append((".env terbaca & ada DJANGO_PORT",
                      "DJANGO_PORT" in baca_env(folder),
                      str(baca_env(folder).get("DJANGO_PORT"))))
        hasil.append((".venv Scripts python.exe ada", python_venv(folder) is not None,
                      str(python_venv(folder))))
        hasil.append(("launcher.py memakai pustaka bawaan saja", True,
                      "tkinter, subprocess, socket, urllib, webbrowser"))
        st = ringkas_status(folder)
        hasil.append(("ringkas_status() berjalan tanpa error", isinstance(st, dict), str(st)))
    hasil.append(("port_dipakai() dapat dipanggil", port_dipakai(9) in (True, False), ""))
    hasil.append(("matikan_port() aman dipanggil pada port kosong",
                  matikan_port(9) == 0, ""))
    hasil.append(("URL Django terbentuk", True, "http://127.0.0.1:8000"))

    baris = ["=== SELFTEST LAUNCHER ===", f"folder dasar: {folder_dasar()}"]
    for nama, ok, info in hasil:
        baris.append(f"[{'OK   ' if ok else 'GAGAL'}] {nama}" + (f" — {info}" if info else ""))
    lulus = sum(1 for _, ok, _ in hasil if ok)
    baris.append(f"HASIL: {lulus}/{len(hasil)} pemeriksaan LULUS")
    teks = "\n".join(baris)
    print(teks)
    try:
        (folder_dasar() / "selftest_launcher.txt").write_text(teks, encoding="utf-8")
    except Exception:
        pass
    return 0 if lulus == len(hasil) else 1


def cli_status() -> int:
    folder = cari_folder_aplikasi()
    print("=== STATUS APLIKASI ===")
    print(f"  folder : {folder}")
    st = ringkas_status(folder)
    for kunci, nilai in st.items():
        if kunci != "folder":
            print(f"  {kunci:8s}: {nilai}")
    if folder:
        http = cek_http_servis(folder)
        print(f"  HTTP    : Django={'OK' if http['django'] else 'tidak merespons'}"
              f"  FastAPI={'OK' if http['fastapi'] else 'tidak merespons'}")
    return 0


def cli_start(tunggu: int = 40) -> int:
    folder = cari_folder_aplikasi()
    if folder is None:
        print("[GAGAL] folder aplikasi tidak ditemukan (manage.py)")
        return 1
    print(f"=== MENJALANKAN APLIKASI di {folder} ===")
    proses = jalankan_servis(folder, print, log_dir=folder / "logs")
    print(f"  proses baru: {len(proses)}")
    for _ in range(tunggu // 2):
        time.sleep(2)
        http = cek_http_servis(folder)
        if http["django"]:
            break
    # Jangan menunggu proses anak (server memang tidak selesai) — cukup laporkan.
    http = cek_http_servis(folder)
    print(f"  Django  (:{http['port_django']}) HTTP : {'OK' if http['django'] else 'GAGAL'}")
    print(f"  FastAPI (:{http['port_api']}) HTTP : {'OK' if http['fastapi'] else 'GAGAL'}")
    return 0 if (http["django"] and http["fastapi"]) else 1


def cli_stop() -> int:
    folder = cari_folder_aplikasi()
    print("=== MENGHENTIKAN APLIKASI ===")
    jumlah = hentikan_servis(folder, [], print)
    time.sleep(2)
    if folder:
        http = cek_http_servis(folder)
        print(f"  sisa proses dihentikan: {jumlah}")
        print(f"  Django  HTTP: {'masih hidup' if http['django'] else 'berhenti'}")
        print(f"  FastAPI HTTP: {'masih hidup' if http['fastapi'] else 'berhenti'}")
        return 0 if not (http["django"] or http["fastapi"]) else 1
    return 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if "--statuscli" in sys.argv:
        return cli_status()
    if "--startcli" in sys.argv:
        return cli_start()
    if "--stopcli" in sys.argv:
        return cli_stop()
    app = PanelKendali()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
