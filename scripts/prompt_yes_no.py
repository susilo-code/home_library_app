"""
Tanya ya/tidak yang aman untuk pemakaian otomatis (dipakai setup.bat).

Perilaku:
  - stdin adalah terminal (dijalankan manusia)  -> bertanya seperti biasa.
  - stdin dialihkan (pipa/berkas, mis. dari launcher atau CI/otomatisasi)
        * ada baris masukan  -> dipakai sebagai jawaban (mis. launcher mengirim "y")
        * tanpa masukan/EOF  -> langsung memakai nilai bawaan (tidak menggantung)
  - bila stdin tidak ada sama sekali -> memakai nilai bawaan.

Jawaban dituliskan ke berkas --output sebagai "1" (ya) atau "0" (tidak), supaya
bisa dibaca batch dengan:  set /p JAWAB=<berkas

Contoh:
    .venv\\Scripts\\python.exe scripts\\prompt_yes_no.py ^
        --pertanyaan "Isi data contoh? [y/N]: " --bawaan n --output "%TEMP%\\jawab.txt"
"""
import argparse
import sys
from pathlib import Path


def tanya(pertanyaan: str, bawaan_ya: bool) -> bool:
    jawab = ''
    stdin = sys.stdin
    interaktif = bool(stdin) and stdin.isatty()

    if interaktif:
        try:
            jawab = (input(pertanyaan) or '').strip()
        except (EOFError, KeyboardInterrupt):
            jawab = ''
    else:
        baris = ''
        try:
            baris = (stdin.readline() if stdin else '') or ''
        except Exception:
            baris = ''
        baris = baris.strip()
        if baris:
            jawab = baris
            print(f'{pertanyaan}{jawab}')
        else:
            print(f'{pertanyaan}{"y" if bawaan_ya else "n"} (otomatis: tanpa tanya-jawab)')

    if not jawab:
        return bawaan_ya
    return jawab[:1].lower() in ('y', '1', 't')  # ya / yes / true


def main() -> int:
    ap = argparse.ArgumentParser(description='Tanya ya/tidak dengan aman untuk otomatisasi.')
    ap.add_argument('--pertanyaan', required=True, help='Teks pertanyaan yang ditampilkan')
    ap.add_argument('--bawaan', choices=['y', 'n', 'Y', 'N'], default='n',
                    help='Jawaban bawaan bila tidak ada masukan (bawaan: n)')
    ap.add_argument('--output', required=True, help='Berkas tujuan penulisan jawaban (1/0)')
    args = ap.parse_args()

    ya = tanya(args.pertanyaan, args.bawaan.lower() == 'y')

    tujuan = Path(args.output)
    try:
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        tujuan.write_text('1' if ya else '0', encoding='ascii')
    except OSError as exc:
        print(f'[X] Gagal menulis {tujuan}: {exc}')
        return 1

    print('      -> ya' if ya else '      -> tidak')
    return 0


if __name__ == '__main__':
    sys.exit(main())
