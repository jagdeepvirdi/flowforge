"""Tests for smart attachment logic in email_step._handle_attachments."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _handle(attachments, max_mb=10, drive_folder_id='folder123',
            drive_message='', context=None):
    from flowforge.steps.email_step import _handle_attachments
    return _handle_attachments(
        attachments,
        max_mb=max_mb,
        drive_folder_id=drive_folder_id,
        drive_message_template=drive_message,
        context=context or {},
    )


# ── File under limit → direct attachment ──────────────────────────────────────

def test_small_file_goes_to_direct(tmp_path):
    small = tmp_path / 'small.csv'
    small.write_bytes(b'x' * 100)   # 100 bytes, well under 10 MB

    direct, extra = _handle([small])

    assert small in direct
    assert extra == ''


def test_multiple_small_files_all_direct(tmp_path):
    files = []
    for i in range(3):
        f = tmp_path / f'file{i}.csv'
        f.write_bytes(b'x' * 1000)
        files.append(f)

    direct, extra = _handle(files)

    assert len(direct) == 3
    assert extra == ''


# ── File over limit → Drive upload ────────────────────────────────────────────

def test_large_file_triggers_drive_upload(tmp_path):
    large = tmp_path / 'big_report.xlsx'
    large.write_bytes(b'x' * (6 * 1024 * 1024))   # 6 MB

    with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/abc') as mock_upload:
        direct, extra = _handle([large], max_mb=5)

    mock_upload.assert_called_once_with(large, 'folder123', make_shareable=True)
    assert large not in direct
    assert 'https://drive.google.com/abc' in extra


def test_large_file_link_in_body(tmp_path):
    large = tmp_path / 'report.xlsx'
    large.write_bytes(b'x' * (15 * 1024 * 1024))   # 15 MB

    with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/xyz'):
        direct, extra = _handle([large], max_mb=10)

    assert 'report.xlsx' in extra
    assert 'https://drive.google.com/xyz' in extra


def test_drive_link_uses_default_message_template(tmp_path):
    large = tmp_path / 'data.csv'
    large.write_bytes(b'x' * (2 * 1024 * 1024))   # 2 MB

    with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/link'):
        _, extra = _handle([large], max_mb=1, drive_message='')

    assert 'uploaded to Google Drive' in extra
    assert 'data.csv' in extra


def test_custom_drive_message_template(tmp_path):
    large = tmp_path / 'file.xlsx'
    large.write_bytes(b'x' * (2 * 1024 * 1024))

    custom_template = 'Files: {% for link in drive_links %}{{ link.filename }}{% endfor %}'

    with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/x'):
        _, extra = _handle([large], max_mb=1, drive_message=custom_template)

    assert extra == 'Files: file.xlsx'


# ── Mixed small + large ───────────────────────────────────────────────────────

def test_mixed_attachments_split_correctly(tmp_path):
    small = tmp_path / 'small.csv'
    small.write_bytes(b'x' * 100)

    large = tmp_path / 'large.xlsx'
    large.write_bytes(b'x' * (20 * 1024 * 1024))   # 20 MB

    with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/big'):
        direct, extra = _handle([small, large], max_mb=10)

    assert small in direct
    assert large not in direct
    assert 'https://drive.google.com/big' in extra


# ── Missing files ─────────────────────────────────────────────────────────────

def test_missing_file_is_skipped(tmp_path):
    missing = tmp_path / 'nonexistent.csv'

    direct, extra = _handle([missing])

    assert direct == []
    assert extra == ''


def test_mix_of_existing_and_missing(tmp_path):
    existing = tmp_path / 'real.csv'
    existing.write_bytes(b'data')
    missing = tmp_path / 'ghost.csv'

    direct, extra = _handle([existing, missing])

    assert existing in direct
    assert missing not in direct


# ── Threshold edge case ───────────────────────────────────────────────────────

def test_file_exactly_at_limit_goes_direct(tmp_path):
    """A file that is exactly max_mb should go direct (> not >=)."""
    max_mb = 5
    exact = tmp_path / 'exact.csv'
    exact.write_bytes(b'x' * (max_mb * 1024 * 1024))

    direct, extra = _handle([exact], max_mb=max_mb)

    assert exact in direct
    assert extra == ''


def test_file_one_byte_over_limit_goes_to_drive(tmp_path):
    max_mb = 5
    over = tmp_path / 'over.csv'
    over.write_bytes(b'x' * (max_mb * 1024 * 1024 + 1))

    with patch('flowforge.storage.google_drive.upload_file', return_value='https://drive.google.com/o'):
        direct, extra = _handle([over], max_mb=max_mb)

    assert over not in direct
    assert 'https://drive.google.com/o' in extra
