from eth_account import Account
from mnemonic import Mnemonic  # New import for BIP-39 mnemonics


def create_student_wallet():
    """
    Generates a new Ethereum wallet using a BIP-39 mnemonic phrase.

    Returns:
        dict: {'mnemonic': mnemonic_phrase, 'address': wallet_address, 'private_key': private_key}
    """
    # Generate a secure BIP-39 mnemonic phrase
    mnemo = Mnemonic("english")
    mnemonic_phrase = mnemo.generate(strength=128)

    # Convert the mnemonic to a seed
    seed = mnemo.to_seed(mnemonic_phrase)

    # Generate a wallet from the seed
    account = Account.from_key(seed[:32])
    return {"mnemonic": mnemonic_phrase, "address": account.address, "private_key": account.key.hex()}
