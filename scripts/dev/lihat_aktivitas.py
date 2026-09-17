"""Lihat 20 aktivitas terakhir (untuk memastikan siapa/kapan mengubah identitas aplikasi)."""
import os
import sys
from pathlib import Path

_RO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_RO))
os.chdir(_RO)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()
from library.models import ActivityLog, SiteConfig  # noqa: E402

cfg = SiteConfig.get_solo()
print(f"SiteConfig sekarang: {cfg.app_name!r} / {cfg.app_short_name!r} / "
      f"label_owner={cfg.label_owner!r} / updated_at={cfg.updated_at}")
print()
print("20 aktivitas terakhir:")
for a in ActivityLog.objects.select_related("user").order_by("-timestamp")[:20]:
    print(f"  {a.timestamp:%Y-%m-%d %H:%M:%S} | {getattr(a.user, 'username', None) or '-'} | "
          f"{a.action} | {(a.detail or '')[:90]}")
