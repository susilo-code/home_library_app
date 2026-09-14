# Product Requirement Document (PRD): Home Library App

## 1. Ringkasan Eksekutif & Tujuan Project
**Home Library App** adalah aplikasi manajemen perpustakaan rumah berbasis kolaboratif yang memungkinkan multiple pengguna untuk mencatat, mengelola, dan memantau koleksi buku bersama. Aplikasi ini dirancang dengan estetika visual elegan (nuansa Ungu Tua & Putih Redup / Slate), hemat di mata (eye-friendly), serta mendukung pengalihan Dark Mode / Light Mode secara mulus.

---

## 2. Target Pengguna & Karakteristik
- **Multi-User Collaborative**: Setiap pengguna terdaftar dapat menambahkan dan mengedit data buku.
- **Transparansi Koleksi**: Seluruh pengguna dapat melihat hasil perekaman dari pengguna lain, memantau kontributor teraktif, serta mencari koleksi buku secara terpusat.

---

## 3. Fitur Utama & Spesifikasi Teknis

### A. Dashboard Interaktif & Stat Analysis
1. **Ringkasan KPI Card**:
   - Total Jumlah Buku dalam Perpustakaan.
   - Total Genre / Kategori Terdaftar.
   - Total Kontributor Teraktif (Pengguna).
2. **Visualisasi Grafik (Chart.js)**:
   - **Distribusi Buku per Genre** (Doughnut / Pie Chart).
   - **Produktivitas Perekaman per User** (Bar Chart membandingkan jumlah buku yang di-input tiap user).
3. **Widget Jam Digital Realtime**:
   - Tampilan jam, menit, detik & tanggal terkini dengan animasi halus di header / dashboard.

### B. Manajemen Data Buku (Form & DataTable)
1. **Form Perekaman Buku (CBV Create/Update)**:
   - Judul Buku, Penulis, ISBN, Genre, Tahun Terbit, Penerbit, Jumlah Halaman, Status Baca (Belum Dibaca, Sedang Dibaca, Selesai Dibaca), Deskripsi, & Cover URL/Image.
2. **DataTable & Filter Advanced**:
   - Pencarian Instan (Live Search judul, penulis, ISBN).
   - Filter Multi-kriteria (Filter per Genre, Filter per User perekam, Filter per Status Baca).
   - Pagination & Sorting (Judul, Tanggal Input, Tahun Terbit).

### C. Profil Pengguna & Pengaturan (Settings)
1. **Profile Management**:
   - Tampilan profil user, bio, serta Foto Profil (Avatar Upload).
   - Statistik individu (jumlah buku yang dikontribusikan).
2. **Settings**:
   - Pengaturan Preferensi Tampilan (Dark/Light mode).
   - Pengaturan Sistem & Informasi Akun.

### D. UI/UX & Tema Visual
- **Palet Warna**:
  - Primary / Accent: Deep Purple (`#3B1E54`, `#2E1A47`, `#522B5B`).
  - Background Light Mode: Soft Off-White (`#F7F5FA`, `#EFEBF4`).
  - Background Dark Mode: Deep Midnight Purple (`#120B1C`, `#1A1126`).
  - Text: High Contrast Slate & Muted Lilac (`#DFD7BF`, `#8B7E74`, `#E0E0E0`).
- **Dark & Light Mode Toggle**: Pengalihan tema yang tersimpan di `localStorage` browser.
- **Responsif**: Layout fleksibel untuk desktop, tablet, dan mobile.

---

## 4. Arsitektur Software & Tech Stack

| Komponen | Teknologi | Keterangan |
| :--- | :--- | :--- |
| **Backend Framework** | Django 5.x | Class-Based Views (CBV) untuk routing & render template |
| **API Backend Service** | FastAPI + Uvicorn | High-performance endpoints untuk stats dashboard & datatable JSON |
| **Frontend Rendering** | Django Templates + HTMX | Modular template inheritence & dynamic updating |
| **Styling** | Tailwind CSS (Local Bundle) | Custom Purple Slate Palette & Dark Mode Config |
| **Database** | SQLite / MySQL | Persistensi data koleksi buku & profil pengguna |
| **Python Environment** | `uv venv` Python 3.11 | Isolasi dependensi & manajemen paket cepat |

---

## 5. Struktur Data (Data Models)

1. **User / UserProfile**:
   - `user`: OneToOneField(User)
   - `avatar`: ImageField / URL
   - `bio`: TextField
   - `created_at`: DateTimeField

2. **Genre**:
   - `name`: CharField (Unique)
   - `color_code`: CharField (Hex Code untuk Badge UI)
   - `description`: TextField

3. **Book**:
   - `title`: CharField
   - `author`: CharField
   - `isbn`: CharField
   - `genre`: ForeignKey(Genre)
   - `recorded_by`: ForeignKey(User)
   - `status`: CharField (UNREAD, READING, COMPLETED)
   - `rating`: IntegerField (1-5 star)
   - `publisher`: CharField
   - `publication_year`: IntegerField
   - `pages`: IntegerField
   - `summary`: TextField
   - `cover_url`: URLField / CharField
   - `created_at`: DateTimeField
   - `updated_at`: DateTimeField

