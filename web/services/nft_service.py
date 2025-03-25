# import json
# import os
# import requests
# from datetime import datetime
# from web3 import Web3
# from eth_account import Account
# from django.conf import settings
# from django.utils import timezone
# from web.models import NFTBadge, Achievement
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # NFT.Storage API Key (Ensure it's set in the .env file)
# NFT_STORAGE_API_KEY = os.getenv("NFT_STORAGE_API_KEY", "")
# NFT_STORAGE_URL = "https://api.nft.storage/upload"

# # Use WEB3_URL_PROVIDER for Polygon RPC URL
# WEB3_URL_PROVIDER = os.getenv("WEB3_PROVIDER_URL", "").strip()
# if not WEB3_URL_PROVIDER:
#     raise ValueError("❌ WEB3_PROVIDER_URL is missing in environment variables")

# # Default NFT Badge Image
# DEFAULT_BADGE_URL = f"https://{settings.SITE_DOMAIN}/static/images/logo.png"

# class NFTBadgeService:
#     def __init__(self):
#         self.web3 = Web3(Web3.HTTPProvider(WEB3_URL_PROVIDER))

#         if not self.web3.is_connected():
#             raise ConnectionError("❌ Failed to connect to blockchain")

#         print("✅ Connected to Polygon Amoy Testnet")

#         # Load contract address and ABI
#         self.contract_address = os.getenv("NFT_CONTRACT_ADDRESS", "").strip()
#         if not self.contract_address:
#             raise ValueError("❌ NFT_CONTRACT_ADDRESS is missing in environment variables")

#         self.contract_address = self.web3.to_checksum_address(self.contract_address)
#         print(f"📜 Smart Contract Address: {self.contract_address}")

#         self.contract_abi = self._load_contract_abi()
#         self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.contract_abi)

#     def _load_contract_abi(self):
#         """Load contract ABI from file"""
#         try:
#             with open("web/static/contracts/nft_abi.json", "r") as f:
#                 return json.load(f)
#         except FileNotFoundError:
#             raise FileNotFoundError("❌ ABI file not found!")

#     def upload_to_ipfs(self, file_path):
#         """Uploads a file to IPFS using NFT.Storage"""
#         if not NFT_STORAGE_API_KEY:
#             raise ValueError("❌ NFT.Storage API key is missing!")

#         headers = {"Authorization": f"Bearer {NFT_STORAGE_API_KEY}"}
#         with open(file_path, "rb") as file:
#             response = requests.post(NFT_STORAGE_URL, files={"file": file}, headers=headers)

#         if response.status_code == 200:
#             cid = response.json()["value"]["cid"]
#             print(f"🚀 IPFS Upload Success! CID: {cid}")
#             return f"ipfs://{cid}"  # Return IPFS URI
#         else:
#             print(f"❌ IPFS Upload Failed: {response.text}")
#             raise ValueError(f"IPFS Upload Failed: {response.text}")

#     def create_metadata(self, achievement):
#         """Creates and uploads metadata JSON for the NFT badge to IPFS"""
#         image_path = f"static/images/badges/{achievement.achievement_type}.png"
#         if os.path.exists(image_path):
#             image_ipfs_uri = self.upload_to_ipfs(image_path)
#         else:
#             image_ipfs_uri = DEFAULT_BADGE_URL  # Fallback image

#         metadata = {
#             "name": achievement.title,
#             "description": achievement.description,
#             "attributes": [
#                 {"trait_type": "Achievement Type", "value": achievement.get_achievement_type_display()},
#                 {"trait_type": "Course", "value": achievement.course.title if achievement.course else "General"},
#                 {"trait_type": "Awarded Date", "value": achievement.awarded_at.strftime("%Y-%m-%d")}
#             ],
#             "image": image_ipfs_uri
#         }

#         metadata_path = f"metadata_{achievement.id}.json"
#         with open(metadata_path, "w") as f:
#             json.dump(metadata, f)

#         metadata_ipfs_uri = self.upload_to_ipfs(metadata_path)
#         return metadata_ipfs_uri, image_ipfs_uri

#     def mint_nft_badge(self, achievement, wallet_address):
#         print("🚀 Minting NFT Badge...")

#         if not wallet_address.startswith("0x") or len(wallet_address) != 42:
#             raise ValueError(f"❌ Invalid Wallet Address: {wallet_address}")

#         wallet_address = self.web3.to_checksum_address(wallet_address)
#         print(f"📌 Minting to Wallet: {wallet_address}")

#         metadata_uri, image_ipfs_uri = self.create_metadata(achievement)
#         print(f"🌍 Metadata URI: {metadata_uri}")

#         private_key = os.getenv("ADMIN_WALLET_PRIVATE_KEY", "").strip()
#         if not private_key:
#             raise ValueError("❌ Admin wallet private key not found in environment variables")

#         admin_account = Account.from_key(private_key)

#         # Build transaction
#         print("🛠️ Building mint transaction...")
#         tx = self.contract.functions.mint(wallet_address, metadata_uri).build_transaction({
#             "from": admin_account.address,
#             "nonce": self.web3.eth.get_transaction_count(admin_account.address),
#             "gas": 1000000,
#             "gasPrice": self.web3.eth.gas_price
#         })

#         print("✍️ Signing transaction...")
#         signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)

#         print("📡 Sending transaction to blockchain...")
#         tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

#         print("⏳ Waiting for transaction confirmation...")
#         receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

#         # Extract token ID
#         token_id = "1"
#         try:
#             transfer_events = self.contract.events.Transfer().process_receipt(receipt)
#             if transfer_events:
#                 token_id = str(transfer_events[0]["args"]["tokenId"])
#                 print(f"🏷️ Token ID: {token_id}")
#         except Exception as e:
#             print(f"⚠️ Could not extract token ID: {e}")

#         nft_badge, created = NFTBadge.objects.update_or_create(
#             achievement=achievement,
#             defaults={
#                 "token_id": token_id,
#                 "contract_address": self.contract_address,
#                 "transaction_hash": tx_hash.hex(),
#                 "metadata_uri": metadata_uri,
#                 "minted_at": timezone.now(),
#                 "wallet_address": wallet_address,
#                 "blockchain": "polygon",
#                 "image_url": image_ipfs_uri
#             }
#         )

#         print(f"✅ NFT Minted Successfully! Token ID: {token_id}")
#         return nft_badge

# def send_nft_badge(achievement_id, wallet_address):
#     try:
#         print(f"📦 Fetching Achievement ID: {achievement_id}")
#         achievement = Achievement.objects.get(id=achievement_id)

#         print(f"🏆 Found Achievement: {achievement.title}")

#         print("🛠️ Initializing NFTBadgeService...")
#         service = NFTBadgeService()

#         print(f"⚡ Minting NFT for Wallet: {wallet_address}")
#         nft_badge = service.mint_nft_badge(achievement, wallet_address)

#         if nft_badge:
#             print(f"✅ NFT Badge Minted Successfully for {wallet_address}")
#             return nft_badge
#         else:
#             print("❌ Failed to mint NFT badge")
#             return None

#     except Achievement.DoesNotExist:
#         print(f"❌ Achievement {achievement_id} does not exist")
#         return None
#     except Exception as e:
#         print(f"❌ Error minting NFT: {e}")
#         return None
