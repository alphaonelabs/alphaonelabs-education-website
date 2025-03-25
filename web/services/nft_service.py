# import json
# import os
# from datetime import datetime
# from web3 import Web3
# from eth_account import Account
# from django.conf import settings
# from django.utils import timezone
# from web.models import NFTBadge, Achievement

# class NFTBadgeService:
#     def __init__(self):
#         provider_url = 'https://polygon-amoy.g.alchemy.com/v2/1zqpg4KCcU6eXpi0Eh0NZju2hctd8bWQ'
#         self.web3 = Web3(Web3.HTTPProvider(provider_url))

#         if not self.web3.is_connected():
#             raise ConnectionError(f"Failed to connect to blockchain network at {provider_url}")
#         print("Connection successful")

#         self.contract_address = os.getenv('NFT_CONTRACT_ADDRESS')
#         if not self.contract_address:
#             raise ValueError("NFT_CONTRACT_ADDRESS environment variable is not set")

#         self.contract_address = self.web3.to_checksum_address(self.contract_address)
#         print(f"Contract address: {self.contract_address}")

#         self.contract_abi = self._load_contract_abi()
#         print("ABI loaded")

#         self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.contract_abi)
#         print("Contract loaded successfully")

#     def _load_contract_abi(self):
#         return [
#             {
#                 "inputs": [
#                     {"internalType": "address", "name": "to", "type": "address"},
#                     {"internalType": "string", "name": "uri", "type": "string"}
#                 ],
#                 "name": "mint",
#                 "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
#                 "stateMutability": "nonpayable",
#                 "type": "function"
#             },
#             {
#                 "anonymous": False,
#                 "inputs": [
#                     {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
#                     {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
#                     {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"}
#                 ],
#                 "name": "Transfer",
#                 "type": "event"
#             },
#             {
#                 "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
#                 "name": "tokenURI",
#                 "outputs": [{"internalType": "string", "name": "", "type": "string"}],
#                 "stateMutability": "view",
#                 "type": "function"
#             }
#         ]

#     # def _load_contract_abi(self):
#     #     return [
#     #         {
#     #             "inputs": [
#     #                 {"internalType": "address", "name": "recipient", "type": "address"},
#     #                 {"internalType": "string", "name": "tokenURI", "type": "string"}
#     #             ],
#     #             "name": "mintBadge",
#     #             "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
#     #             "stateMutability": "nonpayable",
#     #             "type": "function"
#     #         },
#     #         {
#     #             "anonymous": False,
#     #             "inputs": [
#     #                 {"indexed": True, "internalType": "address", "name": "recipient", "type": "address"},
#     #                 {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"},
#     #                 {"indexed": False, "internalType": "string", "name": "tokenURI", "type": "string"}
#     #             ],
#     #             "name": "BadgeMinted",
#     #             "type": "event"
#     #         }
#     #     ]
#     def create_metadata(self, achievement):
#         metadata = {
#             "name": achievement.title,
#             "description": achievement.description,
#             "attributes": [
#                 {"trait_type": "Achievement Type", "value": achievement.get_achievement_type_display()},
#                 {"trait_type": "Course", "value": achievement.course.title if achievement.course else "General"},
#                 {"trait_type": "Awarded Date", "value": achievement.awarded_at.strftime("%Y-%m-%d")}
#             ]
#         }

#         # Add image URL if available
#         if hasattr(settings, 'SITE_URL'):
#             metadata["image"] = f"{settings.SITE_URL}/static/images/badges/{achievement.achievement_type}.png"

#         return json.dumps(metadata)

#     def mint_nft_badge(self, achievement, wallet_address):
#         print("Starting NFT minting process...")

#         if not wallet_address:
#             raise ValueError("Wallet address is required to mint NFT badge")

#         if not wallet_address.startswith('0x') or len(wallet_address) != 42:
#             raise ValueError(f"Invalid wallet address format: {wallet_address}")

#         # Convert to checksum address
#         wallet_address = self.web3.to_checksum_address(wallet_address)
#         print(f"Recipient wallet address (checksummed): {wallet_address}")

#         # Create metadata
#         metadata = self.create_metadata(achievement)
#         print(f"Created metadata: {metadata}")

#         # In a production environment, you'd upload this to IPFS and get a real hash
#         metadata_uri = "ipfs://placeholder_ipfs_hash"
#         print(f"Using metadata URI: {metadata_uri}")

