@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo ESP32 FLASH ERASE AND REFLASH
echo ======================================================================

REM Setup environment
call C:\esp-idf\export.bat

cd /d C:\ESP32-CSI-Tool\passive

REM Step 1: Erase flash
echo.
echo [1/3] Erasing ESP32 flash on COM5...
idf.py erase-flash -p COM5
if !errorlevel! neq 0 (
    echo ERROR: Flash erase failed
    exit /b 1
)

echo [OK] Flash erased

REM Step 2: Flash firmware
echo.
echo [2/3] Flashing CSI firmware...
idf.py flash -p COM5 -b 460800
if !errorlevel! neq 0 (
    echo ERROR: Flash failed
    exit /b 1
)

echo [OK] Firmware flashed

REM Step 3: Monitor serial output
echo.
echo [3/3] Waiting 3 seconds for ESP32 to boot...
timeout /t 3 /nobreak

echo.
echo ======================================================================
echo SUCCESS! ESP32 ready
echo ======================================================================
echo Now run: python main.py live --port COM5 --no_display
echo ======================================================================

endlocal
