"""
AFASA 2.0 - Secrets Encryption
AES-256-GCM encryption for sensitive credentials
"""
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Tuple

from .settings import get_settings


class SecretsManager:
    def __init__(self):
        settings = get_settings()
        key_b64 = settings.afasa_master_key_base64
        if key_b64:
            self._key = base64.b64decode(key_b64)
        else:
            # Generate a temporary key for development
            self._key = os.urandom(32)
    
    def encrypt(self, plaintext: str) -> Tuple[bytes, bytes]:
        """
        Encrypt plaintext using AES-256-GCM.
        Returns (nonce, ciphertext) combined as single bytes.
        """
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        # Combine nonce + ciphertext for storage
        return nonce + ciphertext
    
    def decrypt(self, data: bytes) -> str:
        """
        Decrypt data encrypted with encrypt().
        Input is nonce (12 bytes) + ciphertext.
        """
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()


_secrets_manager: SecretsManager = None


def get_secrets_manager() -> SecretsManager:
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
