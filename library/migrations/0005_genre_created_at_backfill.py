"""Backfill Genre.created_at lalu jadikan non-null (auto_now_add)."""
from django.db import migrations, models
from django.utils import timezone


def backfill_created_at(apps, schema_editor):
    Genre = apps.get_model('library', 'Genre')
    Genre.objects.filter(created_at__isnull=True).update(created_at=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0004_book_type_fixed_and_purchase_year'),
    ]

    operations = [
        migrations.RunPython(backfill_created_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='genre',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
