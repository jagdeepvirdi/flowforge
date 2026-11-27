"""Keyed tokenization of subscriber identifiers, and its use by the reconcile step."""
import hashlib
from unittest.mock import patch

import pytest

from flowforge.steps.reconcile import ReconcileStep
from flowforge.tokenization import TokenizationError, check_ready, scrub_text, tokenize

KEY_A = 'aa' * 32
KEY_B = 'bb' * 32


@pytest.fixture(autouse=True)
def _keys(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_SECRET_KEY', KEY_A)
    monkeypatch.delenv('FLOWFORGE_TOKEN_KEY', raising=False)


# -- library ------------------------------------------------------------------------------

def test_deterministic_and_well_formed():
    t = tokenize('15550001234')
    assert t == tokenize('15550001234')
    assert t.startswith('tk_msisdn_') and len(t) == len('tk_msisdn_') + 32
    assert tokenize('15550001234') != tokenize('15550001235')


def test_token_does_not_contain_or_unkeyed_hash_the_value():
    value = '15550001234'
    t = tokenize(value)
    assert value not in t
    # the whole point: an unsalted hash would let anyone enumerate the number space
    assert hashlib.sha256(value.encode()).hexdigest()[:32] not in t
    assert hashlib.md5(value.encode()).hexdigest() not in t  # noqa: S324 - negative check only


def test_msisdn_and_imsi_normalise_to_digits():
    assert tokenize('+1 (555) 000-1234') == tokenize('15550001234')
    assert tokenize(' 15550001234 ', 'msisdn') == tokenize(15550001234)
    assert tokenize('001010000000001', 'imsi') == tokenize('00101 0000 000001', 'imsi')


def test_generic_kind_only_trims():
    assert tokenize(' Ab-1 ', 'generic') == tokenize('Ab-1', 'generic')
    assert tokenize('ab-1', 'generic') != tokenize('Ab-1', 'generic')


def test_kinds_are_domain_separated():
    digits = '15550001234'
    assert len({tokenize(digits, 'msisdn'), tokenize(digits, 'imsi'), tokenize(digits, 'generic')}) == 3


def test_different_keys_give_different_tokens(monkeypatch):
    a = tokenize('15550001234')
    monkeypatch.setenv('FLOWFORGE_SECRET_KEY', KEY_B)
    assert tokenize('15550001234') != a


def test_explicit_token_key_overrides_and_is_not_the_encryption_key(monkeypatch):
    derived = tokenize('15550001234')
    monkeypatch.setenv('FLOWFORGE_TOKEN_KEY', KEY_B)
    explicit = tokenize('15550001234')
    assert explicit != derived
    monkeypatch.setenv('FLOWFORGE_TOKEN_KEY', KEY_A)       # same bytes as the secret key
    assert tokenize('15550001234') != derived              # HKDF output is not the raw secret


def test_empty_values_stay_empty():
    assert tokenize('') == '' and tokenize(None) == '' and tokenize('  ') == ''
    assert tokenize('abc', 'msisdn') == ''                 # no digits at all -> nothing to tokenize


def test_missing_or_bad_key_fails_closed(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_SECRET_KEY')
    with pytest.raises(TokenizationError):
        tokenize('15550001234')
    with pytest.raises(TokenizationError):
        check_ready()
    monkeypatch.setenv('FLOWFORGE_TOKEN_KEY', 'not-hex')
    with pytest.raises(TokenizationError):
        tokenize('1')
    monkeypatch.setenv('FLOWFORGE_TOKEN_KEY', 'ab' * 8)    # hex but only 8 bytes
    with pytest.raises(TokenizationError):
        tokenize('1')


def test_unknown_kind_rejected():
    with pytest.raises(TokenizationError):
        tokenize('1', 'iccid')


def test_scrub_text_replaces_emails_and_numbers_only():
    out = scrub_text('Contact Jo@Example.com about 15550001234 and +447700900123 (case 42, 2 retries)')
    assert 'example.com' not in out.lower() and '15550001234' not in out and '447700900123' not in out
    assert 'case 42' in out and '2 retries' in out         # short numbers and words are kept
    assert out.count('tk_') == 3
    assert scrub_text('Jo@Example.com') == scrub_text('jo@example.com')
    assert scrub_text(None) == '' and scrub_text('plain text') == 'plain text'


# -- reconcile integration ----------------------------------------------------------------

class FakeConn:
    def __init__(self, columns, rows):
        self.columns, self.rows = columns, rows
        self.queried = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute_query_with_columns_chunked(self, sql, params=(), chunk_size=5000):
        self.queried = True
        return self.columns, iter(self.rows)


def _run(config, left, right, left_cols=('k',), right_cols=('k',)):
    cfg = {'left_connection_id': 'L', 'right_connection_id': 'R',
           'left_query': 'SELECT k FROM l', 'right_query': 'SELECT k FROM r', **config}
    conns = {'L': FakeConn(list(left_cols), left), 'R': FakeConn(list(right_cols), right)}
    with patch.object(ReconcileStep, '_open', lambda self, cid: conns[cid]):
        return ReconcileStep('recon', cfg).run({'steps': {}}), conns


LEFT = [('15550000001',), ('15550000002',), ('15550000003',)]
RIGHT = [('15550000002',), ('15550000003',), ('15550000004',)]


def test_default_keeps_raw_keys():
    r, _ = _run({}, LEFT, RIGHT)
    assert {x['key'] for x in r.rows} == {'15550000001', '15550000004'}


def test_tokenize_keys_hides_raw_identifiers_but_not_counts():
    plain, _ = _run({}, LEFT, RIGHT)
    r, _ = _run({'tokenize_keys': True}, LEFT, RIGHT)
    assert r.success
    assert r.output_variables == plain.output_variables           # matching is unaffected
    assert {x['key'] for x in r.rows} == {tokenize('15550000001'), tokenize('15550000004')}
    blob = repr(r.rows) + r.table_html + r.logs
    assert '1555000000' not in blob                               # nothing raw anywhere in the result


def test_tokenized_keys_cover_value_mismatches():
    r, _ = _run({'compare': 'values', 'tokenize_keys': True},
                [('15550000001', 10)], [('15550000001', 99)], ('k', 'v'), ('k', 'v'))
    assert [x['key'] for x in r.rows] == [tokenize('15550000001')]
    assert r.rows[0]['issue'] == 'value_mismatch'


def test_token_kind_is_used_and_validated():
    r, _ = _run({'tokenize_keys': True, 'token_kind': 'imsi'}, LEFT, RIGHT)
    assert all(x['key'].startswith('tk_imsi_') for x in r.rows)
    bad, _ = _run({'tokenize_keys': True, 'token_kind': 'nope'}, LEFT, RIGHT)
    assert not bad.success and 'token_kind' in bad.error


def test_tokenize_keys_without_a_key_fails_before_any_query(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_SECRET_KEY')
    r, conns = _run({'tokenize_keys': True}, LEFT, RIGHT)
    assert not r.success and 'tokenize_keys' in r.error
    assert not conns['L'].queried and not conns['R'].queried      # no data was read, nothing leaked
    assert r.rows == []
