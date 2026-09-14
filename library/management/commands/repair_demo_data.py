"""
Perbaiki data DEMO: selaraskan jenis buku (Fiksi/Non-Fiksi) & genre
berdasarkan daftar judul bawaan seeder.

Latar belakang: klasifikasi jenis buku demo berasal dari genre saat perekaman.
Bila genre "Fiksi"/"Non-Fiksi" pernah terhapus, sebagian buku bisa kehilangan
genre atau berubah jenisnya. Perintah ini memulihkannya secara deterministik.

Hanya menyentuh buku yang judulnya cocok dengan template seeder — entri
manual pengguna TIDAK diubah kecuali judulnya memang sama.

Pemakaian:
    python manage.py repair_demo_data            # terapkan
    python manage.py repair_demo_data --dry-run  # lihat rencana saja
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from library.models import Book, Genre
# Daftar judul & aturan diambil dari seeder agar konsisten satu sumber kebenaran
from library.management.commands.seed_data import JUDUL_FIKSI, judul_dasar


class Command(BaseCommand):
    help = 'Selaraskan jenis buku & genre untuk data demo (berdasarkan template seeder)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Tampilkan rencana perubahan tanpa menyimpan')

    def handle(self, *args, **options):
        dry = options['dry_run']

        genre_fiksi, _ = Genre.objects.get_or_create(
            slug='fiksi',
            defaults={'name': 'Fiksi', 'color_code': '#8A4FFF',
                      'description': 'Novel, cerita pendek, dan karya fiksi lainnya'},
        )
        genre_non, _ = Genre.objects.get_or_create(
            slug='non-fiksi',
            defaults={'name': 'Non-Fiksi', 'color_code': '#06B6D4',
                      'description': 'Biografi, sejarah, sains, dan pengetahuan umum'},
        )

        rencana = []
        for b in Book.objects.select_related('genre').all():
            target_jenis = (Book.BookCategory.FIKSI
                            if judul_dasar(b.title) in JUDUL_FIKSI
                            else Book.BookCategory.NON_FIKSI)
            target_genre = genre_fiksi if target_jenis == Book.BookCategory.FIKSI else genre_non

            perlu_jenis = b.book_type != target_jenis
            # Genre hanya disesuaikan bila KOSONG atau masih generik (fiksi/non-fiksi)
            # yang tidak cocok. Genre spesifik (Sejarah, Teknologi, dst) TIDAK diubah.
            generik = {'fiksi', 'non-fiksi'}
            perlu_genre = (
                b.genre is None
                or (b.genre.slug in generik and b.genre.slug != target_genre.slug)
            )

            if perlu_jenis or perlu_genre:
                rencana.append((b, target_jenis, target_genre, perlu_jenis, perlu_genre))

        self.stdout.write(f'Buku diperiksa : {Book.objects.count()}')
        self.stdout.write(f'Perlu diperbaiki: {len(rencana)}')
        for b, jenis, genre, pj, pg in rencana[:15]:
            aksi = []
            if pj:
                aksi.append(f'jenis {b.book_type} -> {jenis}')
            if pg:
                aksi.append(f'genre {b.genre.name if b.genre else "kosong"} -> {genre.name}')
            self.stdout.write(f'  - "{b.title[:42]}" : ' + '; '.join(aksi))
        if len(rencana) > 15:
            self.stdout.write(f'  ... dan {len(rencana) - 15} buku lagi')

        if dry:
            self.stdout.write(self.style.WARNING('\nMode --dry-run: tidak ada perubahan disimpan.'))
            return

        with transaction.atomic():
            for b, jenis, genre, perlu_jenis, perlu_genre in rencana:
                ubah = []
                if perlu_jenis:
                    b.book_type = jenis
                    ubah.append('book_type')
                if perlu_genre:
                    b.genre = genre
                    ubah.append('genre')
                b.save(update_fields=ubah)

        self.stdout.write(self.style.SUCCESS(f'\nSelesai: {len(rencana)} buku diperbaiki.'))
        total = Book.objects.count()
        fiksi = Book.objects.filter(book_type='FIKSI').count()
        self.stdout.write(f'  Fiksi     : {fiksi} buku')
        self.stdout.write(f'  Non-Fiksi : {total - fiksi} buku')
        self.stdout.write(f'  Tanpa genre: {Book.objects.filter(genre__isnull=True).count()} buku')
