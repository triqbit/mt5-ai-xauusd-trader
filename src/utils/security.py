"""
Cryptographic utilities for model integrity and technical trust.
src/utils/security.py
"""

import hashlib
import hmac
from pathlib import Path
from typing import Union


def compute_hmac(filepath: Union[str, Path], key: str) -> str:
    """
    Computes the HMAC-SHA256 signature of a file.

    Args:
        filepath: Path to the file to sign.
        key: The signing key as a string.

    Returns:
        The hex-encoded HMAC signature.
    """
    h = hmac.new(key.encode(), digestmod=hashlib.sha256)
    path = Path(filepath)

    with open(path, "rb") as f:
        # Read in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)

    return h.hexdigest()


def verify_hmac(filepath: Union[str, Path], key: str, expected_signature: str) -> bool:
    """
    Verifies the HMAC-SHA256 signature of a file.

    Args:
        filepath: Path to the file to verify.
        key: The signing key as a string.
        expected_signature: The expected hex-encoded signature.

    Returns:
        True if the signature is valid, False otherwise.
    """
    actual_signature = compute_hmac(filepath, key)
    return hmac.compare_digest(actual_signature, expected_signature)
