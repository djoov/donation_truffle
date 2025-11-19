import json

CONTRACT_ADDRESS = "0xCE27ba588EEc60774C9aD10bBB2C780d73492CDA"

ABI = [
    {
      "inputs": [
        {
          "internalType": "string",
          "name": "_title",
          "type": "string"
        },
        {
          "internalType": "uint256",
          "name": "_durationInMinutes",
          "type": "uint256"
        }
      ],
      "name": "createCampaign",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "_campaignId",
          "type": "uint256"
        }
      ],
      "name": "donateToCampaign",
      "outputs": [],
      "stateMutability": "payable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "_campaignId",
          "type": "uint256"
        }
      ],
      "name": "withdrawFunds",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "campaignCount",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "name": "campaigns",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "id",
          "type": "uint256"
        },
        {
          "internalType": "address",
          "name": "creator",
          "type": "address"
        },
        {
          "internalType": "string",
          "name": "title",
          "type": "string"
        },
        {
          "internalType": "uint256",
          "name": "deadline",
          "type": "uint256"
        },
        {
          "internalType": "uint256",
          "name": "totalDonations",
          "type": "uint256"
        },
        {
          "internalType": "bool",
          "name": "withdrawn",
          "type": "bool"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": True,
          "internalType": "uint256",
          "name": "campaignId",
          "type": "uint256"
        },
        {
          "indexed": False,
          "internalType": "string",
          "name": "title",
          "type": "string"
        },
        {
          "indexed": False,
          "internalType": "address",
          "name": "creator",
          "type": "address"
        }
      ],
      "name": "CampaignCreated",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": True,
          "internalType": "uint256",
          "name": "campaignId",
          "type": "uint256"
        },
        {
          "indexed": False,
          "internalType": "address",
          "name": "donor",
          "type": "address"
        },
        {
          "indexed": False,
          "internalType": "uint256",
          "name": "amount",
          "type": "uint256"
        }
      ],
      "name": "DonationReceived",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": True,
          "internalType": "uint256",
          "name": "campaignId",
          "type": "uint256"
        },
        {
          "indexed": False,
          "internalType": "uint256",
          "name": "totalAmount",
          "type": "uint256"
        },
        {
          "indexed": False,
          "internalType": "address",
          "name": "creator",
          "type": "address"
        }
      ],
      "name": "FundsWithdrawn",
      "type": "event"
    }
]
