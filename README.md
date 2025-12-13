# 🪙 DonasiKuy - Decentralized Crowdfunding Platform
### Final Project: Teknologi Blockchain & Distributed Ledger — Semester 5

![Badge](https://img.shields.io/badge/Blockchain-Ethereum-3C3C3D?style=for-the-badge&logo=ethereum)
![Badge](https://img.shields.io/badge/Backend-Flask-000000?style=for-the-badge&logo=flask)
![Badge](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**DonasiKuy** adalah platform donasi transparan berbasis Ethereum Blockchain yang menggabungkan kemudahan Web 2.0 dengan keamanan Web 3.0 (Hybrid Architecture).

Proyek ini bertujuan untuk mengatasi krisis kepercayaan dalam donasi online dengan mencatat setiap transaksi secara kekal (immutable) di blockchain, sambil menyediakan antarmuka modern yang ramah pengguna.

---

## ✨ Fitur Unggulan (New Features)

### 🛡️ 1. Smart Security & Validation
*   **Strict Balance Check**: Sistem menolak transaksi donasi jika `Saldo < (Donasi + Gas Fee)`.
*   **Dynamic Gas Estimation**: Menggunakan `web3.eth.estimate_gas` untuk kalkulasi biaya transaksi yang akurat, mencegah kegagalan transaksi di jaringan.
*   **Admin Security Dashboard (SIEM)**: Pemantauan keamanan, deteksi serangan, dan log aktivitas mencurigakan.

### 🔔 2. User Engagement System
*   **Welcome Email**: Sapaan hangat otomatis via Email (SMTP Gmail) saat registrasi berhasil.
*   **SweetAlert Notifications**: Notifikasi popup interaktif (bukan sekadar teks) untuk Sukses/Error.
*   **Live Activity Toast**: Notifikasi realtime aktivitas donasi pengguna lain.
*   **Smart Countdown**: Penghitung mundur otomatis untuk tenggat kampanye.

### ⚡ 3. Performance & Tech
*   **Smart Caching**: Menyimpan data blockchain (Block Height, Gas Price) di memori selama 5 detik untuk akses super cepat via WiFi / Mobile.
*   **Public Blockchain Explorer**: Visualisasi rantai blok dan transaksi donasi secara live & transparan.
*   **Responsive UI**: Tampilan dioptimalkan untuk Desktop & Mobile.

---

## 👥 Tim Pengembang

| Peran              | Nama                         | Fokus Tugas                                     |
| ------------------ | ---------------------------- | ----------------------------------------------- |
| Analis & Pemodel   | **Masdani Ilman P. K.**      | Use Case, Flow Sistem, Requirement Analysis     |
| Arsitek & Engineer | **Nur Akhmad Van Jouvi**     | Smart Contract, Flask Backend, Security Logic   |
| QA & Security      | **Fathur Rahman**            | Security Testing, Bug Hunting, Validation Test  |

---

## 🛠️ Teknologi (Tech Stack)

* **Core Blockchain**: Ethereum (Simulasi via Ganache)
* **Smart Contract**: Solidity (.sol), Truffle Framework
* **Backend**: Python Flask
* **Frontend**: Bootstrap 5, Jinja2, SweetAlert2, Chart.js
* **Database**: SQLite (untuk data user & meta-data kampanye)
* **Connector**: Web3.py (Jembatan Python ↔ Blockchain)

---

## 🚀 Panduan Instalasi & Menjalankan

Ikuti langkah berikut agar proyek berjalan lancar.

### 1. Persiapan Software (Prerequisites)
Pastikan sudah terinstall: `Node.js`, `Python 3.8+`, `Ganache GUI`, dan `Git`.

### 2. Setup Blockchain (Ganache)
1.  Buka Ganache, pilih **New Workspace**.
2.  Set Port Number = **7545**.
3.  Simpan dan biarkan menyala.
4.  *Penting*: Pastikan Network ID sesuai dengan `truffle-config.js` (biasanya default 5777).

### 3. Deploy Smart Contract
Masuk ke terminal root folder (`donation_truffle`):
```bash
npm install -g truffle
truffle migrate --reset
```
Setelah sukses, update alamat kontrak di `backend_python/contract_data.py` jika diperlukan (biasanya otomatis jika menggunakan logic JSON artifact).

### 4. Setup Backend (Python Flask)
Masuk ke folder backend:
```bash
cd backend_python
python -m venv venv
```

Aktifkan virtual environment:
```bash
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

Install library:
```bash
pip install -r requirements.txt
```

### 5. Konfigurasi Email (Opsional)
Buka `app.py`, cari bagian **CONFIG EMAIL**.
```python
app.config['MAIL_USERNAME'] = 'email_anda@gmail.com'
app.config['MAIL_PASSWORD'] = 'app_password_anda' # Gunakan App Password Gmail
```

### 6. Jalankan Aplikasi
```bash
python app.py
```

### 7. Akses Platform
*   **Localhost**: `http://127.0.0.1:5000`
*   **Mobile (Satu WiFi)**: `http://<IP_LAPTOP_ANDA>:5000`

---

## 🔑 Akun Demo (Ganache)
Gunakan Private Key dari Ganache untuk login/transaksi.

### 1. Super Admin
*   Email: **admin@donasi.com**
*   Password: **admin123**
*   *Fungsi*: Dashboard SIEM, Approve/Reject Kampanye.

### 2. Akun Kreator
*   Register baru di web -> Pilih Role **Kreator**.
*   Gunakan Private Key akun ke-2 dari Ganache.
*   *Fungsi*: Buat Galang Dana, Request Withdraw.

### 3. Akun Donatur
*   Register baru di web -> Pilih Role **Donatur**.
*   Gunakan Private Key akun ke-3 dari Ganache.
*   *Fungsi*: Donasi (Pastikan saldo cukup sekitar 0.0002 ETH untuk Gas Fee).

---

## ⚠️ Troubleshooting

| Masalah | Solusi |
| :--- | :--- |
| **Connection Refused** | Buka Ganache → Pastikan Port 7545 → Restart app.py |
| **Transaksi Gagal** | Pastikan saldo akun cukup untuk Donasi + Gas Fee. |
| **Email Gagal Kirim** | Cek config `app.py`. Jika belum diset, cek Terminal (Mock Mode). |
| **Loading Lama di HP** | Cek koneksi WiFi. Sistem sudah menggunakan Cache 5 detik. |
| **Signature Failed** | Hapus `instance/users.db` dan restart Flask jika database tidak sinkron. |

---

## 📜 Referensi Akademik
* Kharisma et al. (2025) — Transparansi Blockchain
* Kartiko et al. (2023) — Efisiensi Gas Fee (Hybrid Architecture)
* Indra S B et al. (2024) — Verifikasi Identitas Kreator

---
© 2025 **DonasiKuy Foundation**. Transparency is our currency.
