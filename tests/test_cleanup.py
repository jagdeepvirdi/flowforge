"""Tests for engine/cleanup.py — output file TTL deletion."""
import time
from pathlib import Path


def _touch_old(path: Path, age_seconds: float) -> None:
    """Create a file and backdate its mtime."""
    path.write_bytes(b"x" * 100)
    mtime = time.time() - age_seconds
    import os
    os.utime(path, (mtime, mtime))


def _touch_new(path: Path) -> None:
    path.write_bytes(b"x" * 50)


# ── directory does not exist ──────────────────────────────────────────────────

def test_missing_dir_returns_zeros(tmp_path):
    from flowforge.engine.cleanup import cleanup_output_files
    result = cleanup_output_files(output_dir=str(tmp_path / 'nonexistent'), ttl_days=7)
    assert result == {'deleted': 0, 'bytes_freed': 0, 'errors': 0}


# ── basic TTL logic ───────────────────────────────────────────────────────────

def test_old_file_is_deleted(tmp_path):
    from flowforge.engine.cleanup import cleanup_output_files
    old = tmp_path / 'old_report.xlsx'
    _touch_old(old, age_seconds=8 * 86_400)  # 8 days old, TTL=7
    result = cleanup_output_files(output_dir=str(tmp_path), ttl_days=7)
    assert result['deleted'] == 1
    assert result['bytes_freed'] == 100
    assert not old.exists()


def test_new_file_is_kept(tmp_path):
    from flowforge.engine.cleanup import cleanup_output_files
    new = tmp_path / 'new_report.csv'
    _touch_new(new)
    result = cleanup_output_files(output_dir=str(tmp_path), ttl_days=7)
    assert result['deleted'] == 0
    assert new.exists()


def test_mixed_files(tmp_path):
    from flowforge.engine.cleanup import cleanup_output_files
    old = tmp_path / 'old.csv'
    new = tmp_path / 'new.csv'
    _touch_old(old, age_seconds=10 * 86_400)
    _touch_new(new)
    result = cleanup_output_files(output_dir=str(tmp_path), ttl_days=7)
    assert result['deleted'] == 1
    assert not old.exists()
    assert new.exists()


def test_bytes_freed_accumulates(tmp_path):
    from flowforge.engine.cleanup import cleanup_output_files
    for i in range(3):
        p = tmp_path / f'old_{i}.csv'
        _touch_old(p, age_seconds=9 * 86_400)
    result = cleanup_output_files(output_dir=str(tmp_path), ttl_days=7)
    assert result['deleted'] == 3
    assert result['bytes_freed'] == 300  # 3 × 100 bytes


def test_returns_correct_keys(tmp_path):
    from flowforge.engine.cleanup import cleanup_output_files
    result = cleanup_output_files(output_dir=str(tmp_path), ttl_days=7)
    assert set(result.keys()) == {'deleted', 'bytes_freed', 'errors'}


# ── non-file items are skipped ────────────────────────────────────────────────

def test_subdirectory_not_deleted(tmp_path):
    from flowforge.engine.cleanup import cleanup_output_files
    sub = tmp_path / 'subdir'
    sub.mkdir()
    result = cleanup_output_files(output_dir=str(tmp_path), ttl_days=0)
    # ttl=0 means everything is expired, but directories are still skipped
    assert result['deleted'] == 0
    assert sub.is_dir()


# ── zero-day TTL deletes everything ──────────────────────────────────────────

def test_ttl_zero_deletes_all_files(tmp_path):
    from flowforge.engine.cleanup import cleanup_output_files
    for i in range(4):
        f = tmp_path / f'file_{i}.txt'
        _touch_new(f)
    # Need files that are at least 1 second old; sleep is not ideal but
    # using age_seconds just above 0 is more reliable:
    for f in tmp_path.iterdir():
        import os
        os.utime(f, (time.time() - 2, time.time() - 2))
    result = cleanup_output_files(output_dir=str(tmp_path), ttl_days=0)
    assert result['deleted'] == 4


# ── env var fallbacks ─────────────────────────────────────────────────────────

def test_uses_env_var_dir(tmp_path, monkeypatch):
    from flowforge.engine.cleanup import cleanup_output_files
    monkeypatch.setenv('FLOWFORGE_OUTPUT_DIR', str(tmp_path))
    old = tmp_path / 'ev.csv'
    _touch_old(old, age_seconds=8 * 86_400)
    result = cleanup_output_files(ttl_days=7)
    assert result['deleted'] == 1


def test_uses_env_var_ttl(tmp_path, monkeypatch):
    from flowforge.engine.cleanup import cleanup_output_files
    monkeypatch.setenv('FLOWFORGE_OUTPUT_TTL_DAYS', '3')
    old = tmp_path / 'ev2.csv'
    _touch_old(old, age_seconds=4 * 86_400)
    result = cleanup_output_files(output_dir=str(tmp_path))
    assert result['deleted'] == 1


# ── error handling ────────────────────────────────────────────────────────────

def test_unreadable_file_counts_as_error(tmp_path, monkeypatch):
    from flowforge.engine.cleanup import cleanup_output_files

    bad = tmp_path / 'bad.csv'
    bad.write_bytes(b'x')

    # Patch Path.stat to raise for this specific file
    original_stat = Path.stat

    def patched_stat(self, **kw):
        if self == bad:
            raise PermissionError("access denied")
        return original_stat(self, **kw)

    monkeypatch.setattr(Path, 'stat', patched_stat)
    result = cleanup_output_files(output_dir=str(tmp_path), ttl_days=0)
    assert result['errors'] == 1
