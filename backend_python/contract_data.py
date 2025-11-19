import json
from web3 import Web3

GANACHE_URL = "http://127.0.0.1:7545"

web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
assert web3.is_connected(), "❌ Ganache tidak terhubung!"

def load_abi():
    with open("build/contracts/DonationPlatform.json") as f:
        data = json.load(f)
        return data["abi"]

def load_address():
    with open("build/contracts/DonationPlatform.json") as f:
        data = json.load(f)
        # 5777 = jaringan Ganache GUI
        return data["networks"]["5777"]["address"]

ABI = load_abi()
CONTRACT_ADDRESS = load_address()

contract = web3.eth.contract(
    address=CONTRACT_ADDRESS,
    abi=ABI
)