---

## 6. Rencana Eksekusi & Tahapan Implementasi
1. **Tahap 1**: Setup Environment `uv venv` & Instalasi Package (Django, FastAPI, Uvicorn, Pillow, Jinja2).
2. **Tahap 2**: Inisialisasi Django Project & App Structure (`home_library` & `library_app`).
3. **Tahap 3**: Implementasi Model Database & Migrasi.
4. **Tahap 4**: Pembuatan Seeder Data Dummy (User, Genre, Buku, Activity Logs).
5. **Tahap 5**: Implementasi Django Class-Based Views (CBV) & FastAPI Service.
6. **Tahap 6**: Desain UI/UX Django Templates dengan Tailwind CSS Local, Jam Digital JS, Chart.js, & Switcher Dark/Light Mode.
7. **Tahap 7**: Pengujian (Unit Tests & Functional Endpoint Verification) & Run Application.

---

## 7. Catatan Revisi

### Revisi 1 (v1.1.0)
- Halaman login didesain ulang: nuansa ungu tua, judul **Hirunaza's Library Information System**, ilustrasi perpustakaan lokal (`static/img/library-hero.svg`).
- Form perekaman: section detail/sampul/sinopsis **terlipat** (default tertutup), tombol simpan sticky.
- **Autocomplete judul** dengan pencocokan fuzzy (`/api/titles/`) + deteksi duplikat **tidak peka huruf besar/kecil & spasi ganda** (field normalisasi `title_normalized` / `author_normalized`).
- Master data **Lokasi Rak Buku** dinamis (CRUD dari Pengaturan).

### Revisi 2 (v1.2.0)
- **Jenis Buku dikunci** menjadi pilihan tetap: **Fiksi** dan **Non-Fiksi** (`Book.BookCategory`); model `BookType` (master data) dihapus.
- **Genre / Kategori menjadi DINAMIS**: tambah/ubah/hapus dari halaman **Pengaturan**, lengkap dengan slug otomatis, warna label, ikon, dan status aktif. Hanya genre aktif yang muncul di form perekaman.
- Field baru **Tahun Beli** (`purchase_year`) dengan validasi: 1900 s.d. tahun berjalan, dan tidak boleh lebih awal dari tahun terbit.
- Tombol **Simpan** kini selalu terlihat tanpa scroll: bar aksi melayang (`fixed bottom-0`) + tombol di header form.
- Halaman login: kalimat sambutan diganti kutipan **Imam Syafi'i Rahimahullah** tentang menahan lelahnya belajar.
- Migrasi: `0004` (jenis buku tetap + tahun beli + genre dinamis, mapping data dari genre) dan `0005` (backfill `Genre.created_at`).

### Revisi 3 (v1.3.0)
- **Manajemen Pengguna di dalam aplikasi** (`/pengguna/`, khusus staff/superuser): daftar akun
  (peran, status, jumlah buku), tambah pengguna, ubah data, atur ulang kata sandi,
  aktif/nonaktifkan, dan hapus akun.
- Command CLI **`manage.py create_user`** (`--list`, `--set-password`, `--staff`,
  `--superuser`, `--activate`, `--deactivate`).
- Pengaman: akun sendiri tidak bisa dinonaktifkan/dihapus, superuser terakhir tidak bisa
  dihapus, kata sandi divalidasi & ter-hash, aksi tercatat di ActivityLog
  (`TAMBAH_USER` / `UPDATE_USER` / `HAPUS_USER`).
- Infrastruktur rilis: `.env` + `.env.example`, `.gitignore`, `.gitattributes`,
  `requirements.txt` ter-pin, `MANUAL.md`, `setup.bat`, `start.bat`, `stop.bat`,
  `push_github.bat`, serta skrip verifikasi di `scripts/dev/`.
- Perbaikan: endpoint FastAPI diubah ke fungsi sinkron (Django ORM tidak boleh di
  konteks async), penghapusan genre/rak kini tercatat, dan seeder tidak lagi
  menimpa klasifikasi jenis buku secara manual.

### Revisi 4 (v1.4.0)
Delapan permintaan perbaikan sekaligus:

1. **Judul aplikasi dinamis** — model baru `SiteConfig` (singleton) + context processor
   `identitas_aplikasi`; diedit dari Pengaturan → **Identitas Aplikasi** (khusus admin).
   Dipakai di judul tab browser, navbar, footer, halaman login, dan label cetak.
   Field: `app_name`, `app_short_name`, `tagline`, `label_owner`.
2. **Kapasitas rak dihapus** — field `Shelf.capacity` + property `fill_percent` dihapus
   dari model, form, admin, halaman Pengaturan, seeder, dan API.
3. **Detail buku menjadi MODAL** — section detail (ISBN, tahun terbit, tahun beli,
   penerbit, halaman, rating) tidak lagi terlipat di halaman, melainkan tersembunyi dan
   dibuka lewat tombol **“Isi Detail Buku”**; otomatis terbuka bila ada error validasi.
