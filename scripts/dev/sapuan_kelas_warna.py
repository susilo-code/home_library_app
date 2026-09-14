"""
Sapuan warna teks template → kelas semantik (teks-utama/kedua/samar/…).

Menjalankan tanpa argumen = DRY RUN (hanya menampilkan rencana).
Tambahkan --terapkan untuk menulis perubahan.

Aturan: pada satu atribut class, pasangan `text-<warna> dark:text-<warna>`
diganti satu kelas semantik yang mengambil warna dari variabel CSS
(:root = mode terang, .dark = mode gelap). Variasi `hover:`/`focus:` tidak
disentuh.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERAPKAN = "--terapkan" in sys.argv

# (token mode terang, token mode gelap) -> kelas semantik
PASANGAN = {
    ("text-purple-800", "dark:text-purple-200"): "teks-utama",
    ("text-purple-700", "dark:text-purple-200"): "teks-utama",
    ("text-purple-700", "dark:text-purple-300"): "teks-utama",
    ("text-purple-600", "dark:text-purple-300"): "teks-utama",
    ("text-purple-600", "dark:text-purple-400"): "teks-kedua",
    ("text-purple-500", "dark:text-purple-400"): "teks-kedua",
    ("text-indigo-600", "dark:text-indigo-400"): "teks-kedua",
    ("text-purple-400", "dark:text-purple-500"): "teks-samar",
    ("text-purple-300", "dark:text-purple-700"): "teks-samar",
    ("text-purple-200", "dark:text-purple-700"): "teks-samar",
    ("text-red-600", "dark:text-red-400"): "teks-bahaya",
    ("text-red-700", "dark:text-red-300"): "teks-bahaya",
    ("text-red-500", "dark:text-red-400"): "teks-bahaya",
    ("text-green-600", "dark:text-green-400"): "teks-sukses",
    ("text-green-700", "dark:text-green-300"): "teks-sukses",
    ("text-green-500", "dark:text-green-400"): "teks-sukses",
    ("text-emerald-600", "dark:text-emerald-400"): "teks-sukses",
    ("text-yellow-700", "dark:text-yellow-300"): "teks-peringatan",
    ("text-yellow-500", "dark:text-yellow-400"): "teks-peringatan",
    ("text-amber-700", "dark:text-amber-300"): "teks-peringatan",
    ("text-amber-800", "dark:text-amber-200"): "teks-peringatan",
    ("text-amber-700", "dark:text-amber-200"): "teks-peringatan",
    ("text-amber-600", "dark:text-amber-400"): "teks-peringatan",
    ("text-amber-800", "dark:text-amber-300"): "teks-peringatan",
    ("text-red-600", "dark:text-red-300"): "teks-bahaya",
    ("text-deep-purple-600", "dark:text-purple-300"): "teks-kedua",
    ("text-purple-200", "dark:text-purple-700"): "teks-samar",
}

POLA_KELAS = re.compile(r'class="([^"]*)"')


def sapu_kelas(teks: str) -> tuple[str, int]:
    total = 0

    def ganti(m):
        nonlocal total
        kelas = m.group(1)
        if "{{" in kelas or "{%" in kelas:
            return m.group(0)
        token = kelas.split()
        keluaran, dipakai = [], set()
        for t in token:
            if t in dipakai:
                continue
            cocok = None
            for (terang, gelap), semantik in PASANGAN.items():
                if t == terang and gelap in token:
                    cocok = (gelap, semantik)
                    break
                if t == gelap and terang in token:
                    cocok = (terang, semantik)
                    break
            if cocok:
                dipakai.add(cocok[0])
                if semantik := cocok[1]:
                    keluaran.append(semantik)
                    total += 1
                continue
            keluaran.append(t)
        return 'class="' + " ".join(keluaran) + '"'

    return POLA_KELAS.sub(ganti, teks), total


def sapu_badge_genre(teks: str) -> tuple[str, int]:
    """`class="badge" style="background-color: X20; color: X;"` -> badge-genre."""
    pola = re.compile(
        r'class="badge([^"]*)"\s+style="background-color:\s*(\{\{[^}]+\}\}|\S+?)20;\s*color:\s*\2;"')
    baru, n = pola.subn(
        lambda m: f'class="badge-genre{m.group(1)}" style="--warna-genre: {m.group(2)}"',
        teks)
    return baru, n


def main() -> int:
    berkas_diubah = 0
    total_ganti = 0
    sisa_semua = []
    for f in sorted((ROOT / "templates").rglob("*.html")):
        asli = f.read_text(encoding="utf-8")
        baru, n1 = sapu_kelas(asli)
        baru, n2 = sapu_badge_genre(baru)
        sisa_semua.append((f, baru))
        if baru == asli:
            continue
        berkas_diubah += 1
        total_ganti += n1 + n2
        print(f"  {f.relative_to(ROOT)}: {n1} pasangan warna -> kelas semantik, "
              f"{n2} badge genre")
        if TERAPKAN:
            f.write_text(baru, encoding="utf-8")

    print()
    print(f"  berkas diubah: {berkas_diubah}, penggantian: {total_ganti}")
    print(f"  mode: {'DITERAPKAN' if TERAPKAN else 'DRY RUN (belum ditulis)'}")

    # Laporkan sisa `dark:text-` yang belum tercakup (perlu tinjauan manual)
    print()
    print("  SISA `dark:text-` yang belum bisa dipetakan otomatis:")
    jumlah = 0
    for f, isi in sisa_semua:
        for i, baris in enumerate(isi.splitlines(), 1):
            for m in re.finditer(r"(?<![\w:-])dark:text-[\w/\[\]-]+", baris):
                jumlah += 1
                if jumlah <= 25:
                    print(f"    {f.name}:{i}  {m.group(0)}")
    print(f"    total sisa: {jumlah}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
