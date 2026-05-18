"""Unit tests for AES-256-GCM credential encryption. No DB needed."""
import os
import pytest

os.environ['FLOWFORGE_SECRET_KEY'] = 'ab' * 32   # 32 bytes = 64 hex chars


def test_encrypt_decrypt_roundtrip():
    from flowforge.crypto import encrypt_config, decrypt_config
    data = {'host': 'localhost', 'port': 5432, 'password': 'secret123'}
    token = encrypt_config(data)
    assert isinstance(token, str)
    assert token != str(data)
    result = decrypt_config(token)
    assert result == data


def test_each_encryption_is_unique():
    """Same input must produce different ciphertext every time (random nonce)."""
    from flowforge.crypto import encrypt_config
    data = {'password': 'same'}
    assert encrypt_config(data) != encrypt_config(data)


def test_missing_key_raises():
    original = os.environ.pop('FLOWFORGE_SECRET_KEY', None)
    try:
        import importlib
        import flowforge.crypto as crypto_mod
        importlib.reload(crypto_mod)
        with pytest.raises(RuntimeError, match='FLOWFORGE_SECRET_KEY'):
            crypto_mod.encrypt_config({'x': 1})
    finally:
        if original:
            os.environ['FLOWFORGE_SECRET_KEY'] = original
        import importlib
        import flowforge.crypto as crypto_mod
        importlib.reload(crypto_mod)


def test_wrong_key_fails_decrypt():
    from flowforge.crypto import encrypt_config
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag

    token = encrypt_config({'secret': 'value'})

    # Tamper: try decrypting with a different key
    wrong_key = bytes.fromhex('cd' * 32)
    raw = base64.b64decode(token.encode())
    nonce, ciphertext = raw[:12], raw[12:]
    with pytest.raises(Exception):   # InvalidTag or similar
        AESGCM(wrong_key).decrypt(nonce, ciphertext, None)


def test_short_key_raises():
    os.environ['FLOWFORGE_SECRET_KEY'] = 'tooshort'
    try:
        import importlib
        import flowforge.crypto as crypto_mod
        importlib.reload(crypto_mod)
        with pytest.raises(RuntimeError, match='32-byte'):
            crypto_mod.encrypt_config({'x': 1})
    finally:
        os.environ['FLOWFORGE_SECRET_KEY'] = 'ab' * 32
        import importlib
        import flowforge.crypto as crypto_mod
        importlib.reload(crypto_mod)
