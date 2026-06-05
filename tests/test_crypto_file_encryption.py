"""Tests for file-level encryption functions in crypto.py.

Covers: encrypt_file, decrypt_file_to_bytes, decrypt_file_to_stream.
"""
import io

import pytest


@pytest.fixture(autouse=True)
def _set_secret_key(monkeypatch):
    monkeypatch.setenv(
        'FLOWFORGE_SECRET_KEY',
        '4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0',
    )


def test_encrypt_file_creates_enc_file(tmp_path):
    from flowforge.crypto import ENCRYPTED_SUFFIX, encrypt_file
    original = tmp_path / 'report.xlsx'
    original.write_bytes(b'Excel content here')
    enc_path = encrypt_file(original)
    assert enc_path.suffix == ENCRYPTED_SUFFIX
    assert enc_path.exists()
    assert not original.exists()


def test_encrypt_file_returns_enc_path(tmp_path):
    from flowforge.crypto import encrypt_file
    f = tmp_path / 'data.csv'
    f.write_bytes(b'col1,col2\n1,2\n')
    enc = encrypt_file(f)
    assert str(enc).endswith('.enc')


def test_decrypt_file_to_bytes_roundtrip(tmp_path):
    from flowforge.crypto import decrypt_file_to_bytes, encrypt_file
    content = b'Secret report data \x00\xff'
    f = tmp_path / 'report.bin'
    f.write_bytes(content)
    enc = encrypt_file(f)
    recovered = decrypt_file_to_bytes(enc)
    assert recovered == content


def test_decrypt_file_to_stream_returns_bytesio(tmp_path):
    from flowforge.crypto import decrypt_file_to_stream, encrypt_file
    content = b'Stream test content'
    f = tmp_path / 'out.txt'
    f.write_bytes(content)
    enc = encrypt_file(f)
    stream = decrypt_file_to_stream(enc)
    assert isinstance(stream, io.BytesIO)
    assert stream.read() == content


def test_encrypt_decrypt_large_file(tmp_path):
    from flowforge.crypto import decrypt_file_to_bytes, encrypt_file
    content = b'X' * 100_000
    f = tmp_path / 'large.bin'
    f.write_bytes(content)
    enc = encrypt_file(f)
    assert decrypt_file_to_bytes(enc) == content


def test_output_encryption_enabled_false_by_default(monkeypatch):
    from flowforge.crypto import output_encryption_enabled
    monkeypatch.delenv('FLOWFORGE_ENCRYPT_OUTPUT', raising=False)
    assert output_encryption_enabled() is False


def test_output_encryption_enabled_true_when_set(monkeypatch):
    from flowforge.crypto import output_encryption_enabled
    monkeypatch.setenv('FLOWFORGE_ENCRYPT_OUTPUT', 'true')
    assert output_encryption_enabled() is True
