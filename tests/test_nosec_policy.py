"""Policy for bandit `# nosec` suppressions in flowforge/.

A bare `# nosec` hid a real SQL injection in data_load.py for months (2026-07 audit). Bandit
reports clean whenever a line carries `# nosec`, so every suppression has to earn its place:

1. It must name the specific bandit test(s) it silences (`# nosec B608`). A bare `# nosec`
   silences every test on the line, including ones added by later edits.
2. It must say why the suppression is safe, in at least three words after the test id(s).
3. The number of suppressions per file is pinned in BASELINE below, so adding (or removing) one
   forces a visible edit to this file in the same diff and gets a reviewer's attention.

If you need a new suppression: fix the finding instead if you can. If you cannot, add the
comment with a reason, then update BASELINE. Only comments count; strings and docstrings do not.
"""
import collections
import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# file -> number of `# nosec` comments. Keep sorted. Adjust deliberately.
BASELINE = {
    'flowforge/api/app.py': 1,
    'flowforge/api/routes/runs.py': 1,
    'flowforge/api/routes/sso.py': 2,
    'flowforge/audit.py': 2,
    'flowforge/cli.py': 1,
    'flowforge/connections/bigquery.py': 1,
    'flowforge/connections/mssql.py': 1,
    'flowforge/connections/mysql.py': 1,
    'flowforge/connections/odbc.py': 1,
    'flowforge/connections/snowflake.py': 1,
    'flowforge/connections/ssh.py': 1,
    'flowforge/db/migrations/versions/0006_projects.py': 2,
    'flowforge/db/migrations/versions/0028_project_members.py': 1,
    'flowforge/email_providers/gmail.py': 1,
    'flowforge/engine/concurrency.py': 3,
    'flowforge/engine/notifications.py': 1,
    'flowforge/steps/bulk_load.py': 4,
    'flowforge/steps/data_load.py': 1,
    'flowforge/steps/db_health_check.py': 3,
    'flowforge/steps/db_query.py': 1,
    'flowforge/storage/google_drive.py': 1,
}

_NOSEC = re.compile(r'#\s*nosec\b(?P<rest>.*)$', re.IGNORECASE)
_IDS = re.compile(r'^[\s:]*(?P<ids>B\d{3}(?:\s*,\s*B\d{3})*)(?P<reason>.*)$')
MIN_REASON_WORDS = 3


def _nosec_comments():
    """Yield (relative path, line number, comment text) for every `# nosec` comment."""
    for path in sorted((ROOT / 'flowforge').rglob('*.py')):
        rel = path.relative_to(ROOT).as_posix()
        source = path.read_bytes()
        for tok in tokenize.tokenize(io.BytesIO(source).readline):
            if tok.type == tokenize.COMMENT and 'nosec' in tok.string.lower():
                yield rel, tok.start[0], tok.string


def test_every_nosec_names_a_bandit_test_and_gives_a_reason():
    problems = []
    for rel, line, text in _nosec_comments():
        m = _NOSEC.search(text)
        if not m:
            continue  # mentions the word in a comment, but is not a suppression marker
        ids = _IDS.match(m.group('rest'))
        if not ids:
            problems.append(f'{rel}:{line}: bare `# nosec` silences every bandit test; name one (e.g. B608)')
            continue
        reason = re.sub(r'^[\s\-–—:]+', '', ids.group('reason'))
        if len(reason.split()) < MIN_REASON_WORDS:
            problems.append(
                f"{rel}:{line}: `# nosec {ids.group('ids')}` needs a reason of at least "
                f'{MIN_REASON_WORDS} words explaining why it is safe'
            )
    assert not problems, 'Unjustified bandit suppressions:\n' + '\n'.join(problems)


def test_nosec_counts_match_the_baseline():
    counts = collections.Counter(rel for rel, _, text in _nosec_comments() if _NOSEC.search(text))
    changes = []
    for rel in sorted(set(counts) | set(BASELINE)):
        have, pinned = counts.get(rel, 0), BASELINE.get(rel, 0)
        if have != pinned:
            changes.append(f'{rel}: {have} `# nosec` comment(s), baseline says {pinned}')
    assert not changes, (
        'The set of bandit suppressions changed. Prefer fixing the finding. If the suppression is '
        'justified, update BASELINE in tests/test_nosec_policy.py in the same change:\n' + '\n'.join(changes)
    )


def test_policy_rejects_bare_and_unexplained_markers():
    """The matchers themselves: guard against the policy silently accepting weak comments."""
    def verdict(comment):
        m = _NOSEC.search(comment)
        ids = _IDS.match(m.group('rest')) if m else None
        if not ids:
            return 'bare'
        reason = re.sub(r'^[\s\-–—:]+', '', ids.group('reason'))
        return 'ok' if len(reason.split()) >= MIN_REASON_WORDS else 'unexplained'

    assert verdict('# nosec') == 'bare'
    assert verdict('# nosec - trust me') == 'bare'
    assert verdict('# nosec B608') == 'unexplained'
    assert verdict('# nosec B608 - ok') == 'unexplained'
    assert verdict('# nosec B608 — identifiers pass validate_identifier first') == 'ok'
    assert verdict('# nosec:B105,B106 because values are public URLs') == 'ok'
