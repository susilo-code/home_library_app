# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Verifikasi fitur MANAJEMEN PENGGUNA:
  - command CLI create_user (tambah, list, ubah sandi, aktif/nonaktif, peran)
  - halaman /pengguna/ (khusus staff): tambah, ubah, nonaktifkan, hapus
  - kontrol akses: non-staff ditolak
  - pengaman: tidak bisa menonaktifkan/menghapus akun sendiri & superuser terakhir

Jalankan: .venv\\Scripts\\python.exe scripts\\dev\\verify_user_management.py
"""
import os
import subprocess
import sys
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402

PY = Path('.venv/Scripts/python.exe')
hasil = []
DIBERSIHKAN = []


def cek(nama, kondisi, detail=""):
    hasil.append(bool(kondisi))
    print(f"  {'[OK]  ' if kondisi else '[GAGAL]'} {nama}{(' — ' + detail) if detail else ''}")


def mg(*args, input_text=None):
    return subprocess.run([str(PY), 'manage.py', *args], capture_output=True, text=True,
                          input=input_text, cwd=str(Path.cwd()))


print("═" * 78)
print("1. COMMAND CLI: create_user")
print("═" * 78)

r = mg('create_user', '--list')
cek("--list menampilkan akun", r.returncode == 0 and 'USERNAME' in r.stdout,
    f"{len([l for l in r.stdout.splitlines() if l.strip()]) - 2} akun terdaftar")

# Tambah akun baru lewat CLI
r = mg('create_user', '--username', 'uji_cli_user', '--password', 'RahasiaUji123!',
       '--email', 'uji_cli@mail.com', '--first-name', 'Uji', '--last-name', 'CLI')
baru = User.objects.filter(username='uji_cli_user').first()
cek("CLI membuat akun baru", baru is not None, r.stdout.strip()[:90])
if baru:
    DIBERSIHKAN.append('uji_cli_user')
    cek("Kata sandi ter-hash (bukan plaintext)",
        baru.password.startswith('pbkdf2_') and 'RahasiaUji123!' not in baru.password)
    cek("Profil otomatis dibuat", hasattr(baru, 'profile'))
    c = Client()
    cek("Akun baru bisa login", c.login(username='uji_cli_user', password='RahasiaUji123!'))
    cek("Akun baru bukan staff", not baru.is_staff and not baru.is_superuser)

# Ubah sandi + peran lewat CLI
r = mg('create_user', '--username', 'uji_cli_user', '--set-password', '--password', 'SandiBaru456!')
baru.refresh_from_db()
c = Client()
cek("CLI ubah kata sandi berhasil",
    c.login(username='uji_cli_user', password='SandiBaru456!'), r.stdout.strip()[:70])

r = mg('create_user', '--username', 'uji_cli_user', '--staff')
baru.refresh_from_db()
cek("CLI memberi akses staff", baru.is_staff, r.stdout.strip()[:70])

r = mg('create_user', '--username', 'uji_cli_user', '--deactivate')
baru.refresh_from_db()
cek("CLI menonaktifkan akun", not baru.is_active)
c2 = Client()
cek("Akun nonaktif tidak bisa login", not c2.login(username='uji_cli_user', password='SandiBaru456!'))

# Kembalikan ke aktif + cabut staff untuk uji kontrol akses
mg('create_user', '--username', 'uji_cli_user', '--activate')

# Duplikat nama akun
r = mg('create_user', '--username', 'UJI_CLI_USER', '--password', 'apapun12345')
cek("Nama pengguna duplikat (beda kapitalisasi) ditolak",
    r.returncode != 0 and 'sudah ada' in (r.stdout + r.stderr))

# Sandi TIDAK lagi divalidasi kerumitannya (permintaan pemilik aplikasi:
# "password untuk user dibebaskan, tidak perlu validasi rumit") — jadi CLI
# justru HARUS menerima sandi pendek. Dulu suite ini menuntut sebaliknya.
r = mg('create_user', '--username', 'uji_lemah', '--password', '123')
cek("CLI menerima kata sandi bebas (tanpa aturan kerumitan)",
    r.returncode == 0 and User.objects.filter(username='uji_lemah').exists(),
    (r.stdout + r.stderr).strip().splitlines()[-1][:80] if (r.stdout + r.stderr).strip() else '')
if User.objects.filter(username='uji_lemah').exists():
    cek("Sandi pendek '123' benar-benar bisa dipakai login",
        Client().login(username='uji_lemah', password='123'))
    DIBERSIHKAN.append('uji_lemah')

print()
print("═" * 78)
print("2. KONTROL AKSES HALAMAN /pengguna/")
print("═" * 78)

# Pastikan ada penguji staff & non-staff
admin = User.objects.filter(is_superuser=True).order_by('pk').first()
if admin is None:
    admin = User.objects.create_superuser(username='uji_admin', password='AdminUji123!')
    DIBERSIHKAN.append('uji_admin')
nonstaff = User.objects.filter(is_staff=False, is_superuser=False).exclude(
    username='uji_cli_user').order_by('pk').first()
if nonstaff is None:
    nonstaff = User.objects.create_user(username='uji_nonstaff', password='NonStaff123!')
    DIBERSIHKAN.append('uji_nonstaff')

c_admin = Client()
c_non = Client()
c_admin.force_login(admin)
c_non.force_login(nonstaff)

r = c_admin.get('/pengguna/')
html = r.content.decode()
cek("Staff bisa buka /pengguna/", r.status_code == 200, f"HTTP {r.status_code}")
cek("Daftar akun tampil", 'Daftar Akun' in html)
cek("Form tambah pengguna tampil", 'Buat Akun Pengguna' in html)
cek("Ringkasan total akun tampil", 'Total Akun' in html)

r = c_non.get('/pengguna/')
cek("Non-staff dialihkan (bukan 200)", r.status_code in (302, 403), f"HTTP {r.status_code}")
if r.status_code == 302:
    cek("Dialihkan ke dashboard", r.url.endswith('/'), r.url)

print()
print("═" * 78)
print("3. TAMBAH / UBAH / HAPUS LEWAT UI")
print("═" * 78)

r = c_admin.post('/pengguna/', {
    'username': 'uji_ui_user', 'email': 'ui@mail.com', 'first_name': 'Uji', 'last_name': 'UI',
    'password1': 'SandiUi12345!', 'password2': 'SandiUi12345!',
    'is_active': 'on',
})
p = User.objects.filter(username='uji_ui_user').first()
cek("UI: pengguna baru tersimpan", p is not None, f"count user = {User.objects.count()}")
if p:
    DIBERSIHKAN.append('uji_ui_user')
    c = Client()
    cek("UI: akun baru bisa login", c.login(username='uji_ui_user', password='SandiUi12345!'))

# Validasi: kata sandi tidak sama
r = c_admin.post('/pengguna/', {
    'username': 'uji_beda_sandi', 'password1': 'SandiUi12345!', 'password2': 'BedaBanget999!',
    'is_active': 'on',
})
cek("UI: kata sandi tidak sama ditolak",
    not User.objects.filter(username='uji_beda_sandi').exists())

# Validasi: username duplikat
r = c_admin.post('/pengguna/', {
    'username': 'uji_ui_user', 'password1': 'SandiUi12345!', 'password2': 'SandiUi12345!',
    'is_active': 'on',
})
cek("UI: username duplikat ditolak",
    User.objects.filter(username__iexact='uji_ui_user').count() == 1)

# Ubah data + atur ulang sandi
if p:
    r = c_admin.post(f'/pengguna/{p.pk}/edit/', {
        'first_name': 'Diubah', 'last_name': 'UI', 'email': 'baru@mail.com',
        'password_baru': 'SandiGanti789!', 'is_active': 'on',
    })
    p.refresh_from_db()
    c = Client()
    cek("UI: data pengguna diperbarui", p.first_name == 'Diubah' and p.email == 'baru@mail.com')
    cek("UI: sandi baru berfungsi", c.login(username='uji_ui_user', password='SandiGanti789!'))

    # Nonaktifkan (tanpa centang is_active)
    r = c_admin.post(f'/pengguna/{p.pk}/edit/', {
        'first_name': 'Diubah', 'last_name': 'UI', 'email': 'baru@mail.com',
    })
    p.refresh_from_db()
    cek("UI: akun bisa dinonaktifkan", not p.is_active)
    c = Client()
    cek("Akun nonaktif ditolak login", not c.login(username='uji_ui_user', password='SandiGanti789!'))

print()
print("═" * 78)
print("4. PENGAMAN (tidak bisa merusak akses sendiri / superuser terakhir)")
print("═" * 78)

# Tidak bisa menonaktifkan akun sendiri
r = c_admin.post(f'/pengguna/{admin.pk}/edit/', {
    'first_name': admin.first_name, 'last_name': admin.last_name, 'email': admin.email,
})
admin.refresh_from_db()
cek("Tidak bisa menonaktifkan akun sendiri", admin.is_active)

# Tidak bisa hapus akun sendiri
r = c_admin.post(f'/pengguna/{admin.pk}/hapus/')
cek("Tidak bisa menghapus akun sendiri", User.objects.filter(pk=admin.pk).exists())

# Superuser terakhir tidak bisa dihapus
if User.objects.filter(is_superuser=True).count() == 1:
    r = c_admin.post(f'/pengguna/{admin.pk}/hapus/')
    cek("Superuser terakhir tidak terhapus", User.objects.filter(is_superuser=True).count() == 1)

# Non-staff tidak bisa POST ke endpoint pengguna
r = c_non.post('/pengguna/', {
    'username': 'uji_ilegal', 'password1': 'Ilegal12345!', 'password2': 'Ilegal12345!',
    'is_active': 'on',
})
cek("Non-staff tidak bisa membuat pengguna",
    not User.objects.filter(username='uji_ilegal').exists(), f"HTTP {r.status_code}")

print()
print("═" * 78)
print("5. BERSIH-BERSIH AKUN UJI")
print("═" * 78)
hapus = User.objects.filter(username__in=DIBERSIHKAN)
print(f"  Menghapus {hapus.count()} akun uji: {[u.username for u in hapus]}")
hapus.delete()
print(f"  Sisa akun: {[u.username for u in User.objects.all()]}")

print()
print("═" * 78)
total, ok = len(hasil), sum(hasil)
print(f"HASIL AKHIR: {ok}/{total} pemeriksaan LULUS" + (" — SEMUA BAIK ✅" if ok == total else f" — {total - ok} GAGAL ❌"))
print("═" * 78)
sys.exit(0 if ok == total else 1)
