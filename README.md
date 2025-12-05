# 🪙 DonasiKuy - Decentralized Crowdfunding Platform

### Final Project: Teknologi Blockchain & Distributed Ledger

DonasiKuy adalah platform donasi transparan berbasis Ethereum Blockchain yang menggabungkan kemudahan Web 2.0 dengan keamanan Web 3.0 (Hybrid Architecture).

Proyek ini bertujuan untuk mengatasi krisis kepercayaan dalam donasi online dengan mencatat setiap transaksi secara kekal (immutable) di blockchain, sambil menyediakan antarmuka modern yang ramah pengguna.

---

## ✨ Fitur Unggulan (New!)

* 🌍 **Public Blockchain Explorer** — Visualisasi rantai blok dan transaksi donasi secara live & transparan.
* 🛡️ **Admin Security Dashboard (SIEM)** — Pemantauan keamanan, deteksi serangan, analisis trafik, dan pemantauan IP.
* 📰 **Live Humanitarian News** — Integrasi berita bencana real-time via RSS Feed.
* 🔔 **Real-Time Activity Toast** — Notifikasi aktivitas donasi otomatis tanpa perlu refresh.
* ⏳ **Smart Countdown** — Penghitung mundur otomatis untuk tenggat kampanye.

---

## 👥 Tim Pengembang

| Peran              | Nama                         | Fokus Tugas                                        |
| ------------------ | ---------------------------- | -------------------------------------------------- |
| Analis & Pemodel   | Masdani Ilman Putra Karmawan | Use Case, Flow Sistem, Requirement Analysis        |
| Arsitek & Engineer | Nur Akhmad Van Jouvi         | Smart Contract, Flask Backend, Ganache Setup, SIEM |
| QA & Security      | Fathur Rahman                | Security Testing, Postman API Test, Bug Hunting    |

---

## 🛠️ Teknologi (Tech Stack)

* **Core Blockchain**: Ethereum (Simulasi via Ganache)
* **Smart Contract**: Solidity (.sol), Truffle Framework
* **Backend**: Python Flask
* **Frontend**: Bootstrap 5, Jinja2, SweetAlert2, Chart.js
* **Database**: SQLite (untuk data user & meta-data kampanye)
* **Connector**: Web3.py (Jembatan Python ↔ Blockchain)

---

## 🚀 Panduan Instalasi & Menjalankan (Lengkap)

Ikuti langkah berikut agar proyek berjalan lancar.

### 1. Persiapan Software (Prerequisites)

Pastikan sudah terinstall:

* Node.js
* Python 3.8+
* Ganache GUI
* Git

### 2. Setup Blockchain (Ganache)

1. Buka Ganache
2. Klik **New Workspace (Ethereum)**
3. Isi nama workspace → *DonasiKuy_Dev*
4. Masuk tab **Server**, pastikan Port = **7545**
5. Klik **Save Workspace**
6. Biarkan Ganache tetap menyala

### 3. Deploy Smart Contract

Masuk ke folder `donation_truffle`:

```
npm install -g truffle
truffle migrate --reset
```

Setelah selesai, terminal akan menampilkan **Contract Address** (contoh: `0x123...`).

Update file:

```
backend_python/contract_data.py
```

Isi variabel `contract_address` dengan alamat terbaru.

### 4. Setup Backend (Python Flask)

Masuk ke folder backend:

```
cd backend_python
```

Buat virtual environment:

```
Windows:
python -m venv venv
venv\Scripts\activate

Mac/Linux:
python3 -m venv venv
source venv/bin/activate
```

Install library:

```
pip install Flask web3 feedparser
```

Atau:

```
pip install -r requirements.txt
```

Jalankan aplikasi:

```
python app.py
```

### 5. Akses Platform

Akses melalui browser:

```
http://127.0.0.1:5000
```

---

## 🔑 Akun Demo

Gunakan data ini untuk demo tanpa registrasi ulang.

### 1. Super Admin

* Email: **[admin@donasi.com](mailto:admin@donasi.com)**
* Password: **admin123**
* Fitur: Dashboard SIEM, Approve/Reject Kampanye, Hapus User

### 2. Akun Kreator

Cara:

1. Register di web
2. Pilih role **Kreator**
3. Dari Ganache ambil akun ke-2 (Index 1)
4. Klik icon kunci → copy Private Key

### 3. Akun Donatur

Cara:

1. Register di web
2. Pilih role **Donatur**
3. Dari Ganache ambil akun ke-3 (Index 2)
4. Copy Private Key

---

## ⚠️ Troubleshooting (Solusi Masalah Umum)

| Masalah                       | Penyebab                     | Solusi                                                          |
| ----------------------------- | ---------------------------- | --------------------------------------------------------------- |
| Connection Refused            | Ganache mati / Port salah    | Buka Ganache → Pastikan Port 7545 → Restart app.py              |
| Contract Logic Error / Revert | Saldo kurang / akun salah    | Pastikan akun memiliki 100 ETH default dari Ganache             |
| Signature Verification Failed | Database tidak sinkron       | Hapus `backend_python/instance/users.db` → jalankan ulang Flask |
| Notifikasi Tidak Muncul       | Cache browser                | Hard Refresh (Ctrl + F5) atau buka mode Incognito               |
| TVL/Saldo Aneh                | Data lama tersisa di Ganache | Klik **Restart Workspace** → jalankan `truffle migrate --reset` |

---

## 📜 Referensi Akademik

* Zheng et al. (2020) — Blockchain-Based Decentralized Application Architecture
* Kartiko et al. (2023) — Efisiensi Gas Fee Ethereum
* Indra S B et al. (2024) — Verifikasi Identitas Kreator

---

© 2025 Kelompok Blockchain DonasiKuy Informatika
