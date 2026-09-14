# MANUAL PEMASANGAN DI PC BARU
## Hirunaza's Library Information System

Panduan ini ditulis agar aplikasi bisa jalan di PC lain **tanpa masalah dependency maupun
kompatibilitas**. Ikuti urutannya; setiap langkah disertai cara verifikasinya.

Versi aplikasi: **1.2.0** · Django 5.2.17 · Python 3.11 · SQLite (default)

---

## 1. Prasyarat

| Kebutuhan | Versi disarankan | Wajib? | Catatan |
| :--- | :--- | :--- | :--- |
| **Python** | **3.11** atau 3.12 | ⬜ **Tidak wajib** | `setup.bat` bisa menyiapkannya sendiri: bila `uv` ada (atau berhasil dipasang otomatis), Python 3.11 **diunduh otomatis** — lihat catatan di bawah |
| **Koneksi internet** | — | ✅ Wajib saat setup | Untuk mengunduh Python/dependency. Setelah terpasang, aplikasi jalan offline |
| **Git** | 2.30+ | ✅ Wajib (untuk clone) | https://git-scm.com/downloads — alternatif: unduh ZIP repo dari GitHub |
| **Google Chrome** | versi terbaru | Disarankan | Dibuka otomatis oleh `start.bat`; browser lain tetap jalan |
| **Node.js** | 18 / 20 / 22 | ⬜ Opsional | Hanya untuk *rebuild* Tailwind CSS. Tanpa Node pun tampilan tetap benar |
| **uv** | terbaru | ⬜ Opsional | Mempercepat pembuatan venv & bisa mengunduh Python sendiri |
| **MySQL/PostgreSQL** | — | ⬜ Opsional | Hanya jika tidak memakai SQLite (lihat bagian 8) |

> **Soal Python: apakah PC baru harus sudah punya Python?**
> Tidak harus. `setup.bat` mencoba berurutan:
> 1. **Python 3.11+ yang sudah ada** di PC → langsung dipakai;
> 2. **uv** (bila ada) → `uv venv --python 3.11` mengunduh Python 3.11 sendiri (±21 MB, tanpa hak admin);
> 3. **Pasang uv otomatis** → lewat `winget`, lalu skrip resmi `astral.sh` (PowerShell), lalu unduh arsip dari GitHub Releases.
>
> Bila ketiganya gagal (mis. tanpa internet), barulah script meminta Anda memasang Python manual dari
> https://www.python.org/downloads/ — **centang “Add python.exe to PATH”** saat instalasi.

---

## 2. Cara Tercepat (otomatis)

```bat
:: 1) Clone repository (ganti URL sesuai repo Anda)
git clone https://github.com/<USERNAME>/<NAMA_REPO>.git
cd <NAMA_REPO>

:: 2) Jalankan setup sekali saja
setup.bat

:: 3) Jalankan aplikasi (Django + FastAPI + Chrome otomatis terbuka)
start.bat
```

`setup.bat` mengerjakan: cek Python → buat `.venv` → install dependency → buat `.env`
dengan SECRET_KEY acak → migrasi database → (opsional) build Tailwind → (opsional) isi data contoh
dan akun admin.

Bila ingin mematikan semua service: **`stop.bat`**.

---

## 3. Cara Manual (bila ingin kendali penuh)

