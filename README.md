# 🚀 Decentralized Donation Platform

**Blockchain + Flask + SQLite + Smart Contract Ethereum**

---

## 📌 Deskripsi Proyek

Decentralized Donation Platform adalah aplikasi donasi berbasis blockchain yang transparan dan aman. Dana donasi dikirim langsung ke kreator kampanye tanpa perantara, dan prosesnya tercatat permanen di blockchain melalui smart contract Ethereum.

Aplikasi ini terdiri dari:

* Backend: Flask + Web3.py
* On-Chain: Smart Contract Solidity
* Off-Chain: SQLite
* Blockchain Network: Ganache
* Deployment: Truffle Framework

---

## 📂 Struktur Folder Proyek

```
donation_truffle/
│
├── backend_python/
│   ├── app.py
│   ├── contract_data.py
│   ├── db.py
│   ├── database.db
│   ├── templates/
│   └── static/
│
├── contracts/
│   └── DonationPlatform.sol
│
├── migrations/
│   └── 2_deploy_contracts.js
│
├── build/
│   └── contracts/
│       └── DonationPlatform.json
│
├── truffle-config.js
└── README.md
```

---

## 🔧 Teknologi Utama

### On-Chain

* Solidity
* Truffle
* Ganache

### Backend

* Flask
* Python 3.10+
* Web3.py
* SQLite

### Frontend

* Flask + Jinja2
* Bootstrap 5

---

## 🧠 Fitur Utama

### Donatur

* Melihat daftar kampanye
* Melihat detail kampanye
* Donasi ETH ke kampanye

### Kreator

* Membuat kampanye baru
* Menarik dana setelah deadline

### Admin

* Approve kampanye
* Reject kampanye
* Disable kampanye

### Smart Contract

* createCampaign
* approveCampaign
* rejectCampaign
* disableCampaign
* donateToCampaign
* withdrawFunds
* getCampaign
* getCampaignCount

### SQLite

* User management
* Role (admin/creator/user)
* Wallet mapping

---

## ⚙️ Cara Install dan Menjalankan

### 1. Clone Repo

```
git clone https://github.com/djoov/donation_truffle.git
cd donation_truffle
```

### 2. Setup Python

```
conda create -n donation-backend python=3.10
conda activate donation-backend
pip install flask web3 python-dotenv
```

### 3. Setup Database

```
python -c "from db import init_db; init_db()"
```

### 4. Jalankan Ganache

RPC: [http://127.0.0.1:7545](http://127.0.0.1:7545)

### 5. Deploy Smart Contract

```
truffle compile
truffle migrate --reset
```

### 6. Update contract_data.py

Isi:

* ABI
* Contract Address

### 7. Jalankan Flask

```
cd backend_python
python app.py
```

Akses di browser: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

---

## 🧪 Contoh API (Postman)

**GET campaigns:**

```
GET http://127.0.0.1:5000/campaigns
```

**POST donasi:**

```
POST /donate
{
  "campaign_id": 0,
  "amount": 0.01,
  "from": "0x123...",
  "private_key": "YOUR_KEY"
}
```

---

## 📄 UML (Use Case)

Kode lengkap PlantUML tersedia di dokumentasi utama.

---

## 🤝 Kontribusi

1. Fork repository
2. Buat branch baru:

```
git checkout -b fitur-baru
```

3. Commit:

```
git commit -m "fitur baru"
```

4. Pull request

---

## 📄 License

MIT License

---

## 🙋 Tim Pengembang

* Nur Akhmad Van Jouvi
* Masdani Ilman
* Fathur Rahman


