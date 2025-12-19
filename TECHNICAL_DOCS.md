# 📘 Dokumentasi Teknis: DonasiKuy Platform

## 1. Deskripsi Proyek
**DonasiKuy** adalah platform *Crowdfunding* (penggalangan dana) terdesentralisasi yang dibangun di atas teknologi **Blockchain Ethereum**. Tujuan utamanya adalah menyelesaikan masalah klasik dalam donasi konvensional: **Kurangnya Transparansi**. Dengan mencatat setiap transaksi donasi dan penarikan dana ke dalam Smart Contract yang *immutable* (kekal), DonasiKuy menjamin bahwa dana publik dapat diaudit oleh siapa saja kapan saja.

Platform ini menggunakan pendekatan **Hybrid**, menggabungkan kemudahan antarmuka Web 2.0 (Flask/Bootstrap) dengan keamanan pencatatan Web 3.0 (Smart Contract).

---

## 2. Fitur & Fungsionalitas

### 🔸 Fitur Utama (User Public)
1.  **Explorasi Kampanye:** Halaman beranda dengan visual modern (Mesh Gradient) menampilkan daftar kampanye yang sedang aktif, lengkap dengan *Progress Bar* real-time.
2.  **Sistem Donasi Blockchain:**
    *   Pengguna dapat berdonasi menggunakan mata uang Ether (ETH).
    *   Setiap donasi menghasilkan **Transaction Hash** dan **Nonce** sebagai bukti digital yang valid.
    *   Pencegahan donasi negatif dan validasi saldo dompet sebelum transaksi.
3.  **Transparansi Penuh (Campaign Detail):**
    *   Riwayat donasi ditampilkan secara terbuka (Nama, Jumlah, Waktu, Pesan, Tx Hash).
    *   Tab "Kabar Terbaru" update langsung dari pemilik kampanye.
    *   Status penarikan dana (Withdrawal) terpampang jelas jika dana sudah diambil.
4.  **Autentikasi Aman:**
    *   Login/Register dengan validasi input ketat (Email Regex, Username Regex).
    *   Fitur **Forgot Password** aman menggunakan Token sementara (15 menit).
    *   Rate Limiting untuk mencegah *Brute Force Attack*.

### 🔸 Fitur Kreator (Penggalang Dana)
1.  **Pengajuan Kampanye:** Form pembuatan kampanye dengan upload gambar dan target dana.
2.  **Manajemen Kampanye:**
    *   Posting "Kabar Terbaru" + Bukti Foto untuk update ke donatur.
    *   Tombol **Withdraw Funds** yang hanya aktif jika kampanye memiliki saldo.
    *   Notifikasi email otomatis ke donatur saat ada update/penarikan.

### 🔸 Fitur Administrator (Back Office)
1.  **Dashboard Premium:** Tampilan statistik *Traffic*, status jaringan Blockchain, dan waktu server.
2.  **Moderasi Konten:** Menyetujui (Approve) atau Menolak (Reject) kampanye baru.
3.  **Security Intelligence Center:**
    *   Log aktivitas keamanan real-time (Login gagal, SQL Injection attempt, dll).
    *   Fitur **Export CSV** untuk audit data keamanan.
4.  **Blockchain Audit Log:** Tabel sinkronisasi otomatis yang mencatat semua *Event* dari Smart Contract.

---

## 3. Analisis Kelebihan & Kekurangan

### ✅ Kelebihan (Pros)
1.  **Integritas Data Tinggi:** Karena data transaksi disimpan di Blockchain, mutasi dana tidak bisa dimanipulasi atau dihapus oleh admin sekalipun.
2.  **Transparansi Real-time:** Donatur tidak perlu menunggu laporan tahunan. Setiap sen yang masuk dan keluar bisa dilacak detik itu juga melalui *Transaction Hash*.
3.  **Keamanan Berlapis:** Selain keamanan blockchain, aplikasi dilengkapi WAF sederhana (Filter SQLi/XSS), Rate Limiting, dan Token-based Reset Password.
4.  **User Experience (UX) Modern:** Antarmuka menggunakan desain *Glassmorphism* dan animasi halus yang jauh lebih menarik dibanding platform donasi kaku pada umumnya.
5.  **Notifikasi Proaktif:** Sistem email otomatis menjaga donatur tetap terhubung dengan perkembangan kampanye (Engagement).

