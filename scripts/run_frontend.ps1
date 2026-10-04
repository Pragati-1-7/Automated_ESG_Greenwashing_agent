# Windows PowerShell: start the React UI on http://localhost:5173
Set-Location web
if (-not (Test-Path node_modules)) { npm install }
npm run dev
