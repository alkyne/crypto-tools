#!/usr/bin/env python3

import os
import requests
import hashlib

import sys

try:
    from mnemonic import Mnemonic
    import bip32utils
except ImportError:
    print("Please install required packages: pip install mnemonic bip32utils")
    sys.exit(1)

def seed_phrase_to_private_key(phrase: str, passphrase: str = "") -> str:
    """
    1) Convert the 24-word BIP-39 mnemonic to a seed.
    2) Use BIP32 to derive the Ethereum private key at the path m/44'/60'/0'/0/0.
    3) Return the private key in hex form, prefixed with 0x.
    """
    # 1) Convert to seed (BIP-39)
    mnemo = Mnemonic("english")
    seed = mnemo.to_seed(phrase, passphrase=passphrase)  # "mnemonic" + passphrase is standard

    # 2) Create a BIP32 master key from the seed
    master_key = bip32utils.BIP32Key.fromEntropy(seed)

    # Hardened derivation:
    #   44' -> for BIP44
    #   60' -> for Ethereum
    #   0'  -> account
    #   0   -> change (0 for external, 1 for internal)
    #   0   -> index
    #
    # BIP32 child derivation requires the index plus bip32utils.BIP32_HARDEN for hardened paths.
    # For example, 44' = 44 + bip32utils.BIP32_HARDEN
    #
    # So the path m/44'/60'/0'/0/0 => indexes:
    # m -> master_key
    # 44' -> master_key.ChildKey(44 + BIP32_HARDEN)
    # 60' -> ...
    # 0'  -> ...
    # 0   -> ...
    # 0   -> ...
    #
    hardened_offset = bip32utils.BIP32_HARDEN
    purpose_key = master_key.ChildKey(44 + hardened_offset)
    coin_type_key = purpose_key.ChildKey(60 + hardened_offset)
    account_key = coin_type_key.ChildKey(0 + hardened_offset)
    change_key = account_key.ChildKey(0)
    derived_key = change_key.ChildKey(0)

    # 3) Retrieve the private key in hex form
    private_key_bytes = derived_key.PrivateKey()
    private_key_hex = private_key_bytes.hex()
    return f"0x{private_key_hex}"


def get_bip39_wordlist():
    url = "https://raw.githubusercontent.com/bitcoin/bips/refs/heads/master/bip-0039/english.txt"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text.split()

def generate_mnemonic():
    # 1) Get the BIP-39 English word list
    wordlist = get_bip39_wordlist()
    if len(wordlist) != 2048:
        raise ValueError("Word list must contain 2048 words.")

    # 2) Generate 256 bits of random entropy
    entropy = os.urandom(32)  # 32 bytes = 256 bits

    # 3) Create the checksum (first 8 bits of SHA-256(entropy))
    sha = hashlib.sha256(entropy).digest()
    checksum_length = 256 // 32  # 8 bits for 256 bits of entropy
    # Convert the SHA-256 hash to binary, and take the first 8 bits
    sha_bits = bin(int.from_bytes(sha, byteorder="big"))[2:].zfill(256)
    checksum = sha_bits[:checksum_length]

    # 4) Combine entropy bits + checksum bits
    entropy_bits = bin(int.from_bytes(entropy, byteorder="big"))[2:].zfill(256)
    total_bits = entropy_bits + checksum  # now 264 bits

    # 5) Split into 24 groups of 11 bits each => indices into the wordlist
    mnemonic = []
    for i in range(0, len(total_bits), 11):
        idx = int(total_bits[i : i + 11], 2)
        mnemonic.append(wordlist[idx])

    return mnemonic

if __name__ == "__main__":
    mnemonic_words = generate_mnemonic()
    # 6) Print the 24-word mnemonic (last word includes checksum bits)
    print("Mnemonic phrase (24 words):")
    mnemonic_words_str = " ".join(mnemonic_words)
    print(mnemonic_words_str)

    phrase = mnemonic_words_str
    passphrase = ""
    private_key = seed_phrase_to_private_key(phrase, passphrase)
    print(f"EVM Private Key:")
    print(private_key)