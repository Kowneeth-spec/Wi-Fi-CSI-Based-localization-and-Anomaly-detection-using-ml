# Rebuild ESP32 CSI firmware with proper configuration

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "REBUILDING ESP32 CSI FIRMWARE WITH PROPER CONFIGURATION"
Write-Host "======================================================================" -ForegroundColor Cyan

$passive_dir = "C:\ESP32-CSI-Tool\passive"
$idf_export = "C:\esp-idf\export.bat"

# Step 1: Activate ESP-IDF environment
Write-Host "`n[1/4] Activating ESP-IDF environment..." -ForegroundColor Yellow
cmd /c "$idf_export && cd /d $passive_dir && echo ESP-IDF activated"

# Step 2: Clean previous build
Write-Host "`n[2/4] Cleaning previous build..." -ForegroundColor Yellow
cmd /c "$idf_export && cd /d $passive_dir && idf.py fullclean"

# Step 3: Set configuration options via command line
Write-Host "`n[3/4] Setting menuconfig options..." -ForegroundColor Yellow
$sdkconfig = "$passive_dir\sdkconfig"

# Backup current sdkconfig
if (Test-Path $sdkconfig) {
    Copy-Item $sdkconfig "$sdkconfig.backup"
    Write-Host "  [OK] Backed up existing sdkconfig"
}

# Add configuration options to sdkconfig
@"
CONFIG_SHOULD_COLLECT_CSI=y
CONFIG_SEND_CSI_TO_SERIAL=y
CONFIG_WIFI_CHANNEL=6
CONFIG_ESP_CONSOLE_UART_BAUDRATE=115200
CONFIG_ESPTOOLPY_MONITOR_BAUD=115200
"@ | Add-Content $sdkconfig

Write-Host "  [OK] Added CSI configuration options"

# Step 4: Build firmware
Write-Host "`n[4/4] Building firmware with CSI enabled..." -ForegroundColor Yellow
cmd /c "$idf_export && cd /d $passive_dir && idf.py build"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "BUILD COMPLETE - Ready to flash with: idf.py flash" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
