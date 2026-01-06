$uvi = Get-Process uvicorn
if ($uvi) {
  # try gracefully first
  $uvi.CloseMainWindow()
  # kill after five seconds
  Sleep 5
  if (!$firefox.started) {
    $uvi | Stop-Process -Force
  }
}
Remove-Variable uvi

poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
