import json
import os
from web3 import Web3

# --- KONFIGURASI PENTING ---
# Cek di Aplikasi Ganache bagian atas "RPC SERVER"
# Jika di aplikasi tertulis 8545, ganti angka di bawah jadi 8545
GANACHE_URL = "http://127.0.0.1:7545" 

# Setup Koneksi Web3
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))

def get_contract_info():
    print("-" * 50)
    print(f"🔍 DEBUGGING SMART CONTRACT CONNECTION ke {GANACHE_URL}...")
    
    # 1. Cek Koneksi Ganache
    if not web3.is_connected():
        print("❌ GAGAL: Tidak bisa terhubung ke Ganache.")
        print(f"   Pastikan Ganache menyala dan RPC SERVER di aplikasi sama dengan {GANACHE_URL}")
        return None, None
    else:
        print(f"✅ Ganache Terhubung. Network ID: {web3.eth.chain_id}")

    # 2. Mencari File JSON (Logika Path Absolut yang Lebih Kuat)
    # Mencari folder 'build' di folder utama (donation_truffle)
    # Struktur: donation_truffle/build/contracts/DonationPlatform.json
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) # Folder backend_python
    root_dir = os.path.dirname(current_dir) # Folder donation_truffle
    json_path = os.path.join(root_dir, 'build', 'contracts', 'DonationPlatform.json')
    
    print(f"📂 Mencari file JSON di: {json_path}")

    if not os.path.exists(json_path):
        print("❌ GAGAL: File JSON tidak ditemukan!")
        print("👉 SOLUSI: Buka terminal baru di folder 'donation_truffle', lalu ketik:")
        print("   truffle migrate --reset")
        return None, None
    
    print("✅ File JSON ditemukan.")

    # 3. Membaca JSON & Mencocokkan Network
    try:
        with open(json_path) as f:
            contract_json = json.load(f)
            
        abi = contract_json['abi']
        networks = contract_json['networks']
        chain_id = str(web3.eth.chain_id)
        
        if chain_id in networks:
            address = networks[chain_id]['address']
            print(f"✅ MATCH! Kontrak ditemukan di address: {address}")
            return address, abi
        else:
            # Fallback: Ambil network terakhir yang tersedia
            if len(networks) > 0:
                latest_net = list(networks.keys())[-1]
                address = networks[latest_net]['address']
                print(f"⚠️  Network ID {chain_id} tidak ada di JSON.")
                print(f"⚠️  Menggunakan fallback network {latest_net} -> Address: {address}")
                return address, abi
            else:
                print("❌ GAGAL: JSON ada, tapi 'networks' kosong. Belum dideploy!")
                return None, None

    except Exception as e:
        print(f"❌ ERROR SYSTEM: {str(e)}")
        return None, None
    finally:
        print("-" * 50)

# Inisialisasi Global Variable
address, abi = get_contract_info()

if address and abi:
    contract = web3.eth.contract(address=address, abi=abi)
else:
    contract = None
    print("⚠️  PERINGATAN: Aplikasi berjalan TANPA koneksi Smart Contract.")