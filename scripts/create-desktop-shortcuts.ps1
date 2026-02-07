# Create Desktop Shortcuts for Demo Apps (Hidden Console)
# These shortcuts launch Electron apps without visible command prompt
# The LLM agent can click these icons to open the apps
#
# Usage: .\scripts\create-desktop-shortcuts.ps1 [-ProjectPath "C:\data\proxi-ai"]

param(
    [string]$ProjectPath = "C:\data\proxi-ai"
)

$ErrorActionPreference = "Stop"
$Desktop = [Environment]::GetFolderPath("Desktop")

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Creating Desktop Shortcuts (Hidden Console)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# App configurations
$apps = @(
    @{
        Name = "Pricing System"
        Folder = "pricing-app"
        Icon = "💰"
    },
    @{
        Name = "CRM System"  
        Folder = "crm-app"
        Icon = "👥"
    }
)

foreach ($app in $apps) {
    $appPath = Join-Path $ProjectPath "demo-apps\$($app.Folder)"
    $vbsPath = Join-Path $ProjectPath "scripts\launch-$($app.Folder).vbs"
    $shortcutPath = Join-Path $Desktop "$($app.Name).lnk"
    
    # Check if app exists
    if (-not (Test-Path (Join-Path $appPath "package.json"))) {
        Write-Host "  [SKIP] $($app.Name) - not found at $appPath" -ForegroundColor Yellow
        continue
    }
    
    # Create VBS launcher (hides command prompt)
    $vbsContent = @"
' Launch $($app.Name) without visible command prompt
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "$appPath"
WshShell.Run "cmd /c npm start", 0, False
Set WshShell = Nothing
"@
    $vbsContent | Out-File -FilePath $vbsPath -Encoding ASCII -Force
    Write-Host "  [OK] Created launcher: $vbsPath" -ForegroundColor Gray
    
    # Create desktop shortcut
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = "wscript.exe"
    $Shortcut.Arguments = "`"$vbsPath`""
    $Shortcut.WorkingDirectory = $appPath
    $Shortcut.Description = "$($app.Name) - Proxi Demo App"
    
    # Try to use a relevant icon
    $electronExe = Join-Path $appPath "node_modules\electron\dist\electron.exe"
    if (Test-Path $electronExe) {
        $Shortcut.IconLocation = "$electronExe,0"
    }
    
    $Shortcut.Save()
    Write-Host "  [OK] Created shortcut: $shortcutPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Desktop shortcuts created!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "The LLM agent can now:" -ForegroundColor Cyan
Write-Host "  1. See 'Pricing System' and 'CRM System' icons on desktop" -ForegroundColor Gray
Write-Host "  2. Click them to launch apps (no command prompt visible)" -ForegroundColor Gray
Write-Host ""
