"""Ubah jenis buku menjadi pilihan TETAP (Fiksi / Non-Fiksi), genre jadi dinamis,
tambah Tahun Beli, dan hapus model BookType.

Mapping data lama: jenis buku diturunkan dari GENRE tiap buku
(genre mengandung 'fiksi' -> FIKSI, selain itu -> NON_FIKSI).
"""
from django.db import migrations, models
import django.db.models.deletion


def map_book_type(apps, schema_editor):
    Book = apps.get_model('library', 'Book')
    for book in Book.objects.select_related('genre', 'book_type_legacy').all().iterator():
        nama_genre = (book.genre.name if book.genre else '') or ''
        slug_genre = (book.genre.slug if book.genre else '') or ''
        nama_lama = (book.book_type_legacy.name if book.book_type_legacy else '') or ''
        teks = f'{slug_genre} {nama_genre} {nama_lama}'.lower()

        # "non-fiksi" harus dicek lebih dulu agar tidak tertangkap sebagai "fiksi"
        if 'non-fiksi' in teks or 'non fiksi' in teks or 'nonfiksi' in teks:
            book.book_type = 'NON_FIKSI'
        elif 'fiksi' in teks:
            book.book_type = 'FIKSI'
        else:
            book.book_type = 'NON_FIKSI'
        book.save(update_fields=['book_type'])


def revert_map(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0003_backfill_normalized_fields'),
    ]

    operations = [
        # 1. Simpan FK lama dengan nama sementara
        migrations.RenameField(
            model_name='book',
            old_name='book_type',
            new_name='book_type_legacy',
        ),

        # 2. Field baru: jenis buku sebagai pilihan tetap
        migrations.AddField(
            model_name='book',
            name='book_type',
            field=models.CharField(
                choices=[('FIKSI', 'Fiksi'), ('NON_FIKSI', 'Non-Fiksi')],
                default='NON_FIKSI', max_length=10, verbose_name='Jenis Buku',
            ),
        ),

        # 3. Field baru: tahun beli
        migrations.AddField(
            model_name='book',
            name='purchase_year',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Tahun Beli'),
        ),

        # 4. Genre jadi master data dinamis
        migrations.AddField(
            model_name='genre',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Aktif'),
        ),
        migrations.AddField(
            model_name='genre',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='genre',
            name='slug',
            field=models.SlugField(blank=True, max_length=100, unique=True, verbose_name='Slug URL'),
        ),
        migrations.AlterField(
            model_name='genre',
            name='description',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Keterangan'),
        ),
        migrations.AlterField(
            model_name='genre',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='Nama Genre / Kategori'),
        ),
        migrations.AlterField(
            model_name='genre',
            name='color_code',
            field=models.CharField(default='#8A4FFF', max_length=7, verbose_name='Warna Label'),
        ),
        migrations.AlterField(
            model_name='genre',
            name='icon',
            field=models.CharField(default='bookmark', max_length=50, verbose_name='Ikon'),
        ),
        migrations.AlterModelOptions(
            name='genre',
            options={'ordering': ['name'], 'verbose_name': 'Genre / Kategori', 'verbose_name_plural': 'Genre / Kategori'},
        ),

        # 5. Pindahkan data jenis buku dari FK lama ke pilihan tetap
        migrations.RunPython(map_book_type, revert_map),

        # 6. Bersihkan FK lama & hapus model BookType
        migrations.RemoveField(model_name='book', name='book_type_legacy'),
        migrations.DeleteModel(name='BookType'),
    ]
