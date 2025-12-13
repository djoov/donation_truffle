@echo off
TITLE DonasiKuy Auto Updater
COLOR 0A

echo ========================================================
echo      DONASIKUY PROJECT UPDATER (SATU KLIK)
echo ========================================================
echo.

:: 1. Cek status git
echo [1/5] Memeriksa status Git...
git status

:: 2. Amankan perubahan lokal jika ada (Stash) agar tidak bentrok
echo.
echo [2/5] Mengamankan pekerjaan lokal anda sementara...
git stash

:: 3. Tarik update dari GitHub
echo.
echo [3/5] Mengambil update terbaru dari GitHub Punya Jouvi...
git pull origin main

:: 4. Update Library Python (Jaga-jaga kalau ada library baru)
echo.
echo [4/5] Cek apakah ada library Python baru...
cd backend_python
if exist venv\Scripts\activate (
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    echo Venv tidak ditemukan, melewati install requirements...
)
cd ..

:: 5. Selesai
echo.
echo ========================================================
echo      UPDATE SELESAI! PROJECT SUDAH VERSI TERBARU.
echo ========================================================
echo.
echo Silakan jalankan 'python app.py' seperti biasa.
pause