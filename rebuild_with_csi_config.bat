@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo REBUILD ESP32 CSI FIRMWARE WITH CONFIG
echo ======================================================================

REM Activate ESP-IDF
call C:\esp-idf\export.bat

REM Navigate to project
cd /d C:\ESP32-CSI-Tool\passive

REM Step 1: Clean
echo.
echo [1/4] Clean building...
call idf.py fullclean
if !errorlevel! neq 0 (
    echo ERROR: Clean failed
    exit /b 1
)

REM Step 2: Build
echo.
echo [2/4] Building firmware...
call idf.py build
if !errorlevel! neq 0 (
    echo ERROR: Build failed
    exit /b 1
)

REM Step 3: Erase flash
echo.
echo [3/4] Erasing ESP32 flash on COM5...
python -m esptool --chip auto -p COM5 -b 460800 erase_flash
if !errorlevel! neq 0 (
    echo ERROR: Erase failed
    exit /b 1
)

timeout /t 2 /nobreak

REM Step 4: Flash
echo.
echo [4/4] Flashing firmware...
python -m esptool --chip auto -p COM5 -b 460800 --before default-reset --after hard-reset write-flash --flash-mode dio --flash-freq 40m --flash-size 2MB 0x1000 build\bootloader\bootloader.bin 0x8000 build\partition_table\partition-table.bin 0x10000 build\passive.bin
if !errorlevel! neq 0 (
    echo ERROR: Flash failed
    exit /b 1
)

echo.
echo ======================================================================
echo SUCCESS! Firmware rebuilt and flashed with CSI enabled
echo ======================================================================
echo Now run: python main.py live --port COM5 --no_display
echo ======================================================================

endlocal
