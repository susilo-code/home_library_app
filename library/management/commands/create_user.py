"""
Tambah / kelola akun pengguna dari terminal.

Contoh pemakaian:
    python manage.py create_user                          # interaktif
    python manage.py create_user --username budi --password rahasia123
    python manage.py create_user --username ayah --password rahasia123 --staff --email ayah@mail.com
    python manage.py create_user --list                   # tampilkan akun terdaftar
    python manage.py create_user --username budi --set-password   # atur ulang sandi
    python manage.py create_user --username budi --deactivate     # nonaktifkan
"""
import getpass

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count


class Command(BaseCommand):
    help = 'Tambah pengguna baru, atur ulang kata sandi, aktif/nonaktifkan akun'

    def add_arguments(self, parser):
        parser.add_argument('--username', help='Nama pengguna untuk login')
        parser.add_argument('--password', help='Kata sandi (bila kosong akan diminta/di-generate)')
        parser.add_argument('--email', default='', help='Email pengguna')
        parser.add_argument('--first-name', default='', help='Nama depan')
        parser.add_argument('--last-name', default='', help='Nama belakang')
        parser.add_argument('--staff', action='store_true', help='Beri akses panel admin (staff)')
        parser.add_argument('--superuser', action='store_true', help='Jadikan superuser')
        parser.add_argument('--inactive', action='store_true', help='Buat akun dalam keadaan nonaktif')
        # Aksi lain terhadap akun yang sudah ada
        parser.add_argument('--list', action='store_true', help='Tampilkan daftar akun lalu keluar')
        parser.add_argument('--set-password', action='store_true', help='Atur ulang kata sandi akun')
        parser.add_argument('--activate', action='store_true', help='Aktifkan akun')
        parser.add_argument('--deactivate', action='store_true', help='Nonaktifkan akun')

    # ── utilitas ──────────────────────────────────────────────────────────────
    def tampilkan_daftar(self):
        users = User.objects.annotate(jumlah_buku=Count('recorded_books')).order_by(
            '-is_superuser', '-is_staff', 'username')
        if not users:
            self.stdout.write(self.style.WARNING('Belum ada akun pengguna.'))
            return
        self.stdout.write(f'{"USERNAME":<18}{"PERAN":<14}{"STATUS":<10}{"BUKU":>6}  EMAIL')
        self.stdout.write('-' * 70)
        for u in users:
            peran = 'superuser' if u.is_superuser else ('staff' if u.is_staff else 'anggota')
            status = 'aktif' if u.is_active else 'nonaktif'
            self.stdout.write(f'{u.username:<18}{peran:<14}{status:<10}{u.jumlah_buku:>6}  {u.email or "-"}')

    def minta_sandi_baru(self, user=None) -> str:
        """Minta kata sandi dua kali sampai cocok (tanpa aturan kerumitan)."""
        while True:
            p1 = getpass.getpass('Kata sandi: ')
            p2 = getpass.getpass('Ulangi kata sandi: ')
            if p1 != p2:
                self.stderr.write(self.style.ERROR('  Kata sandi tidak sama, coba lagi.'))
                continue
            if not p1:
                self.stderr.write(self.style.ERROR('  Kata sandi tidak boleh kosong.'))
                continue
            return p1

    # ── eksekusi ──────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        if options['list']:
            self.tampilkan_daftar()
            return

        username = (options['username'] or '').strip()
        ada_aksi = any([options['set_password'], options['activate'], options['deactivate'],
                        options['staff'], options['superuser'], options['inactive']])

        # 1) Akun sudah ada -> terapkan perubahan (sandi / peran / status)
        if username:
            user = User.objects.filter(username__iexact=username).first()
            if user:
                if not ada_aksi:
                    raise CommandError(
                        f'Akun "{user.username}" sudah ada. '
                        'Tambahkan --set-password / --staff / --superuser / --deactivate '
                        'bila ingin mengubahnya, atau pakai nama lain untuk akun baru.'
                    )
                perubahan = []
                if options['set_password']:
                    sandi = options['password'] or self.minta_sandi_baru(user)
                    user.set_password(sandi)
                    perubahan.append('kata sandi diperbarui')
                if options['staff'] and not user.is_staff:
                    user.is_staff = True
                    perubahan.append('diberi akses staff')
                if options['superuser'] and not user.is_superuser:
                    user.is_superuser = True
                    user.is_staff = True
                    perubahan.append('dijadikan superuser')
                if options['activate'] and not user.is_active:
                    user.is_active = True
                    perubahan.append('diaktifkan')
                if options['deactivate'] and user.is_active:
                    user.is_active = False
                    perubahan.append('dinonaktifkan')
                if options['inactive'] and user.is_active:
                    user.is_active = False
                    perubahan.append('dinonaktifkan')
                user.save()
                if perubahan:
                    self.stdout.write(self.style.SUCCESS(
                        f'"{user.username}": ' + ', '.join(perubahan) + '.'
                    ))
                else:
                    self.stdout.write('Tidak ada perubahan (status sudah sesuai).')
                return

        # 2) Tambah pengguna baru
        if not username:
            username = input('Nama pengguna untuk login: ').strip()
        if not username:
            raise CommandError('Nama pengguna wajib diisi.')

        email = options['email'] or input('Email (boleh kosong): ').strip()
        first = options['first_name'] or input('Nama depan (boleh kosong): ').strip()
        last = options['last_name'] or input('Nama belakang (boleh kosong): ').strip()

        sandi = options['password'] or self.minta_sandi_baru()

        user = User.objects.create_user(
            username=username,
            email=email,
            password=sandi,
            first_name=first,
            last_name=last,
        )
        user.is_staff = bool(options['staff'] or options['superuser'])
        user.is_superuser = bool(options['superuser'])
        user.is_active = not options['inactive']
        user.save()

        # Profil otomatis dibuat oleh signal; pastikan tetap ada
        from library.models import UserProfile
        UserProfile.objects.get_or_create(user=user)

        peran = 'superuser' if user.is_superuser else ('staff' if user.is_staff else 'anggota')
        status = 'aktif' if user.is_active else 'nonaktif'
        self.stdout.write(self.style.SUCCESS(
            f'Pengguna "{user.username}" berhasil dibuat ({peran}, {status}).'
        ))
        self.stdout.write('  Login di: http://127.0.0.1:8000/login/')
        self.stdout.write('  Sarankan pengguna mengganti kata sandi lewat Pengaturan > Ubah Kata Sandi.')
