"""Cetak potongan tangkapan layar sebagai ASCII (1 piksel = 1 karakter) supaya
tata letak & glyph bisa dibaca tanpa OCR.

Pemakaian:
    python scripts/dev/_ascii_gambar.py <berkas.png> <y0> <y1> [x0] [x1]
"""
import sys
from pathlib import Path

from PIL import Image

BERKAS = Path(sys.argv[1])
y0, y1 = int(sys.argv[2]), int(sys.argv[3])
x0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
x1 = int(sys.argv[5]) if len(sys.argv) > 5 else None

im = Image.open(BERKAS).convert("L")
w, h = im.size
x1 = min(w, x1 if x1 is not None else w)
px = im.load()

RAMPA = " .:-=+*#%@"
print(f"{BERKAS.name} x={x0}..{x1} y={y0}..{y1}")
# penggaris puluhan
baris_ratus = "".join("|" if (x % 50 == 0) else " " for x in range(x0, x1))
print(" " * 6 + baris_ratus)
baris_puluh = "".join(str((x // 10) % 10) if x % 10 == 0 else " " for x in range(x0, x1))
print(" " * 6 + baris_puluh)
for y in range(y0, min(h, y1)):
    baris = "".join(RAMPA[min(len(RAMPA) - 1, px[x, y] * len(RAMPA) // 256)] for x in range(x0, x1))
    print(f"{y:5d} {baris}")