### ❌ Kekurangan (Cons)
1.  **Keterbatasan "Server-Side Wallet":** Saat ini private key pengguna disimpan di server (model *Custodial*). Ini membuat user harus "percaya" pada keamanan server. Idealnya menggunakan *Non-Custodial* (MetaMask langsung di browser klik).
2.  **Biaya Gas (Gas Fee):** Setiap donasi memerlukan biaya jaringan Ethereum (Gas). Jika jaringan sibuk, biaya ini bisa mahal (walaupun di Testnet Ganache gratis).
3.  **Penyimpanan Gambar Terpusat:** Gambar masih disimpan di server lokal (`static/uploads`). Jika server down, gambar hilang. Seharusnya menggunakan IPFS (Decentralized Storage).
4.  **Keamanan Password Database:** Password user saat ini masih *Plain Text* di Database (belum di-hash), yang merupakan risiko keamanan jika database bocor.

---

## 4. Masalah & Tantangan Selama Pengembangan

Dalam perjalanan membangun DonasiKuy, tim menghadapi (dan menyelesaikan) beberapa tantangan teknis utama:

1.  **Konkurensi Transaksi (Nonce Issue):**
    *   *Masalah:* Saat banyak donasi masuk bersamaan, transaksi sering gagal karena berebut "Nomor Antrian" (Nonce) yang sama.
    *   *Solusi:* Mengubah logika Web3 untuk selalu meminta `nonce='pending'`, memastikan setiap transaksi mendapat nomor antrian unik berikutnya.

2.  **Responsivitas Admin Sidebar:**
    *   *Masalah:* Sidebar admin terlihat bagus di Desktop tapi terpotong dan tidak bisa di-scroll di Mobile.
    *   *Solusi:* Mengimplementasikan CSS `@media query` khusus untuk mengubah layout sidebar menjadi vertikal dan *auto-height* pada layar kecil.

3.  **Sinkronisasi Tab Admin (Bug Tampilan):**
    *   *Masalah:* Menekan menu "System" tidak mematikan menu "Main Menu", membuat konten bertumpuk.
    *   *Solusi:* Menambahkan Script JS kustom untuk memaksa "Single Active Tab" di seluruh grup navigasi.

4.  **Floating Point Precision (Uang Blockchain):**
    *   *Masalah:* Menggunakan tipe data `float` biasa menyebabkan ketidakakuratan perhitungan dana crypto (masalah koma).
    *   *Solusi:* Mulai beralih menggunakan konversi `Wei` (satuan terkecil Ether) untuk perhitungan di backend.

---

## 6. Spesifikasi Database (Schema)
Berikut adalah struktur tabel SQLite (`users.db`) yang digunakan untuk menyimpan data *off-chain*:

| Tabel | Deskripsi | Kolom Utama |
| :--- | :--- | :--- |
| `users` | Data akun pengguna | `id`, `username`, `email`, `password`, `role`, `wallet_address`, `private_key` |
| `campaign_details` | Detail tambahan kampanye | `blockchain_id`, `category`, `usage_plan`, `social_link` |
| `campaign_updates` | Berita/Update dari kreator | `blockchain_id`, `title`, `content`, `image` |
| `donations` | Riwayat donasi (Sinkronisasi) | `blockchain_id`, `donor_name`, `amount`, `tx_hash`, `nonce` |
| `security_logs` | Log keamanan sistem | `timestamp`, `ip_address`, `action`, `status`, `description` |

## 7. Smart Contract Interface (Solidity)
Fungsi-fungsi utama yang ada di dalam kontrak `DonationPlatform.sol`:

*   `createCampaign(...)`: Membuat kampanye baru.
*   `donateToCampaign(uint _id)`: Mengirim ETH ke kampanye tertentu (Payable).
*   `withdrawFunds(uint _id)`: Menarik dana terkumpul (Hanya kreator, ada batasan waktu).
*   `getCampaigns()`: Mengambil daftar semua kampanye.

---

## 8. Panduan Instalasi (Development)
1.  **Clone Repository** code project.
2.  **Setup Ganache**: Jalankan Ganache pada port `7545`.
3.  **Deploy Contract**: Jalankan `truffle migrate --reset`.
4.  **Backend Setup**:
    ```bash
    cd backend_python
    pip install -r requirements.txt
    python app.py
    ```
5.  **Akses**: Buka `http://localhost:5000`.
