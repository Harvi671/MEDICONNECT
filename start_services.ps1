# Start both MediConnect services (Windows PowerShell)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Starting patient-service on port 8001..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\patient-service'; python -m uvicorn main:app --host 127.0.0.1 --port 8001" -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "Starting booking-service on port 8000..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\booking-service'; `$env:PATIENT_SERVICE_URL='http://127.0.0.1:8001'; python -m uvicorn main:app --host 127.0.0.1 --port 8000" -WindowStyle Normal

Write-Host "Services started. Booking API: http://127.0.0.1:8000/docs"
