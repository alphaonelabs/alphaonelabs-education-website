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
    def __init__(self, contract_address, admin_private_key):
        self.web3 = Web3(Web3.HTTPProvider(WEB3_URL_PROVIDER))

        if not self.web3.is_connected():
            raise ConnectionError("❌ Failed to connect to blockchain")

        logger.info("✅ Connected to Polygon Amoy Testnet")

        # Validate Blockfrost API Key
        if not BLOCKFROST_API_KEY:
            raise ValueError("❌ Blockfrost API key is missing!")

        # Load contract address and ABI
        self.contract_address = self.web3.to_checksum_address(contract_address)
        logger.info(f"📜 Smart Contract Address: {self.contract_address}")

        self.contract_abi = self._load_contract_abi()
        self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.contract_abi)
        self.admin_private_key = admin_private_key

    def _load_contract_abi(self):
        """Load contract ABI from file"""
        try:
            with open("web/static/contracts/nft_abi.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError("❌ ABI file not found!")

    @staticmethod
    def upload_to_ipfs(file_path):
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

        except Exception:
            logger.error("IPFS Upload Error")
            raise

    def create_metadata(self, achievement):
        """Creates and uploads metadata JSON for the NFT badge to IPFS"""
        image_path = f"static/images/badges/{achievement.achievement_type}.png"

        # Verify file exists before upload
        if not os.path.exists(image_path):
            logger.warning(f"Image file not found: {image_path}")
            image_path = "web/static/images/nft.png"

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
        logger.info("🚀 Minting NFT Badge...")
        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            raise ValueError(f"❌ Invalid Wallet Address: {wallet_address}")
        wallet_address = self.web3.to_checksum_address(wallet_address)
        logger.info(f"📌 Minting to Wallet: {wallet_address}")
        metadata_uri, image_ipfs_uri = self.create_metadata(achievement)
        logger.info(f"🌍 Metadata URI: {metadata_uri}")
        admin_account = Account.from_key(self.admin_private_key)
        # Build transaction
        logger.info("🛠️ Building mint transaction...")
        tx = self.contract.functions.mint(wallet_address, metadata_uri).build_transaction(
            {
                "from": admin_account.address,
                "nonce": self.web3.eth.get_transaction_count(admin_account.address),
                "gas": 1000000,
                "gasPrice": self.web3.eth.gas_price,
            }
        )
        logger.info("✍️ Signing transaction...")
        signed_tx = self.web3.eth.account.sign_transaction(tx, self.admin_private_key)
        logger.info("📡 Sending transaction to blockchain...")
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        logger.info("⏳ Waiting for transaction confirmation...")
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt


def send_nft_badge(achievement_id, wallet_address, contract_address, admin_private_key):
    """
    Send an NFT badge to a wallet address using the provided contract address and admin key

    Parameters:
    achievement_id (int): ID of the Achievement to mint as an NFT
    wallet_address (str): Recipient's wallet address
    contract_address (str): NFT contract address
    admin_private_key (str): Private key of the admin account for minting

    Returns:
    tuple: (receipt, nft_badge) or (None, None) on error
    """
    try:
        logger.info(f"📦 Fetching Achievement ID: {achievement_id}")
        achievement = Achievement.objects.get(id=achievement_id)

        logger.info("🛠️ Initializing NFTBadgeService...")
        service = NFTBadgeService(contract_address, admin_private_key)

        receipt = service.mint_nft_badge(achievement, wallet_address)

        # Create NFTBadge record in database
        if receipt and receipt.status == 1:
            # Get metadata URI from the transaction
            metadata_uri, image_ipfs_uri = service.create_metadata(achievement)

            # Extract token ID from receipt logs
            token_id = None
            for log in receipt.logs:
                # This assumes the contract emits a Transfer event with the token ID
                # You might need to adjust this based on your specific contract
                if log["address"].lower() == contract_address.lower():
                    try:
                        # Typically the token ID is in the Transfer event data
                        topics = log["topics"]
                        if len(topics) == 4:  # ERC-721 Transfer event has 4 topics
                            token_id = int(topics[3].hex(), 16)
                            break
                    except Exception as e:
                        logger.warning(f"Could not extract token ID from log: {e}")

            # If we couldn't get the token ID from logs, use a fallback
            if token_id is None:
                # Use a timestamp-based integer ID as fallback
                token_id = achievement.id * 1_000_000 + int(timezone.now().timestamp())

            nft_badge = NFTBadge.objects.create(
                achievement=achievement,
                blockchain="polygon",  # Default to polygon as in your model
                token_id=str(token_id),  # Convert to string as model field is CharField
                transaction_hash=receipt.transactionHash.hex(),
                contract_address=contract_address,
                wallet_address=wallet_address,
                metadata_uri=metadata_uri,
                minted_at=timezone.now(),
                icon_url=image_ipfs_uri.replace("ipfs://", "https://ipfs.io/ipfs/"),
            )
            logger.info(f"✅ NFT Badge minted successfully: {nft_badge.transaction_hash}")
            return receipt, nft_badge
        else:
            logger.error("❌ Transaction failed or returned invalid receipt")
            return receipt, None

    except Achievement.DoesNotExist:
        logger.error(f"❌ Achievement with ID {achievement_id} not found")
        return None, None
    except Exception as e:
        logger.error(f"❌ Error minting NFT: {str(e)}")
        return None, None