#         # Get admin wallet private key
#         private_key = os.getenv('ADMIN_WALLET_PRIVATE_KEY')
#         if not private_key:
#             raise ValueError("Admin wallet private key not found in environment variables")

#         admin_account = Account.from_key(private_key)
#         print(f"Admin wallet address: {admin_account.address}")

#         # Build mint transaction
#         print("Building mint transaction...")
#         tx = self.contract.functions.mint(
#             wallet_address, metadata_uri
#         ).build_transaction({
#             'from': admin_account.address,
#             'nonce': self.web3.eth.get_transaction_count(admin_account.address),
#             'gas': 10000000,
#             'gasPrice': self.web3.eth.gas_price
#         })

#         # Sign and send transaction
#         print("Signing transaction...")
#         signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)

#         print("Sending transaction...")
#         tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
#         print(f"Transaction hash: {tx_hash.hex()}")

#         print("Waiting for transaction receipt...")
#         receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
#         print(f"Transaction status: {'Success' if receipt.status == 1 else 'Failed'}")

#         # Try to get the token ID from events
#         token_id = "1"  # Default fallback
#         try:
#             transfer_events = self.contract.events.Transfer().process_receipt(receipt)
#             if transfer_events:
#                 token_id = str(transfer_events[0]['args']['tokenId'])
#                 print(f"Extracted token ID from events: {token_id}")
#         except Exception as e:
#             print(f"Warning: Could not extract token ID from events: {e}")
#             print("Using default token ID: 1")

#         # Create or update NFTBadge record
#         nft_badge, created = NFTBadge.objects.update_or_create(
#             achievement=achievement,
#             defaults={
#                 'token_id': token_id,
#                 'contract_address': self.contract_address,
#                 'transaction_hash': tx_hash.hex(),
#                 'metadata_uri': metadata_uri,
#                 'minted_at': timezone.now(),
#                 'wallet_address': wallet_address,
#                 'blockchain': 'polygon'
#             }
#         )

#         # Log detailed NFT information
#         print(f"\n===== NFT BADGE MINTED SUCCESSFULLY =====")
#         print(f"Token ID: {token_id}")
#         print(f"Contract Address: {self.contract_address}")
#         print(f"Transaction Hash: {tx_hash.hex()}")
#         print(f"Wallet Address: {wallet_address}")
#         print(f"Blockchain: polygon (Amoy testnet)")
#         print(f"Metadata URI: {metadata_uri}")
#         print(f"Achievement: {achievement.title}")

#         # Provide verification instructions
#         explorer_url = "https://www.oklink.com/amoy"
#         print(f"\n===== HOW TO VERIFY YOUR NFT =====")
#         print(f"1. View transaction on block explorer:")
#         print(f"   {explorer_url}/tx/{tx_hash.hex()}")
#         print(f"2. View NFT in your wallet:")
#         print(f"   a. Open MetaMask and switch to Polygon Amoy testnet")
#         print(f"   b. Go to NFTs tab")
#         print(f"   c. Click 'Import NFT'")
#         print(f"   d. Enter contract address: {self.contract_address}")
#         print(f"   e. Enter token ID: {token_id}")
#         print(f"3. View NFT details on OpenSea testnet:")
#         print(f"   https://testnets.opensea.io/assets/polygon-amoy/{self.contract_address}/{token_id}")
#         print("=======================================\n")

#         return nft_badge

# def send_nft_badge(achievement_id, wallet_address):
#     try:
#         print(f"Starting NFT badge sending process for achievement ID: {achievement_id}")
#         achievement = Achievement.objects.get(id=achievement_id)
#         print(f"Found achievement: {achievement.title}")

#         if hasattr(achievement, 'teacher'):
#             print(f"Achievement teacher: {achievement.teacher}")

#         print("Initializing NFT Badge Service...")
#         service = NFTBadgeService()

#         print(f"Minting NFT badge for wallet: {wallet_address}")
#         nft_badge = service.mint_nft_badge(achievement, wallet_address)

#         if nft_badge:
#             print(f"✅ NFT badge successfully minted and sent to {wallet_address}")
#             return nft_badge
#         else:
#             print(f"❌ Failed to mint NFT badge")
#             return None

#     except Achievement.DoesNotExist:
#         print(f"❌ Error: Achievement with ID {achievement_id} does not exist")
#         return None
#     except Exception as e:
#         print(f"❌ Error minting NFT badge: {e}")
#         return None
