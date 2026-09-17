#!/usr/bin/env bash
# Jalankan SEMUA pemeriksaan proyek dalam satu perintah.
#
# Pemakaian (dari folder aplikasi, di Git Bash):
#     bash scripts/dev/jalankan_semua_cek.sh
#
# Keluar dengan kode != 0 bila ADA satu suite yang gagal, supaya bisa dipakai
# sebagai gerbang (mis. sebelum commit) — bukan sekadar cetakan.
set -u
cd "$(dirname "$0")/../.." || exit 2

PY="./.venv/Scripts/python.exe"
SUITES=(
  verify_perbaikan_v3
  verify_perbaikan_v4
  verify_perbaikan_v5
  verify_perbaikan_v6
  verify_perbaikan_v7
  verify_perbaikan_v8
  verify_features_v2
  verify_user_management
  verify_label_rak
  verify_login_ikon
  verify_live_v3
  cek_css_lokal
)
gagal_suite=()
lulus_suite=0

echo "=============================================================================="
echo "  SEMUA PEMERIKSAAN PROYEK"
echo "=============================================================================="
for suite in "${SUITES[@]}"; do
  berkas="scripts/dev/${suite}.py"
  if [ ! -f "$berkas" ]; then
    echo "== ${suite}: TIDAK ADA (dilewati)"
    continue
  fi
  keluaran="$("$PY" "$berkas" 2>&1)"
  kode=$?
  ringkas="$(printf '%s\n' "$keluaran" | grep -E 'HASIL|RINGKASAN|Belum tergenerate' | tail -2 | tr '\n' ' | ')"
  if [ $kode -eq 0 ]; then
    lulus_suite=$((lulus_suite + 1))
    echo "== ${suite}: LULUS  ${ringkas}"
  else
    gagal_suite+=("$suite")
    echo "== ${suite}: GAGAL  ${ringkas}"
    printf '%s\n' "$keluaran" | grep -E 'GAGAL' | head -6 | sed 's/^/     /'
  fi
done

echo "------------------------------------------------------------------------------"
echo "SUITE LULUS: ${lulus_suite}/${#SUITES[@]}   GAGAL: ${#gagal_suite[@]}"
if [ ${#gagal_suite[@]} -gt 0 ]; then
  echo "Yang gagal: ${gagal_suite[*]}"
  exit 1
fi
echo "SEMUA SUITE HIJAU"
exit 0
