"""Guard against real credentials landing in tracked docs and config files.

In 2026-05 a dev admin password, a database password and the live FLOWFORGE_SECRET_KEY were
committed in docs/testing.md and a few scripts. TruffleHog missed it because a bare
`PASSWORD=value` line matches no provider-specific detector. This test is the generic net.

It scans tracked configuration and documentation files (not application code, where
`password=` is an ordinary variable) for:
  1. 64-hex-character values assigned to a *SECRET_KEY / *JWT_SECRET setting,
  2. passwords embedded in database / broker URLs,
  3. env-var style `*PASSWORD*` settings,
  4. password values passed to command-line flags such as `-ApiPass "..."`,
and fails unless the value is an obvious placeholder (`<...>`, `${...}`, `your-...`,
`changeme`, a repeated character, ...) or a known public local-demo default listed below.

If it flags something real: remove it and rotate the credential, because it is already in git
history. If it flags a harmless placeholder: make the placeholder more obvious (`<password>`)
rather than adding it to the allowlist.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

SCANNED_SUFFIXES = {'.md', '.yml', '.yaml', '.ps1', '.sh', '.toml', '.cfg', '.ini', '.txt', '.example', '.env'}
SKIP_FILES = {'CHANGELOG.md'}  # release notes quote setting names, never values
# Public throwaway demo container (documented as sample data only), exposed with a known password on purpose.
DEMO_FILES = {'docker-compose.sample-db.yml'}

KEY64 = re.compile(r'''(?i)(?:SECRET_KEY|JWT_SECRET)\s*[=:]-?\s*['"]?([0-9a-f]{64})\b''')
# Any bare 64-hex value in any tracked text file (Python, TypeScript, scripts...). Image digests
# and package hashes are `sha256:<hex>`; lockfiles are skipped entirely.
HEX64_ANY = re.compile(r'(?<![0-9a-fA-F])(?<!sha256:)(?<!sha256-)([0-9a-f]{64})(?![0-9a-fA-F])')
BINARY_SUFFIXES = {'.png', '.jpg', '.gif', '.ico', '.woff', '.woff2', '.pdf', '.lock', '.svg'}
DB_URL_PW = re.compile(r'''(?i)\b(?:postgres(?:ql)?|mysql|oracle|mssql|redis|amqp)://[^\s:/@'"<>]+:([^\s@'"<>`]+)@''')
# Env-var style names only (E2E_PASSWORD, POSTGRES_PASSWORD, $env:X_PASSWORD), so prose such as
# "Password: use an app password" is not mistaken for a setting.
PW_SETTING = re.compile(r'''\b[A-Z0-9_]*PASSWORD[A-Z0-9_]*\s*[=:]\s*['"]?([^\s'"`,;|)]{6,})''')
# Command-line flags that take a password (the shape `-ApiPass "..."` that leaked in docs/testing.md).
PW_FLAG = re.compile(r'''(?i)(?:^|\s)(?:-ApiPass(?:word)?|--pass(?:word)?)[ =]+['"]?([^\s'"`]{4,})''')

PLACEHOLDER_PREFIXES = (
    '<', '${', '$(', '$env', '$', '{{', '%', 'your', 'change', 'replace', 'example', 'sample',
    'xxx', 'dummy', 'placeholder', 'secret', 'password', 'pass', 'test', 'user', 'str', 'dev',
)
# Public, documented local-demo defaults (compose files and quick-start snippets).
KNOWN_DEMO_DEFAULTS = {'flowforge', 'postgres', 'oracle', 'admin'}

RULES = (
    (KEY64, 'secret key'),
    (DB_URL_PW, 'database/broker URL password'),
    (PW_SETTING, 'password setting'),
    (PW_FLAG, 'password flag'),
)


def _tracked_files():
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip('not a git checkout')
    for name in out.stdout.split():
        p = Path(name)
        if p.name in SKIP_FILES or name in DEMO_FILES:
            continue
        if p.suffix in SCANNED_SUFFIXES or p.name.startswith('.env'):
            yield name


def _is_placeholder(value: str) -> bool:
    v = value.strip().strip('\'"').lower()
    if not v or v in KNOWN_DEMO_DEFAULTS:
        return True
    if v.startswith(PLACEHOLDER_PREFIXES):
        return True
    if len(set(v)) <= 4:          # aaaa..., 0000..., abab...
        return True
    return bool(re.fullmatch(r'[.*x#-]+', v))


def find_problems(text: str) -> list[tuple[int, str]]:
    problems = []
    for n, line in enumerate(text.splitlines(), 1):
        for rx, kind in RULES:
            m = rx.search(line)
            if m and not _is_placeholder(m.group(1)):
                problems.append((n, kind))
    return problems


def test_no_real_credentials_in_tracked_config_and_docs():
    found = []
    for name in _tracked_files():
        try:
            text = (ROOT / name).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        found += [f'{name}:{n}: {kind} is not a placeholder' for n, kind in find_problems(text)]
    assert not found, (
        'Possible real credentials in tracked files (values are not printed). Remove them and rotate '
        'the credential, since anything committed is already in git history:\n' + '\n'.join(found)
    )


def test_detector_catches_the_shapes_that_leaked_and_ignores_placeholders():
    leaked_shapes = [
        'E2E_PASSWORD=Sup3rS3cret!',
        'FLOWFORGE_SECRET_KEY=' + '4a1f9c3e' * 8,
        '$env:FLOWFORGE_JWT_SECRET = "' + '0123456789abcdef' * 4 + '"',
        'FLOWFORGE_DB_URL=postgresql://svc:Hunter22pw@db.internal:5432/ff',
        '.\\run_tests.ps1 -Manual -ApiUser admin -ApiPass "Correct-Horse-9"',
        'check_api.py --url http://localhost:5000 --user admin --pass "Correct-Horse-9"',
    ]
    for line in leaked_shapes:
        assert find_problems(line), f'should have been flagged: {line!r}'

    harmless = [
        'E2E_PASSWORD=<your-admin-password>',
        'FLOWFORGE_SECRET_KEY=<64 hex chars>',
        'FLOWFORGE_SECRET_KEY=' + 'a' * 64,
        'FLOWFORGE_DB_URL=postgresql://flowforge:${POSTGRES_PASSWORD:?set in .env}@db:5432/flowforge',
        'FLOWFORGE_DB_URL=postgresql://user:yourpassword@localhost:5432/flowforge',
        'POSTGRES_PASSWORD=changeme',
        'FLOWFORGE_PASSWORD=',
        '.\\run_tests.ps1 -Manual -ApiUser admin -ApiPass "<your-admin-password>"',
        'Password: 16-character App Password (not your account password)',
    ]
    for line in harmless:
        assert not find_problems(line), f'false positive: {line!r}'


def _all_text_files():
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip('not a git checkout')
    for name in out.stdout.split():
        low = name.lower()
        if Path(low).suffix in BINARY_SUFFIXES or 'requirements' in low or 'package-lock' in low:
            continue
        yield name


def find_bare_hex_keys(text: str) -> list[int]:
    return [
        n for n, line in enumerate(text.splitlines(), 1)
        if any(len(set(m.group(1))) > 4 for m in HEX64_ANY.finditer(line))
    ]


def test_no_high_entropy_64_hex_value_anywhere_in_tracked_files():
    """A 64-hex string is the shape of FLOWFORGE_SECRET_KEY / JWT_SECRET (`secrets.token_hex(32)`)."""
    found = []
    for name in _all_text_files():
        try:
            text = (ROOT / name).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        found += [f'{name}:{n}' for n in find_bare_hex_keys(text)]
    assert not found, (
        'High-entropy 64-hex values found (not printed). If one is a real key, remove it and rotate it; '
        'if it is a test fixture, generate it at runtime with secrets.token_hex(32):\n' + '\n'.join(found)
    )


def test_bare_hex_detector():
    assert find_bare_hex_keys('key = "' + '4a1f9c3e' * 8 + '"')
    assert find_bare_hex_keys('${FLOWFORGE_SECRET_KEY:-' + '4a1f9c3e' * 8 + '}')
    assert not find_bare_hex_keys('image: postgres@sha256:' + '4a1f9c3e' * 8)
    assert not find_bare_hex_keys('key = "' + 'a' * 64 + '"')
    assert not find_bare_hex_keys('git sha ' + '4a1f9c3e' * 5)   # 40 hex chars: a commit id, not a key
