import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import argon2

# Argon2id parameters
# Tuned for high security: ~100MB RAM, 8 parallel threads, 2 iterations.
TIME_COST = 2
MEMORY_COST = 102400
PARALLELISM = 8
KEY_LENGTH = 32

def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a 32-byte AES key from the master password using Argon2id."""
    return argon2.low_level.hash_secret_raw(
        secret=password.encode('utf-8'),
        salt=salt,
        time_cost=TIME_COST,
        memory_cost=MEMORY_COST,
        parallelism=PARALLELISM,
        hash_len=KEY_LENGTH,
        type=argon2.low_level.Type.ID
    )

def encrypt_data(key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    """Encrypts plaintext using AES-256-GCM. Returns (nonce, ciphertext)."""
    nonce = os.urandom(12) # GCM standard nonce size
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return nonce, ciphertext

def decrypt_data(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """Decrypts ciphertext using AES-256-GCM. Raises ValueError on failure."""
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    except InvalidTag:
        # InvalidTag is raised if the password is wrong OR if the file was tampered with.
        # We catch and raise a generic error to prevent side-channel information leaks.
        raise ValueError("Authentication failed or data is corrupted.")