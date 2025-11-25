# 🪙 DonasiKuy - Decentralized Crowdfunding Platform

### Final Project: Teknologi Blockchain & Distributed Ledger — Semester 5 - Teknik Informatika

Platform donasi transparan berbasis Ethereum Blockchain dengan arsitektur Hybrid (Flask + Web3).

---

## 👥 Tim Pengembang

| Peran              | Nama                         | Fokus Tugas                                     |
| ------------------ | ---------------------------- | ----------------------------------------------- |
| Analis & Pemodel   | Masdani Ilman Putra Karmawan | Use Case, Flow Sistem, Requirement Analysis     |
| Arsitek & Engineer | Nur Akhmad Van Jouvi         | Smart Contract, Flask Backend, Ganache Setup    |
| QA & Security      | Fathur Rahman                | Security Testing, Postman API Test, Bug Hunting |

---

## 🛠️ Teknologi yang Digunakan (Tech Stack)

* **Blockchain**: Ethereum (Simulasi Lokal via Ganache)
* **Smart Contract**: Solidity (.sol), Truffle Framework
* **Backend**: Python Flask
* **Frontend**: HTML5, CSS3 (Bootstrap 5), Jinja2 Template
* **Database**: SQLite (untuk data user & detail kampanye off-chain)
* **Library**: Web3.py (Jembatan Python ke Blockchain)

---

## 🚀 Cara Menjalankan Project (Langkah demi Langkah)

### 1. Persiapan Awal (Prerequisites)

Pastikan sudah terinstall:

* Node.js (untuk Truffle)
* Python 3.x (untuk Backend)
* Ganache GUI

### 2. Setup Blockchain (Ganache)

1. Buka Ganache
2. Klik **New Workspace**
3. Beri nama workspace (misal: DonasiKuy_Dev)
4. Pastikan Port Number = **7545**
5. Klik **Save Workspace**

> Catatan: Biarkan Ganache tetap menyala selama menjalankan aplikasi.

### 3. Setup Smart Contract

Buka terminal di folder utama project (`donation_truffle`):

```
npm install -g truffle
truffle migrate --reset
```

> Jika sukses, muncul alamat kontrak (contoh: 0x123...). Biarkan terminal tetap terbuka.

### 4. Setup Backend (Python)

Masuk folder backend:

```
cd backend_python
python -m venv venv
```

Aktifkan virtual environment:

```
Windows: venv\Scripts\activate
Mac/Linux: source venv/bin/activate
```

Install library:

```
pip install -r requirements.txt
```

Isi file requirements.txt jika belum ada:

```
Flask
web3
```

### 5. Menjalankan Aplikasi Web

```
python app.py
```

Akses di browser: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Panduan Akun (PENTING UNTUK DEMO)

Menggunakan akun Ganache sebagai dompet.

Cara mendapatkan akun:

* Buka Ganache → lihat Address → klik **Show Key** untuk Private Key

### 👮‍♂️ A. Login Admin

* Email: **[admin@donasi.com](mailto:admin@donasi.com)**
* Password: **admin123**
  Tugas: approve kampanye baru.

### 📢 B. Daftar Kreator

* Pilih Role: Kreator
* Copy Address & Private Key dari Ganache (akun ke-2)
  Tugas: buat kampanye & withdraw dana.

### 💙 C. Daftar Donatur

* Pilih Role: Donatur
* Copy Address & Private Key dari Ganache (akun ke-3)
  Tugas: donasi ke kampanye aktif.

---

## ⚠️ Troubleshooting (Solusi Masalah Umum)

| Masalah                       | Penyebab                                   | Solusi                                                                   |
| ----------------------------- | ------------------------------------------ | ------------------------------------------------------------------------ |
| Connection Refused            | Ganache mati / port beda                   | Pastikan Ganache menyala & port = 7545 (atau ubah di `contract_data.py`) |
| Campaign has ended            | Durasi kampanye habis                      | Buat kampanye baru (misal 30 hari)                                       |
| Signature Verification Failed | Database tidak sinkron dengan Ganache baru | Hapus `backend_python/instance/users.db`, jalankan ulang Flask           |

---

## 📜 Referensi Akademik

* Khokale et al. (2025) — Transparansi Blockchain
* Kartiko et al. (2023) — Efisiensi Gas Fee (Hybrid Architecture)
* Indra S B et al. (2024) — Verifikasi Identitas Kreator

---

© 2025 Kelompok Blockchain DonasiKuy Informatika
