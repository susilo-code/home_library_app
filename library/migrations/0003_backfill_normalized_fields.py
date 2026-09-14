"""Backfill kolom normalisasi (title_normalized / author_normalized) untuk data yang sudah ada.

Dibuat agar deteksi duplikat langsung akurat untuk buku-buku lama,
tanpa perlu menyimpan ulang lewat UI.
"""
import re

from django.db import migrations


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def backfill(apps, schema_editor):
    Book = apps.get_model('library', 'Book')
    updated = []
    for book in Book.objects.all().iterator():
        new_title = normalize(book.title)
        new_author = normalize(book.author)
        if book.title_normalized != new_title or book.author_normalized != new_author:
            book.title_normalized = new_title
            book.author_normalized = new_author
            updated.append(book)
    if updated:
        Book.objects.bulk_update(updated, ['title_normalized', 'author_normalized'], batch_size=500)


def unbackfill(apps, schema_editor):
    Book = apps.get_model('library', 'Book')
    Book.objects.update(title_normalized='', author_normalized='')


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0002_booktype_shelf_book_author_normalized_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
