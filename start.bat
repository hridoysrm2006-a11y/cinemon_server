@echo off
title CineMon Download Server
color 0A

echo.
echo  ================================
echo   CineMon Download Server
echo  ================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Download from: https://python.org
    pause
    exit /b
)

REM Install yt-dlp if missing
yt-dlp --version >nul 2>&1
if errorlevel 1 (
    echo [setup] Installing yt-dlp...
    pip install yt-dlp -q
)

REM Check ffmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] ffmpeg not found!
    echo Download ffmpeg.exe from: https://www.gyan.dev/ffmpeg/builds/
    echo Extract and place ffmpeg.exe in C:\tools\ then add C:\tools to PATH
    echo.
    echo Download will still work for direct MP4 streams without ffmpeg.
    echo But HLS streams need ffmpeg to merge video+audio.
    echo.
    pause
)

REM Get local IP
echo [info] Your local IP addresses:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do echo        http:%%a:8080
echo.
echo [info] Open one of the above URLs in your browser or phone
echo [info] Press Ctrl+C to stop the server
echo.

REM Start server
python server.py
pause