> Cara ini mengasumsikan Python 3.11+ sudah terpasang. Bila belum punya Python sama sekali,
> cara termudah: pasang `uv` (https://docs.astral.sh/uv/) lalu pakai baris `uv venv` di bawah —
> uv akan mengunduh Python 3.11 sendiri tanpa perlu instalasi manual.

### Windows (Command Prompt / PowerShell)

```bat
cd /d "D:\path\ke\home_library_app"

:: 3.1 Virtual environment (pilih salah satu)
python -m venv .venv
:: atau, bila memakai uv (Python diunduh otomatis bila belum ada):
:: uv venv --python 3.11 .venv

.venv\Scripts\activate

:: 3.2 Dependency
python -m pip install --upgrade pip
pip install -r requirements.txt
:: atau: uv pip install --python .venv\Scripts\python.exe -r requirements.txt

:: 3.3 File .env (SECRET_KEY acak otomatis)
python scripts\init_env.py

:: 3.4 Database
python manage.py migrate

:: 3.5 Akun admin & data contoh (opsional)
python manage.py createsuperuser
python manage.py seed_data --users 5 --books-per-user 8
```

### WSL2 Ubuntu / Linux / macOS

```bash
cd ~/path/ke/home_library_app

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python scripts/init_env.py
python manage.py migrate
python manage.py createsuperuser      # opsional
python manage.py seed_data            # opsional

# Jalankan dua service
python manage.py runserver 127.0.0.1:8000
python -m uvicorn api.main:app --host 127.0.0.1 --port 8001    # terminal kedua
```

> File `.bat` hanya untuk Windows. Di Linux/macOS jalankan perintah pada dua terminal
> terpisah, atau buat skrip shell sederhana.

### Verifikasi instalasi

```bat
python -c "import django, fastapi, dotenv, PIL; print('dependency OK')"
python manage.py check
```

Keluaran yang benar: `System check identified no issues (0 silenced).`

---

## 4. Penjelasan File `.env`

`.env` **tidak ikut ter-commit** (berisi rahasia). Yang ikut ter-commit adalah
`.env.example` sebagai cetakan. Salin manual:

```bat
copy .env.example .env
:: lalu isi SECRET_KEY dengan hasil:
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

| Variabel | Default | Keterangan |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(wajib diisi)* | Kunci rahasia Django. **Beda tiap PC itu normal.** Jangan dibagikan |
| `DEBUG` | `True` | `True` untuk lokal. `False` saat dipublikasikan |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost,testserver` | Dipisah koma, tanpa spasi |
| `TIME_ZONE` | `Asia/Jakarta` | Zona waktu tampilan |
| `DB_ENGINE` | `sqlite` | `sqlite` / `mysql` / `postgres` |
| `DB_NAME` | `db.sqlite3` | SQLite: nama file · MySQL/Postgres: nama database |
| `DB_USER`, `DB_PASSWORD` | *(kosong)* | Diabaikan untuk SQLite |
| `DB_HOST`, `DB_PORT` | `127.0.0.1`, `3307` | Laragon biasanya `3307`; MySQL standar `3306`; PostgreSQL `5432` |
| `DJANGO_PORT` | `8000` | Dibaca oleh `start.bat` |
| `FASTAPI_HOST`, `FASTAPI_PORT` | `127.0.0.1`, `8001` | Alamat service API |

Mengubah port cukup dari `.env` — `start.bat` otomatis mengikuti.

---

## 5. Menjalankan Aplikasi

### Cara cepat

```bat
start.bat              :: Django + FastAPI + Chrome terbuka otomatis
start.bat nobrowser    :: tanpa membuka browser
stop.bat               :: matikan semua service
```

### Cara manual (dua jendela)

```bat
:: Jendela 1 — web utama
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

:: Jendela 2 — REST API
.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

| Alamat | Isi |
| :--- | :--- |
| http://127.0.0.1:8000 | Aplikasi web (login, dashboard, katalog) |
| http://127.0.0.1:8000/admin/ | Panel admin Django |
| http://127.0.0.1:8001/docs | Dokumentasi interaktif FastAPI (Swagger) |
| http://127.0.0.1:8001/api/health | Cek kesiapan API + koneksi database |

**Login contoh** (setelah `seed_data`): `user1` / `password123`

> Username bisa diganti dari panel admin, jadi pastikan akun yang benar dengan:
> `.venv\Scripts\python.exe scripts\list_accounts.py`
> (perintah `start.bat` juga menampilkan daftar akun ini secara otomatis)
> Lupa sandi? `.venv\Scripts\python.exe manage.py changepassword <username>`

---

## 6. Struktur Folder

```
home_library_app/
├── .env                  # rahasia lokal (TIDAK di-commit)
├── .env.example          # cetakan konfigurasi (di-commit)
├── .gitignore
├── MANUAL.md             # dokumen ini
├── PRD.md                # kebutuhan produk
├── requirements.txt      # dependency Python (versi di-pin)
├── package.json          # dependency Node untuk Tailwind (opsional)
├── tailwind.config.js
├── setup.bat / start.bat / stop.bat
├── manage.py
├── db.sqlite3            # database lokal (TIDAK di-commit)
├── config/               # pengaturan project (settings, urls, wsgi)
├── library/              # aplikasi utama: models, views, forms, admin
│   ├── migrations/       # riwayat skema database (di-commit)
│   └── management/commands/seed_data.py
├── api/main.py           # service FastAPI
├── scripts/              # init_env.py, env_export.py
│   └── dev/              # skrip pengujian & pratinjau (verify_*.py, test_start_bat.py)
├── templates/            # halaman HTML
│   ├── books/ accounts/ settings/ registration/
│   └── labels/           # pilih & cetak label buku (2 × 3 cm)
├── static/
│   ├── css/output.css    # hasil build Tailwind (di-commit agar tanpa Node tetap rapi)
│   ├── img/library-hero.svg
│   └── js/
└── media/                # upload pengguna (TIDAK di-commit)
```

---

## 7. Data & Akun

```bat
:: isi data contoh (5 user, 16 buku per user, 7 rak, 10 genre)
.venv\Scripts\python.exe manage.py seed_data --users 5 --books-per-user 16

:: ulangi dari nol (hapus buku & aktivitas lama, user tetap)
.venv\Scripts\python.exe manage.py seed_data --clear --users 5 --books-per-user 16

:: pulihkan data demo bila jenis buku/genre tampak kacau (mis. setelah genre dihapus)
.venv\Scripts\python.exe manage.py repair_demo_data --dry-run   :: lihat rencana
.venv\Scripts\python.exe manage.py repair_demo_data             :: terapkan

:: buat akun admin/superuser
.venv\Scripts\python.exe manage.py createsuperuser

:: ganti kata sandi user tertentu lewat shell
.venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth.models import User; u=User.objects.get(username='user1'); u.set_password('rahasia123'); u.save()"
```

Akun: **multi-user** (semua pengguna melihat koleksi bersama) ·
Jenis buku bersifat tetap: **Fiksi / Non-Fiksi** ·
Genre & Lokasi Rak dikelola dari menu **Pengaturan** (dinamis, tersimpan di database).

> **Catatan penting:** menghapus Genre atau Rak **tidak** menghapus bukunya — kolom terkait
> menjadi kosong (`SET NULL`), dan setiap penghapusan **tercatat di ActivityLog**
> (aksi `HAPUS_GENRE` / `HAPUS_RAK`) sehingga bisa ditelusuri.

> **Kata sandi dibebaskan** (v1.4.0): tidak ada aturan panjang minimum maupun kerumitan
> (`AUTH_PASSWORD_VALIDATORS = []`). Yang diperiksa hanya: sandi tidak boleh kosong dan
> sandi harus sama dengan ulangannya. Sandi tetap disimpan dalam bentuk ter-hash.

---

## 7c. Cetak Label Buku (2 × 3 cm)

Menu **Cetak Label** di navbar (atau buka `/label/`).

1. Pilih buku: gunakan pencarian/filter (genre, rak, atau “belum punya rak”).
2. Centang buku yang ingin diberi label — atau klik **Cetak semua hasil filter**.
3. Tentukan **orientasi label** dan (opsional) **lompati N label** bila lembar stiker
   Anda sebagian sudah terpakai.
4. Klik **Cetak label terpilih** → halaman lembar label terbuka → klik
   **Cetak / Simpan PDF** (Ctrl+P).

| Pengaturan | Nilai |
| :--- | :--- |
| Ukuran label | **3 × 2 cm** (mendatar, default) atau **2 × 3 cm** (tegak) |
| Isi label | Lokasi rak (menonjol) + kode rak, judul, penulis, jenis buku, nama pemilik |
| Kertas | A4, margin cetak 8 mm (`@page`) |
| Baris atas label | Kode rak (atau nama rak bila kode kosong); buku **tanpa rak** diberi label merah “TANPA RAK” |

> Nama pemilik pada label diatur di **Pengaturan → Identitas Aplikasi → Nama Pemilik
> (pada label cetak)**. Bila dikosongkan, label menampilkan nomor ID buku.

---

## 7b. Menambah / Mengelola Pengguna

Tersedia **tiga cara**. Aplikasi ini multi-user: semua anggota melihat koleksi yang sama.

### Cara 1 — Dari dalam aplikasi (paling mudah, khusus admin/staff)

1. Login sebagai akun yang berstatus **superuser/staff**.
2. Buka menu **Pengguna** di navbar (atau *Pengaturan → Kelola Pengguna*).
3. Isi form **Tambah Pengguna Baru** → **Buat Akun Pengguna**.
4. Sampaikan username & kata sandi ke orang tersebut; minta ia menggantinya di
   *Pengaturan → Ubah Kata Sandi*.

Di halaman yang sama admin juga bisa: mengubah data, **mengatur ulang kata sandi**,
**menonaktifkan** akun (tanpa menghapus), atau menghapus akun.

> Menu **Pengguna** hanya muncul untuk akun staff/superuser. Pengguna biasa yang mencoba
> membuka `/pengguna/` akan dialihkan ke dashboard dengan pesan "khusus administrator".

### Cara 2 — Lewat terminal (butuh satu akun admin dahulu)

```bat
:: lihat siapa saja yang punya akun
.venv\Scripts\python.exe manage.py create_user --list

:: tambah anggota biasa (kata sandi ditanyakan bila tidak ditulis)
.venv\Scripts\python.exe manage.py create_user --username budi --password Rahasia123 --email budi@mail.com

:: tambah sekaligus sebagai admin
.venv\Scripts\python.exe manage.py create_user --username ayah --password Rahasia123 --staff

:: ubah kata sandi / nonaktifkan / aktifkan akun yang sudah ada
.venv\Scripts\python.exe manage.py create_user --username budi --set-password
.venv\Scripts\python.exe manage.py create_user --username budi --deactivate
.venv\Scripts\python.exe manage.py create_user --username budi --activate

:: jadikan akun yang sudah ada sebagai superuser (mis. akun Anda sendiri)
.venv\Scripts\python.exe manage.py create_user --username hirunaza --superuser
```

### Cara 3 — Panel admin Django

Login ke `http://127.0.0.1:8000/admin/` → menu **Users → Add user**.

> **Penting untuk pemasangan baru:** hasil `seed_data` hanya membuat akun *anggota*
> (`user1`…`user5`). Supaya bisa mengelola pengguna, naikkan salah satu akun menjadi admin:
> ```bat
> .venv\Scripts\python.exe manage.py create_user --username user1 --superuser
> ```

### Perilaku & pengaman

| Aksi | Perilaku |
| :--- | :--- |
| Hapus pengguna | Buku yang ia catat **ikut terhapus** (relasi CASCADE) — konfirmasi menampilkan jumlahnya. Untuk sekadar memutus akses, pakai **nonaktifkan** |
| Nonaktifkan akun | Tidak bisa login, tetapi seluruh datanya tetap ada |
| Akun sendiri | Tidak bisa dinonaktifkan/dihapus, dan akses staff sendiri tidak bisa dicabut dari UI |
| Superuser terakhir | Tidak boleh dihapus (mencegah terkunci dari sistem) |
| Kata sandi | Divalidasi (min. 8 karakter, tidak terlalu umum), disimpan ter-hash, dan tidak ditampilkan di log |
| Jejak audit | Aksi `TAMBAH_USER`, `UPDATE_USER`, `HAPUS_USER` tercatat di ActivityLog |

### Skrip pengujian bawaan (opsional, untuk memastikan aplikasi sehat)

```bat
.venv\Scripts\python.exe scripts\dev\verify_features_v2.py    :: 78 pemeriksaan fitur & halaman
.venv\Scripts\python.exe scripts\dev\verify_perbaikan_v3.py   :: 67 pemeriksaan batch v1.4.0 (8 perbaikan)
.venv\Scripts\python.exe scripts\dev\verify_user_management.py :: 30 pemeriksaan kelola pengguna
.venv\Scripts\python.exe scripts\dev\test_start_bat.py        :: uji start.bat + kedua service
.venv\Scripts\python.exe scripts\dev\verify_fresh_clone.py    :: uji skenario "clone di PC baru" dari nol
.venv\Scripts\python.exe scripts\dev\render_preview.py        :: render halaman ke folder preview/
```

Semua skrip itu sudah punya *bootstrap* sendiri, jadi bisa dijalankan dari direktori mana pun.
`verify_fresh_clone.py` adalah bukti bahwa panduan ini benar-benar bekerja: ia meng-clone repo
ke folder sementara, membuat venv baru, memasang dependency, menjalankan migrasi & seeder,
lalu memastikan halaman login merespons **HTTP 200**.

---

## 8. Mengganti Database

### A. SQLite (default — paling aman untuk PC baru)
Tidak ada yang perlu disiapkan. Database berupa file `db.sqlite3` di root project.
Hapus file itu lalu `python manage.py migrate` untuk memulai dari nol.

### B. MySQL / MariaDB (Laragon, XAMPP)
1. Buka Laragon → **Start All** → pastikan MySQL menyala (Laragon default port **3307**).
2. Buat database kosong, misal `hirunaza_library` (via HeidiSQL/phpMyAdmin).
3. Pasang driver **PyMySQL** (pure Python, tidak perlu compiler C):
   ```bat
   .venv\Scripts\python.exe -m pip install PyMySQL
   ```
   `config/__init__.py` sudah otomatis memakai PyMySQL sebagai pengganti `MySQLdb`.
4. Edit `.env`:
   ```ini
   DB_ENGINE=mysql
   DB_NAME=hirunaza_library
   DB_USER=root
   DB_PASSWORD=
   DB_HOST=127.0.0.1
   DB_PORT=3307
   ```
5. Jalankan: `python manage.py migrate`

### C. PostgreSQL
1. Buat database, lalu pasang driver: `pip install "psycopg[binary]"`
2. `.env`: `DB_ENGINE=postgres`, `DB_PORT=5432`, isi user/password.

> Setelah pindah database, data lama **tidak** ikut pindah otomatis.
> Jalankan `seed_data` atau impor data sendiri.

---

## 9. Tailwind CSS

`static/css/output.css` **ikut di-commit**, sehingga aplikasi tetap tampil rapi
walau Node.js belum terpasang di PC baru.

Rebuild (hanya bila mengubah tampilan):

```bat
npm install
npm run build          :: sekali build
npm run dev            :: mode pantau (auto-build saat file berubah)
```

Walau `output.css` tidak di-build, halaman tetap ter-render karena `base.html`
juga memuat Tailwind lewat CDN.

---

## 10. Push ke GitHub & Clone di PC Lain

### Pertama kali (di PC ini)

```bat
cd /d "D:\IT Projects\home_library_app"
git init
git add .
git commit -m "feat: Hirunaza's Library Information System v1.2.0"
git branch -M main

:: buat repository KOSONG dulu di https://github.com/new (jangan centang README)
git remote add origin https://github.com/<USERNAME>/<NAMA_REPO>.git
git push -u origin main
```

Bila diminta login: gunakan **Personal Access Token** (Settings → Developer settings →
Personal access tokens) sebagai kata sandi, atau pasang GitHub CLI:

```bat
winget install --id GitHub.cli
gh auth login
gh repo create <NAMA_REPO> --private --source . --push
```

### Di PC baru

```bat
git clone https://github.com/<USERNAME>/<NAMA_REPO>.git
cd <NAMA_REPO>
setup.bat
start.bat
```

### Cek berkas yang TIDAK boleh ter-commit

```bat
git status --ignored
```

Pastikan `.env`, `.venv/`, `db.sqlite3`, `media/`, `node_modules/` berstatus **ignored**.

---

## 11. Pemecahan Masalah (Troubleshooting)

| Gejala | Penyebab | Solusi |
| :--- | :--- | :--- |
| `'python' is not recognized` | Python tidak masuk PATH | Instal ulang Python & centang **Add to PATH**, atau pakai `py -3.11` |
| `No module named pip` di dalam `.venv` | Venv dibuat oleh `uv` (tanpa pip) | `\.venv\Scripts\python.exe -m ensurepip --upgrade` atau install pakai `uv pip install --python .venv\Scripts\python.exe -r requirements.txt` |
| `ModuleNotFoundError: No module named 'dotenv'` | Dependency belum lengkap | `.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `pip install mysqlclient` gagal (`fatal error C1083`) | Butuh compiler C | Pakai **PyMySQL** (bagian 8B) — tidak perlu compiler |
| `Port 8000 is already in use` | Server lama masih hidup | `stop.bat` lalu `start.bat`. Kalau perlu: `netstat -ano \| findstr :8000` → `taskkill /F /PID <PID>` |
| Halaman tampil kode lama walau file sudah diubah | Proses server lama memegang port | `stop.bat`, cek `netstat -ano \| findstr :8000` harus kosong, lalu `start.bat` |
| `TemplateSyntaxError: Unclosed tag on line N: 'block'` | `{% block %}` tidak ditutup `{% endblock %}` | Pastikan setiap blok di template punya penutup; jumlah `{% block %}` = jumlah `{% endblock %}` |
| CSS/tampilan polos | `output.css` belum ada | `npm install && npm run build`, atau pastikan CDN Tailwind tidak diblokir |
| `Invalid HTTP_HOST header` | Host tidak diizinkan | Tambahkan host ke `ALLOWED_HOSTS` di `.env` |
| `database is locked` (SQLite) | Ada proses lain memakai DB | Tutup server lain / aplikasi DB viewer, lalu ulangi |
| `no such table: library_book` | Belum migrasi | `python manage.py migrate` |
| Login gagal terus | Belum ada user | `python manage.py seed_data` atau `createsuperuser` |
| Upload gambar gagal (Windows) | Folder `media/` belum ada | `mkdir media\avatars media\book_covers` |
| WSL: halaman tidak terbuka di Chrome Windows | Jaringan WSL terpisah | Gunakan `python manage.py runserver 0.0.0.0:8000` lalu buka `http://localhost:8000` dari Windows |
| `Pillow` gagal dipasang | Python terlalu baru/arsitektur salah | Pakai Python 3.11/3.12 versi 64-bit |
| FastAPI mengembalikan **HTTP 500** di semua endpoint | Endpoint `async def` memanggil Django ORM (sinkron) → `SynchronousOnlyOperation` | Sudah diperbaiki: semua endpoint memakai `def` (sinkron) sehingga dijalankan di threadpool. Jangan ubah ke `async def` tanpa `sync_to_async` |
| Genre/Rak hilang tanpa diketahui penyebabnya | Dihapus dari menu Pengaturan | Cek ActivityLog: aksi `HAPUS_GENRE` / `HAPUS_RAK` mencatat siapa & kapan. Pulihkan buku dengan `manage.py repair_demo_data` |

### Pemeriksaan cepat kondisi sistem

```bat
.venv\Scripts\python.exe -V
.venv\Scripts\python.exe -m pip list
.venv\Scripts\python.exe manage.py check
netstat -ano | findstr :8000
```

---

## 12. Checklist PC Baru

- [ ] Koneksi internet tersedia (dibutuhkan saat setup)
- [ ] `git --version` berjalan — atau unduh ZIP repo dari GitHub
- [ ] Repository berhasil di-`clone`
- [ ] `setup.bat` selesai tanpa error (Python **tidak** perlu dipasang dulu — script menyiapkannya)
- [ ] `.env` ada (berisi `SECRET_KEY` acak)
- [ ] `python manage.py migrate` sukses
- [ ] (opsional) `seed_data` & `createsuperuser` dijalankan
- [ ] `start.bat` membuka Django (8000), FastAPI (8001), dan Chrome
- [ ] Login berhasil (mis. `user1` / `password123`)
- [ ] Upload foto profil & sampul buku berhasil
- [ ] Menu Pengaturan dapat menambah Genre & Lokasi Rak
- [ ] `stop.bat` mematikan semua service

---

*Terakhir diperbarui: Revisi 2 (v1.2.0) — jenis buku tetap Fiksi/Non-Fiksi, genre & rak dinamis, tahun beli, tombol simpan melayang.*
