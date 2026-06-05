"""AES-256-GCM encryption for credential storage in the database and report files."""
import base64
import io
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Suffix appended to encrypted output files.
ENCRYPTED_SUFFIX = '.enc'


def _key() -> bytes:
    raw = os.environ.get('FLOWFORGE_SECRET_KEY', '')
    if not raw:
        raise RuntimeError("FLOWFORGE_SECRET_KEY environment variable is not set.")
    # Accept hex-encoded 32-byte key (64 hex chars) or raw bytes
    try:
        decoded = bytes.fromhex(raw)
    except ValueError:
        decoded = raw.encode()
    if len(decoded) != 32:
        raise RuntimeError("FLOWFORGE_SECRET_KEY must be a 32-byte key (64 hex characters).")
    return decoded


def encrypt_value(s: str) -> str:
    """Encrypt a single string value for database storage."""
    return encrypt_config({'v': s})


def decrypt_value(token: str) -> str:
    """Decrypt a single string value from database storage."""
    return decrypt_config(token)['v']


def encrypt_config(data: dict) -> str:
    """Encrypt a dict to a base64 string for storage in the database."""
    plaintext = json.dumps(data).encode()
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key()).encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_config(token: str) -> dict:
    """Decrypt a base64 string from the database back to a dict."""
    raw = base64.b64decode(token.encode())
    nonce, ciphertext = raw[:12], raw[12:]
    plaintext = AESGCM(_key()).decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())


# ── File encryption at rest ─────────────────────────────────────────────────

def encrypt_file(path: Path) -> Path:
    """Encrypt a report file in-place; returns the new .enc path.

    The original file is removed after encryption.  Encryption is enabled by
    setting FLOWFORGE_ENCRYPT_OUTPUT=true in the environment.
    """
    plaintext = path.read_bytes()
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key()).encrypt(nonce, plaintext, None)
    enc_path = path.with_suffix(path.suffix + ENCRYPTED_SUFFIX)
    enc_path.write_bytes(nonce + ciphertext)
    path.unlink()
    return enc_path


def decrypt_file_to_bytes(path: Path) -> bytes:
    """Return the plaintext bytes of an encrypted report file."""
    raw = path.read_bytes()
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(_key()).decrypt(nonce, ciphertext, None)


def decrypt_file_to_stream(path: Path) -> io.BytesIO:
    """Return a BytesIO stream of the decrypted file contents."""
    return io.BytesIO(decrypt_file_to_bytes(path))


def output_encryption_enabled() -> bool:
    """Return True when FLOWFORGE_ENCRYPT_OUTPUT=true is set."""
    return os.environ.get('FLOWFORGE_ENCRYPT_OUTPUT', '').lower() == 'true'
