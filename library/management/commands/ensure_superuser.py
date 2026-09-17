"""
Pastikan akun superuser tersedia — idempotent, tanpa tanya-jawab.

Dipakai oleh ``setup.bat`` supaya PC baru langsung punya akun admin untuk masuk.
Aman dijalankan berkali-kali: bila akun sudah ada, peran/status dipastikan dan
tidak pernah gagal karena nama pengguna sudah dipakai.

Contoh pemakaian:
    python manage.py ensure_superuser                          # admin / 123 (bawaan)
    python manage.py ensure_superuser --username admin --password 123
    python manage.py ensure_superuser --email admin@gmail.com
    python manage.py ensure_superuser --no-reset-password      # sandi lama dibiarkan
    set ADMIN_USERNAME=admin & set ADMIN_PASSWORD=123 & python manage.py ensure_superuser

Nilai bawaan dapat diubah lewat environment: ADMIN_USERNAME, ADMIN_PASSWORD,
ADMIN_EMAIL (alias: SUPERUSER_USERNAME, SUPERUSER_PASSWORD, SUPERUSER_EMAIL).

Catatan keamanan: sandi bawaan "123" hanya untuk pemakaian lokal/pertama kali.
Ganti lewat menu Pengaturan > Ubah Kata Sandi setelah masuk.
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from library.models import UserProfile


def _env(*nama, bawaan=''):
    """Ambil nilai environment pertama yang terisi."""
    for n in nama:
        nilai = (os.getenv(n) or '').strip()
        if nilai:
            return nilai
    return bawaan


BAWAAN_USERNAME = _env('ADMIN_USERNAME', 'SUPERUSER_USERNAME', bawaan='admin')
BAWAAN_PASSWORD = _env('ADMIN_PASSWORD', 'SUPERUSER_PASSWORD', bawaan='123')
BAWAAN_EMAIL = _env('ADMIN_EMAIL', 'SUPERUSER_EMAIL', bawaan='admin@localhost')


class Command(BaseCommand):
    help = ('Membuat/ memperbarui akun superuser secara otomatis (bawaan: admin / 123). '
            'Tidak pernah gagal bila akun sudah ada — command ini idempotent.')

    def add_arguments(self, parser):
        parser.add_argument('--username', default=BAWAAN_USERNAME,
                            help=f'Nama pengguna superuser (bawaan: {BAWAAN_USERNAME})')
        parser.add_argument('--password', default=BAWAAN_PASSWORD,
                            help='Kata sandi superuser (bawaan: ADMIN_PASSWORD atau 123)')
        parser.add_argument('--email', default=BAWAAN_EMAIL,
                            help='Email superuser (boleh kosong)')
        parser.add_argument('--no-reset-password', action='store_true',
                            help='Bila akun sudah ada, JANGAN setel ulang kata sandinya')
        parser.add_argument('--quiet', action='store_true',
                            help='Hanya tampilkan pesan ringkas')

    def handle(self, *args, **options):
        username = (options['username'] or '').strip()
        password = options['password'] or ''
        email = (options['email'] or '').strip()
        reset_sandi = not options['no_reset_password']
        senyap = options['quiet']

        if not username:
            raise CommandError('Nama pengguna superuser tidak boleh kosong.')
        if not password:
            raise CommandError('Kata sandi superuser tidak boleh kosong.')

        user = User.objects.filter(username__iexact=username).first()
        dibuat = user is None
        perubahan = []

        if dibuat:
            user = User(username=username, email=email)
        else:
            if email and user.email != email:
                user.email = email
                perubahan.append('email diperbarui')
            if reset_sandi:
                user.set_password(password)
                perubahan.append('kata sandi disetel ulang')

        if dibuat:
            user.set_password(password)
            perubahan.append('akun dibuat')

        if not user.is_staff:
            user.is_staff = True
            perubahan.append('akses staff diberikan')
        if not user.is_superuser:
            user.is_superuser = True
            perubahan.append('dijadikan superuser')
        if not user.is_active:
            user.is_active = True
            perubahan.append('akun diaktifkan')

        user.save()

        # Profil dibuat oleh signal; pastikan tetap ada (mis. akun lama)
        UserProfile.objects.get_or_create(user=user)

        if senyap:
            self.stdout.write(f'[OK] superuser "{user.username}" siap '
                              f'({"dibuat" if dibuat else "sudah ada"}).')
            return

        tanda = '+' if dibuat else '='
        judul = 'dibuat' if dibuat else 'sudah ada - disiapkan ulang'
        self.stdout.write(self.style.SUCCESS(
            f'  {tanda} akun superuser "{user.username}" {judul}'
        ))
        if perubahan:
            self.stdout.write('      perubahan: ' + ', '.join(perubahan))

        sandi_dipakai = password if (dibuat or reset_sandi) else '(sandi lama dibiarkan)'
        self.stdout.write(f'      Username : {user.username}')
        self.stdout.write(f'      Kata sandi: {sandi_dipakai}')
        self.stdout.write(f'      Email    : {user.email or "-"}')
        self.stdout.write('      Login    : http://127.0.0.1:8000/login/  '
                          '(panel admin: /admin/)')
        if sandi_dipakai == '123':
            self.stdout.write(self.style.WARNING(
                '      Catatan: sandi "123" hanya untuk pemakaian lokal - '
                'ganti lewat Pengaturan > Ubah Kata Sandi.'))
