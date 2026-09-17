"""Cadangkan & bandingkan SiteConfig (identitas aplikasi) — pengaman sebelum
menjalankan suite uji lama yang menulis SiteConfig (mis. verify_perbaikan_v3).

Pemakaian:
    python scripts/dev/_dbg_siteconfig.py snapshot   # tulis _siteconfig_cadangan.json
    python scripts/dev/_dbg_siteconfig.py cek        # bandingkan & pulihkan bila berubah
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()
from library.models import SiteConfig  # noqa: E402

BERKAS = ROOT / "_siteconfig_cadangan.json"


def bidang():
    return [f.name for f in SiteConfig._meta.get_fields()
            if getattr(f, "concrete", False) and f.name != "id"]


def main() -> int:
    cfg = SiteConfig.get_solo()
    nama = bidang()
    kini = {n: getattr(cfg, n) for n in nama}
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        BERKAS.write_text(json.dumps(kini, indent=2, ensure_ascii=False, default=str),
                          encoding="utf-8")
        print(f"cadangan ditulis: {BERKAS}")
        for n in nama:
            print(f"  {n} = {kini[n]!r}")
        return 0
    if not BERKAS.exists():
        print("[GAGAL] belum ada cadangan — jalankan 'snapshot' dulu")
        return 1
    asli = json.loads(BERKAS.read_text(encoding="utf-8"))
    beda = {n: (asli.get(n), kini.get(n)) for n in asli
            if n not in ("updated_at",) and asli.get(n) != kini.get(n)}
    if beda:
        print("[!] SiteConfig BERUBAH:")
        for n, (a, b) in beda.items():
            print(f"    {n}: {a!r} -> {b!r}")
        for n, (a, _b) in beda.items():
            setattr(cfg, n, a)
        cfg.save()
        cfg.refresh_from_db()
        pulih = all(getattr(cfg, n) == asli[n] for n in asli)
        print(f"    dipulihkan: {'BERHASIL' if pulih else 'GAGAL'}")
        return 0 if pulih else 1
    print("[OK] SiteConfig tidak berubah")
    return 0


if __name__ == "__main__":
    sys.exit(main())
