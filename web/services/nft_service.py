import json
import logging
import os

import requests
from django.conf import settings
from django.utils import timezone
from eth_account import Account
from web3 import Web3

from web.models import Achievement, NFTBadge

logger = logging.getLogger(__name__)

# Blockfrost API Configuration

# Use WEB3_URL_PROVIDER for Polygon RPC URL
WEB3_URL_PROVIDER = settings.WEB3_PROVIDER_URL
if not WEB3_URL_PROVIDER:
    raise ValueError("❌ WEB3_PROVIDER_URL is missing in environment variables")

BLOCKFROST_API_KEY = settings.BLOCKFROST_API_KEY
BLOCKFROST_BASE_ENDPOINT = settings.BLOCKFROST_BASE_ENDPOINT


class NFTBadgeService:
    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(WEB3_URL_PROVIDER))

        if not self.web3.is_connected():
            raise ConnectionError("❌ Failed to connect to blockchain")

        print("✅ Connected to Polygon Amoy Testnet")

        # Validate Blockfrost API Key
        if not BLOCKFROST_API_KEY:
            raise ValueError("❌ Blockfrost API key is missing!")

        # Load contract address and ABI
        self.contract_address = settings.NFT_CONTRACT_ADDRESS
        if not self.contract_address:
            raise ValueError("❌ NFT_CONTRACT_ADDRESS is missing in environment variables")

        self.contract_address = self.web3.to_checksum_address(self.contract_address)
        print(f"📜 Smart Contract Address: {self.contract_address}")

        self.contract_abi = self._load_contract_abi()
        self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.contract_abi)

    def _load_contract_abi(self):
        """Load contract ABI from file"""
        try:
            with open("web/static/contracts/nft_abi.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError("❌ ABI file not found!")

    @staticmethod
    def upload_to_ipfs(file_path, max_retries=3):
        """
        Upload file to IPFS using Blockfrost API
        """
        # Prepare headers exactly as in curl request
        headers = {"project_id": BLOCKFROST_API_KEY}

        try:
            # Open file in binary read mode
            with open(file_path, "rb") as file:
                # Prepare multipart form data
                files = {"file": (os.path.basename(file_path), file, "application/octet-stream")}

                # Send POST request
                response = requests.post(
                    f"{BLOCKFROST_BASE_ENDPOINT}/ipfs/add",
                    headers=headers,
                    files=files,
                    timeout=30,  # 30 seconds timeout
                )

                # Log full response for debugging
                logger.info(f"Upload Response Status: {response.status_code}")
                logger.info(f"Upload Response Content: {response.text}")

                # Check for successful upload
                if response.status_code == 200:
                    # Parse the response
                    upload_result = response.json()
                    ipfs_hash = upload_result.get("ipfs_hash")

                    if not ipfs_hash:
                        logger.error("No IPFS hash found in response")
                        raise ValueError("Invalid upload response")

                    # Attempt to pin the file
                    pin_headers = headers.copy()
                    pin_response = requests.post(
                        f"{BLOCKFROST_BASE_ENDPOINT}/ipfs/pin/add/{ipfs_hash}", headers=pin_headers, timeout=30
                    )

                    if pin_response.status_code == 200:
                        logger.info(f"Successfully uploaded and pinned: {ipfs_hash}")
                        return f"ipfs://{ipfs_hash}"
                    else:
                        logger.warning(f"Pinning failed: {pin_response.text}")
                        return f"ipfs://{ipfs_hash}"

                else:
                    # Log detailed error
                    logger.error(f"Upload failed: {response.status_code} - {response.text}")
                    raise ValueError(f"Upload failed: {response.text}")

        except Exception as e:
            logger.error(f"IPFS Upload Error: {e}")
            raise

    def create_metadata(self, achievement):
        """Creates and uploads metadata JSON for the NFT badge to IPFS"""
        image_path = f"static/images/badges/{achievement.achievement_type}.png"

        # Verify file exists before upload
        if not os.path.exists(image_path):
            logger.warning(f"Image file not found: {image_path}")
            image_path = "web/static/images/logo.png"

        # Upload image to IPFS
        image_ipfs_uri = self.upload_to_ipfs(image_path)

        # Create metadata
        metadata = {
            "name": achievement.title,
            "description": achievement.description,
            "attributes": [
                {"trait_type": "Achievement Type", "value": achievement.get_achievement_type_display()},
                {"trait_type": "Course", "value": achievement.course.title if achievement.course else "General"},
                {"trait_type": "Awarded Date", "value": achievement.awarded_at.strftime("%Y-%m-%d")},
            ],
            "image": image_ipfs_uri,
        }

        # Create temporary metadata file
        metadata_path = f"metadata_{achievement.id}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Upload metadata to IPFS
        try:
            metadata_ipfs_uri = self.upload_to_ipfs(metadata_path)
        finally:
            # Always clean up temporary metadata file
            if os.path.exists(metadata_path):
                os.remove(metadata_path)

        return metadata_ipfs_uri, image_ipfs_uri

    def mint_nft_badge(self, achievement, wallet_address):
        print("🚀 Minting NFT Badge...")

        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            raise ValueError(f"❌ Invalid Wallet Address: {wallet_address}")

        wallet_address = self.web3.to_checksum_address(wallet_address)
        print(f"📌 Minting to Wallet: {wallet_address}")

        metadata_uri, image_ipfs_uri = self.create_metadata(achievement)
        print(f"🌍 Metadata URI: {metadata_uri}")

        private_key = settings.ADMIN_WALLET_PRIVATE_ADDRESS
        if not private_key:
            raise ValueError("❌ Admin wallet private key not found in environment variables")

        admin_account = Account.from_key(private_key)

        # Build transaction
        print("🛠️ Building mint transaction...")
        tx = self.contract.functions.mint(wallet_address, metadata_uri).build_transaction(
            {
                "from": admin_account.address,
                "nonce": self.web3.eth.get_transaction_count(admin_account.address),
                "gas": 1000000,
                "gasPrice": self.web3.eth.gas_price,
            }
        )

        print("✍️ Signing transaction...")
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)

        print("📡 Sending transaction to blockchain...")
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print("⏳ Waiting for transaction confirmation...")
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

        # Extract token ID
        token_id = "1"
        try:
            transfer_events = self.contract.events.Transfer().process_receipt(receipt)
            if transfer_events:
                token_id = str(transfer_events[0]["args"]["tokenId"])
                print(f"🏷️ Token ID: {token_id}")
        except Exception as e:
            print(f"⚠️ Could not extract token ID: {e}")

        nft_badge, created = NFTBadge.objects.update_or_create(
            achievement=achievement,
            token_id=token_id,
            wallet_address=wallet_address,
            blockchain="polygon",
            contract_address=self.contract_address,
            metadata_uri=metadata_uri,
            icon_url="web/static/images/logo.png",
            transaction_hash=tx_hash.hex(),
            minted_at=timezone.now(),
        )
        print(f"✅ NFT Minted Successfully! Token ID: {token_id}")
        return nft_badge


def send_nft_badge(achievement_id, wallet_address):
    try:
        print(f"📦 Fetching Achievement ID: {achievement_id}")
        achievement = Achievement.objects.get(id=achievement_id)

        print(f"🏆 Found Achievement: {achievement.title}")

        print("🛠️ Initializing NFTBadgeService...")
        service = NFTBadgeService()

        print(f"⚡ Minting NFT for Wallet: {wallet_address}")
        nft_badge = service.mint_nft_badge(achievement, wallet_address)

        if nft_badge:
            print(f"✅ NFT Badge Minted Successfully for {wallet_address}")
            return nft_badge
        else:
            print("❌ Failed to mint NFT badge")
            return None

    except Achievement.DoesNotExist:
        print(f"❌ Achievement {achievement_id} does not exist")
        return None
    except Exception as e:
        print(f"❌ Error minting NFT: {e}")
        return None
