# OCR bawaan Windows (Windows.Media.Ocr) — dipakai untuk membaca teks pada
# tangkapan layar tanpa model vision.
# Pemakaian: powershell -NoProfile -ExecutionPolicy Bypass -File _ocr_gambar.ps1 <berkas.png>
param([Parameter(Mandatory=$true)][string]$Path)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null

$extensions = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
}
$asTask = $extensions[0]

function Await($op, $type) {
    $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
    $t.Wait(-1) | Out-Null
    return $t.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]                | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]    | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]             | Out-Null

$full = (Resolve-Path -LiteralPath $Path).Path
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($full)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

Write-Output ("bahasa OCR tersedia: " + ([Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object { $_.LanguageTag }) -join ',')

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage((New-Object Windows.Globalization.Language 'en-US')) }
if (-not $engine) { Write-Output 'TIDAK ADA ENGINE OCR'; exit 1 }

$hasil = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
Write-Output '--- TEKS ---'
foreach ($baris in $hasil.Lines) {
    $kata = @($baris.Words)
    $pertama = $kata[0]
    $terakhir = $kata[$kata.Count - 1]
    $x = [int][math]::Round($pertama.BoundingRect.X)
    $y = [int][math]::Round($pertama.BoundingRect.Y)
    $kanan = [int][math]::Round($terakhir.BoundingRect.X + $terakhir.BoundingRect.Width)
    Write-Output ("[y={0,4} x={1,4}..{2,4}] {3}" -f $y, $x, $kanan, $baris.Text)
}