4. **Tambah genre & rak langsung dari form buku** — modal + endpoint JSON
   `api/genre/tambah/` dan `api/rak/tambah/`; data baru langsung tersimpan dan
   terpilih otomatis di form, tanpa pindah ke halaman Pengaturan.
5. **Kata sandi dibebaskan** — `AUTH_PASSWORD_VALIDATORS = []`; validasi panjang/kerumitan
   dihapus dari form tambah/ubah pengguna, halaman ubah sandi, dan command `create_user`.
   Yang tersisa hanya pemeriksaan sandi == ulangannya dan tidak boleh kosong.
6. **Dashboard tanpa data per user** — grafik “Produktivitas Perekaman per User”
   beserta datanya (`user_labels` / `user_counts`) dihapus.
7. **Donut genre menampilkan persentase** (angka persentase digambar di dalam potongan
   + pada keterangan) dan grafik kontributor diganti **Top 5 Genre** (batang mendatar,
   jumlah buku ditulis di ujung batang).
8. **Cetak label 2 × 3 cm** — halaman `/label/` (pilih buku dengan filter) dan
   `/label/cetak/` (lembar siap cetak). Ukuran label tetap: **3 × 2 cm (mendatar,
   default)** atau **2 × 3 cm (tegak)**; isi label = lokasi rak (menonjol), judul,
   penulis, jenis buku, dan nama pemilik (opsional). Ada opsi “lompati N label”
   untuk stiker yang sebagian sudah terpakai, serta `@page A4 margin 8 mm` saat dicetak.
   Menu **Cetak Label** ditambahkan di navbar (desktop & mobile).

### Revisi 6 (v1.6.0)

1. **Menu “Tentang Aplikasi” + modal** — item keempat di top bar (ikon *info* dalam kotak
   ungu, konsisten dengan tiga menu lain) dan pada menu mobile. Diklik → **modal** berisi:
   identitas **pengembang**, pernyataan **open source**, **tech stack**, **fungsi aplikasi**,
   tautan **repositori GitHub**, dan **syarat pemakaian (“pemakaian harus atas izin pengembang”**).
   Dua data baru ditambahkan pada `SiteConfig` — `developer_name` dan `repo_url` (migrasi
   `0007`) — sehingga modal mengikuti identitas aplikasi dan dapat disunting dari
   **Pengaturan → Identitas Aplikasi**. Bonus: *deep-link* `?tentang=1` langsung membuka modal.
2. **Kredit di halaman login dihapus** — frasa “This app is developed by susilo” tidak lagi
   tampil di `/login/`. Footer `Developed by susilo` tetap ada di halaman dalam aplikasi.
3. **Panel Kendali satu pintu (`launcher.py` → `HirunazaLibraryLauncher.exe`)** — aplikasi
   jendela **tkinter** untuk pengguna awam: tombol **Siapkan / Jalankan / Hentikan / Buka
   Aplikasi / Buat Akun Admin**, status langsung (folder, `.venv`, `.env`, port, Node.js), dan
   catatan aktivitas. Logika start/stop dipakai bersama GUI dan mode CLI
   (`--selftest`, `--statuscli`, `--startcli`, `--stopcli`). Log layanan terpisah:
   `logs/django.log` dan `logs/fastapi.log`. Skrip pembangun: `build_launcher.bat`.
4. **Kesiapan PC tanpa Node.js/JS/npm** — `setup.bat` sudah melewati (bukan gagal) langkah
   build Tailwind bila `npm` tidak ada; ditambah **audit cakupan CSS** baru
   (`scripts/dev/cek_css_lokal.py`, dijalankan otomatis di verifikasi v6) yang membuktikan
   **545/545 kelas** template tersedia di `static/css/output.css`. Ditemukan & diperbaiki:
   palet `royal`/`plum`/`ink` sebelumnya hanya ada di *config* Tailwind CDN sehingga
   **21 kelas** (termasuk di halaman login) tidak tergenerate ke CSS lokal — kini palet
   tersebut sudah resmi ada di `tailwind.config.js`.

### Revisi 5 (v1.4.1)

1. **Top bar dibersihkan** — menu **Pengguna**, tombol **+ Tambah Buku**, dan **jam digital**
   dihapus dari navbar (desktop maupun menu mobile) agar tidak berdesakan.
   Top bar kini hanya: **Dashboard · Katalog Buku · Cetak Label** + pemilih tema + menu user.
   Pengguna tetap bisa dikelola dari **menu klik user → Kelola Pengguna**, dan menambah buku
   dari tombol **Tambah Buku Baru** di Dashboard & Katalog.
2. **Kredit pengembang** — footer berubah menjadi `© {tahun} {judul aplikasi}. Developed by susilo.`
   (menggantikan “Dibangun dengan Django + Tailwind CSS”); halaman login mencantumkan
   **“This app is developed by susilo”**.
3. **Halaman login** — bulet **“Statistik Kontribusi”** diganti **“Statistik Buku”**.
4. **Kartu dashboard** — **“Kontributor Aktif”** menjadi **“User Aktif”**, dan kartu
   **“Buku Anda”** diganti **“Belum Selesai Dibaca”** (jumlah buku yang statusnya belum
   *Selesai Dibaca*, dihitung dari seluruh koleksi).
