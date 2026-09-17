"""
Tambah / kelola akun pengguna dari terminal.

Contoh pemakaian:
    python manage.py create_user                          # interaktif
    python manage.py create_user --username budi --password rahasia123
    python manage.py create_user --username ayah --password rahasia123 --staff --email ayah@mail.com
    python manage.py create_user --username admin --password 123 --superuser --no-input
    python manage.py create_user --list                   # tampilkan akun terdaftar
    python manage.py create_user --username budi --set-password   # atur ulang sandi
    python manage.py create_user --username budi --deactivate     # nonaktifkan

Catatan (penting untuk launcher/.exe):
    Opsi yang TIDAK diberikan kini dibiarkan kosong bila stdin bukan terminal —
    dulu command ini selalu memanggil input() untuk email/nama depan/nama
    belakang, sehingga dijalankan dari .exe --windowed (tanpa stdin) langsung
    gagal "EOFError: EOF when reading a line" dan akun tidak pernah terbuat.
    Pakai --no-input untuk memastikan tidak ada tanya-jawab sama sekali;
    lingkungan NO_INPUT=1 memberi efek yang sama.
"""
import getpass
import os
import sys

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count


class Command(BaseCommand):
    help = 'Tambah pengguna baru, atur ulang kata sandi, aktif/nonaktifkan akun'

    def add_arguments(self, parser):
        # PENTING: nilai bawaan None (bukan '') supaya command tahu bedanya
        # "tidak diberikan" vs "diberikan tetapi kosong". Tanpa ini command
        # SELALU memanggil input() untuk email/nama depan/nama belakang —
        # di .exe --windowed (tanpa stdin) itu langsung EOFError dan akun
        # tidak pernah terbuat. Lihat juga --no-input.
        parser.add_argument('--username', help='Nama pengguna untuk login')
        parser.add_argument('--password', help='Kata sandi (bila kosong akan diminta/di-generate)')
        parser.add_argument('--email', default=None, help='Email pengguna')
        parser.add_argument('--first-name', default=None, help='Nama depan')
        parser.add_argument('--last-name', default=None, help='Nama belakang')
        parser.add_argument('--staff', action='store_true', help='Beri akses panel admin (staff)')
        parser.add_argument('--superuser', action='store_true', help='Jadikan superuser')
        parser.add_argument('--inactive', action='store_true', help='Buat akun dalam keadaan nonaktif')
        parser.add_argument('--no-input', dest='no_input', action='store_true',
                            help='Jangan bertanya sama sekali (untuk launcher/.exe & otomatisasi). '
                                 'Semua data wajib dikirim lewat argumen.')
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

    # ── tanya-jawab: HANYA bila stdin benar-benar interaktif ──────────────────
    @staticmethod
    def _stdin_interaktif() -> bool:
        """
        False bila tidak ada terminal (mis. dijalankan dari launcher .exe
        --windowed, dari GUI, atau lewat CI). Lingkungan boleh memaksa
        non-interaktif dengan NO_INPUT=1.
        """
        if (os.getenv('NO_INPUT') or '').strip().lower() in ('1', 'true', 'yes'):
            return False
        try:
            if sys.stdin is None:      # .exe --windowed: sys.stdin bisa None
                return False
            return sys.stdin.isatty()
        except Exception:
            return False

    @staticmethod
    def _nilai(pertanyaan: str, nilai_argumen, boleh_tanya: bool) -> str:
        """Dari argumen kalau ada; kalau tidak dan boleh, tanya; sisanya kosong."""
        if nilai_argumen is not None:
            return (nilai_argumen or '').strip()
        if not boleh_tanya:
            return ''
        try:
            return input(pertanyaan).strip()
        except Exception:
            # EOFError / OSError / RuntimeError("lost sys.stdin") — semua berarti
            # tidak ada yang bisa ditanya: pakai nilai kosong, jangan gagal.
            return ''

    # ── eksekusi ──────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        if options['list']:
            self.tampilkan_daftar()
            return

        username = (options['username'] or '').strip()
        boleh_tanya = (not options['no_input']) and self._stdin_interaktif()
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
                    if options['password']:
                        sandi = options['password']
                    elif boleh_tanya:
                        sandi = self.minta_sandi_baru(user)
                    else:
                        raise CommandError(
                            '--set-password memerlukan --password bila dijalankan tanpa '
                            'terminal (mis. dari launcher/.exe).'
                        )
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
            if not boleh_tanya:
                raise CommandError(
                    'Nama pengguna wajib diberikan lewat --username (tidak ada '
                    'terminal untuk bertanya).'
                )
            username = input('Nama pengguna untuk login: ').strip()
        if not username:
            raise CommandError('Nama pengguna wajib diisi.')

        email = self._nilai('Email (boleh kosong): ', options['email'], boleh_tanya)
        first = self._nilai('Nama depan (boleh kosong): ', options['first_name'], boleh_tanya)
        last = self._nilai('Nama belakang (boleh kosong): ', options['last_name'], boleh_tanya)

        if options['password']:
            sandi = options['password']
        elif boleh_tanya:
            sandi = self.minta_sandi_baru()
        else:
            raise CommandError(
                'Kata sandi wajib diberikan lewat --password (tidak ada terminal '
                'untuk bertanya).'
            )

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
