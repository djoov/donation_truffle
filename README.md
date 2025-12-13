# 🪙 DonasiKuy - Decentralized Crowdfunding Platform
### Final Project: Teknologi Blockchain & Distributed Ledger — Semester 5

![Badge](https://img.shields.io/badge/Blockchain-Ethereum-3C3C3D?style=for-the-badge&logo=ethereum)
![Badge](https://img.shields.io/badge/Backend-Flask-000000?style=for-the-badge&logo=flask)
![Badge](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

Platform donasi transparan berbasis Ethereum Blockchain dengan arsitektur Hybrid (Web2 + Web3), menjamin transparansi 100% dan keamanan transaksi.

---

## ✨ Fitur Unggulan (New Features)

### 🛡️ 1. Security & Validation (Anti-Fail)
*   **Strict Balance Check**: Sistem menolak transaksi donasi jika `Saldo < (Donasi + Gas Fee)`.
*   **Dynamic Gas Estimation**: Menggunakan `web3.eth.estimate_gas` untuk kalkulasi biaya transaksi yang akurat, mencegah kegagalan transaksi di jaringan.
*   **Security Logging**: Mencatat aktivitas mencurigakan (Saldo tidak cukup, Percobaan akses admin) ke database log.

### 🔔 2. User Engagement System
*   **Welcome Email**: Sapaan hangat otomatis via Email (SMTP Gmail) saat registrasi berhasil.
*   **SweetAlert Notifications**: Notifikasi popup interaktif (bukan sekadar teks) untuk Sukses/Error.
*   **Live Activity Toast**: Notifikasi realtime (pojok kanan bawah) setiap kali ada user lain yang berdonasi.

### ⚡ 3. Performance Optimization
*   **Smart Caching**: Menyimpan data blockchain (Block Height, Gas Price) di memori selama 5 detik untuk akses super cepat via WiFi / Mobile.
*   **Responsive UI**: Tampilan dioptimalkan untuk Desktop & Mobile (Footer ringkas, Form readable).

---

## 👥 Tim Pengembang

| Peran              | Nama                         | Fokus Tugas                                     |
| ------------------ | ---------------------------- | ----------------------------------------------- |
| Analis & Pemodel   | **Masdani Ilman P. K.**      | Use Case, Flow Sistem, Requirement Analysis     |
| Arsitek & Engineer | **Nur Akhmad Van Jouvi**     | Smart Contract, Flask Backend, Security Logic   |
| QA & Security      | **Fathur Rahman**            | Security Testing, Bug Hunting, Validation Test  |

---

## 🚀 Cara Menjalankan Project

### 1. Persiapan (Prerequisites)
Pastikan terinstall: `Node.js`, `Python 3.x`, dan `Ganache GUI`.

### 2. Setup Ganache (Blockchain Lokal)
1.  Buka Ganache, pilih **New Workspace**.
2.  Set Port Number = **7545**.
3.  Simpan dan biarkan menyala.

### 3. Deploy Smart Contract
Di terminal root folder (`donation_truffle`):
```bash
npm install -g truffle
truffle migrate --reset
```
*Pastikan file `backend_python/contract_data.py` telah diperbarui dengan alamat kontrak baru jika migrasi ulang.*

### 4. Setup Backend (Python)
Masuk folder backend:
```bash
cd backend_python
python -m venv venv
# Windows:
venv\Scripts\activate
# Install Library:
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
Akses di Browser:
*   Localhost: `http://127.0.0.1:5000`
*   Dari HP (Satu WiFi): `http://<IP_LAPTOP_ANDA>:5000`

---

## 🔑 Akun Demo (Ganache)
Gunakan Private Key dari Ganache untuk login/transaksi.

| Peran | Email | Password | Fungsi |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@donasi.com` | `admin123` | Approve Kampanye, Hapus User |
| **Kreator** | (Register Baru) | - | Buat Galang Dana, Tarik Dana |
| **Donatur** | (Register Baru) | - | Donasi, Lihat History |

---

## ⚠️ Troubleshooting

1.  **Email Error/Gagal Kirim**:
    *   Pastikan Anda menggunakan **App Password** Gmail, bukan password login biasa.
    *   Jika belum diset, email hanya akan dicetak di Terminal (Mock Mode).

2.  **Transaksi Gagal / Saldo Kurang**:
    *   Pastikan saldo akun Ganache cukup untuk **Donasi + Gas Fee** (sekitar 0.0002 ETH).

3.  **Loading Lama di HP**:
    *   Sistem sudah menggunakan Caching (5 detik). Jika masih lambat, cek koneksi WiFi Anda (Ganache butuh latensi rendah).

---
© 2025 **DonasiKuy Foundation**. Transparency is our currency.
