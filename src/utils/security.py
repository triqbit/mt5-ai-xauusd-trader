"""
Security utilities for MT5 AI Trading Bot.
src/utils/security.py
"""

import hashlib
import hmac
from pathlib import Path


def sign_file(filepath: Path, key: str) -> str:
    """
    Generate an HMAC-SHA256 signature for a file.

    Args:
        filepath: Path to the file to sign.
        key: Secret key used for signing.

    Returns:
        Hexadecimal HMAC signature.
    """
    h = hmac.new(key.encode(), digestmod=hashlib.sha256)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file_signature(filepath: Path, signature: str, key: str) -> bool:
    """
    Verify the HMAC-SHA256 signature of a file.

    Args:
        filepath: Path to the file to verify.
        signature: Expected hexadecimal HMAC signature.
        key: Secret key used for verification.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not filepath.exists():
        return False

    actual_signature = sign_file(filepath, key)
    # Use hmac.compare_digest to prevent timing attacks
    return hmac.compare_digest(actual_signature, signature)
