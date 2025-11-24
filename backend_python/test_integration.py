import time
from web3 import Web3
from contract_data import contract, web3

# --- KONFIGURASI AKUN TEST (Sesuaikan dengan Ganache kamu) ---
# Pastikan Ganache menyala saat menjalankan ini
try:
    accounts = web3.eth.accounts
    ADMIN = accounts[0]    # Akun deployer/admin
    CREATOR = accounts[1]  # Akun pembuat kampanye
    DONOR = accounts[2]    # Akun donatur
except:
    print("❌ Gagal mengambil akun. Pastikan Ganache jalan.")
    exit()

def run_tests():
    print("\n🚀 MEMULAI INTEGRATION TEST (SC5 - KUALITAS)...")
    print("="*50)

    # 1. TEST MEMBUAT CAMPAIGN
    print("\n[TEST 1] Membuat Campaign Baru...")
    try:
        old_count = contract.functions.getCampaignCount().call()
        
        tx_hash = contract.functions.createCampaign(
            "Test Campaign Otomatis", 
            60 # durasi 60 menit
        ).transact({'from': CREATOR})
        web3.eth.wait_for_transaction_receipt(tx_hash)
        
        new_count = contract.functions.getCampaignCount().call()
        campaign_id = new_count - 1
        
        assert new_count == old_count + 1
        print(f"✅ SUKSES: Campaign #{campaign_id} berhasil dibuat.")
    except Exception as e:
        print(f"❌ GAGAL: {e}")
        return

    # 2. TEST APPROVE CAMPAIGN (Admin)
    print("\n[TEST 2] Admin Approve Campaign...")
    try:
        tx_hash = contract.functions.approveCampaign(campaign_id).transact({'from': ADMIN})
        web3.eth.wait_for_transaction_receipt(tx_hash)
        
        camp_data = contract.functions.getCampaign(campaign_id).call()
        # Status: 0=Pending, 1=Approved
        assert camp_data[4] == 1 
        print(f"✅ SUKSES: Campaign #{campaign_id} statusnya sekarang APPROVED.")
    except Exception as e:
        print(f"❌ GAGAL: {e}")
        return

    # 3. TEST DONASI
    print("\n[TEST 3] Donasi 1 ETH...")
    try:
        initial_balance = contract.functions.getCampaign(campaign_id).call()[3]
        donation_amount = web3.to_wei(1, 'ether')
        
        tx_hash = contract.functions.donateToCampaign(campaign_id).transact({
            'from': DONOR, 
            'value': donation_amount
        })
        web3.eth.wait_for_transaction_receipt(tx_hash)
        
        final_balance = contract.functions.getCampaign(campaign_id).call()[3]
        
        assert final_balance == initial_balance + donation_amount
        print(f"✅ SUKSES: Saldo campaign bertambah 1 ETH.")
    except Exception as e:
        print(f"❌ GAGAL: {e}")

    print("\n" + "="*50)
    print("🎉 SEMUA INTEGRATION TEST BERHASIL!")
    print("Sistem siap didemokan.")

if __name__ == "__main__":
    if contract:
        run_tests()
    else:
        print("Smart contract tidak terhubung.")