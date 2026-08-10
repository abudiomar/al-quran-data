param(
  [Parameter(Mandatory = $true)]
  [string]$OutputDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$resources = [ordered]@{
  ibn_kathir = 14
  tabari = 15
  baghawi = 94
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

foreach ($entry in $resources.GetEnumerator()) {
  $url = "https://qul.tarteel.ai/api/v1/tafsirs/$($entry.Value)/by_range?from=1:1&to=114:6&per_page=10000"
  Write-Output "Fetching $($entry.Key) from QUL..."
  $response = Invoke-RestMethod -Uri $url
  $book = [ordered]@{}

  foreach ($tafsir in $response.tafsirs) {
    $verses = @($tafsir.verses)
    if ($verses.Count -eq 0 -or [string]::IsNullOrWhiteSpace($tafsir.text)) {
      continue
    }

    $anchor = [string]$verses[0]
    $record = [ordered]@{ text = [string]$tafsir.text }
    if ($verses.Count -gt 1) {
      $record.ayah_keys = $verses
    }
    $book[$anchor] = $record

    foreach ($verse in $verses | Select-Object -Skip 1) {
      $book[[string]$verse] = $anchor
    }
  }

  if ($book.Count -ne 6236) {
    throw "$($entry.Key): expected 6236 mapped ayahs, got $($book.Count)"
  }

  $path = Join-Path $OutputDirectory "$($entry.Key).json"
  $book | ConvertTo-Json -Depth 8 -Compress | Set-Content -LiteralPath $path -Encoding utf8NoBOM
  Write-Output "Wrote $path ($($book.Count) ayahs)"
}
