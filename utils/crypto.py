"""Cryptographic utilities for token encryption/decryption"""

from typing import Optional

from cryptography.fernet import Fernet

from config import settings


def get_cipher() -> Fernet:
    """Get Fernet cipher instance with configured encryption key"""
    if not settings.FERNET_ENCRYPTION_KEY:
        raise ValueError("FERNET_ENCRYPTION_KEY not configured")

    key = settings.FERNET_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()

    return Fernet(key)


def encrypt_token(token: str) -> Optional[str]:
    """
    Encrypt a token for secure database storage

    Args:
        token: Plain text token to encrypt

    Returns:
        Encrypted token as base64 string, or None if token is empty
    """
    if not token or not token.strip():
        return None

    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(token.encode())
    return encrypted_bytes.decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a token from database storage

    Args:
        encrypted_token: Base64 encrypted token from database

    Returns:
        Decrypted plain text token, or empty string if input is empty

    Raises:
        ValueError: If decryption fails (invalid token or key)
    """
    if not encrypted_token or not encrypted_token.strip():
        return ""

    cipher = get_cipher()
    try:
        encrypted_bytes = encrypted_token.encode()
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt token: {e}")
