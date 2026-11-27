"""Guard the Dependabot policy (.github/dependabot.yml).

An invalid config does not fail loudly: Dependabot silently stops opening update PRs and the error only
shows on the repository's Insights tab. These offline checks pin the invariants that matter, including
the mistakes that would invalidate or quietly weaken the policy. (Schema validation against GitHub's
published schema was done by hand when the policy was written; it needs the network.)
"""
import re
from pathlib import Path

import pytest
import yaml

PATH = Path(__file__).resolve().parent.parent / '.github' / 'dependabot.yml'
RAW = PATH.read_text(encoding='utf-8')
CFG = yaml.safe_load(RAW)
BY = {u['package-ecosystem']: u for u in CFG['updates']}


def test_covers_every_ecosystem_the_repo_uses():
    assert CFG['version'] == 2
    assert set(BY) == {'pip', 'npm', 'github-actions', 'docker'}
    assert BY['pip']['directory'] == '/' and BY['npm']['directory'] == '/frontend'


@pytest.mark.parametrize('eco', ['pip', 'npm'])
def test_lock_files_are_refreshed_weekly_so_the_audit_gates_do_not_drift(eco):
    assert BY[eco]['schedule']['interval'] == 'weekly'


@pytest.mark.parametrize('eco', ['pip', 'npm'])
def test_patch_and_minor_updates_are_separate_so_a_risky_minor_cannot_block_safe_patches(eco):
    groups = BY[eco]['groups']
    assert len(groups) == 2
    assert sorted(t for g in groups.values() for t in g['update-types']) == ['minor', 'patch']
    assert all(len(g['update-types']) == 1 for g in groups.values())


def test_sqlalchemy_21_is_held_back_but_patch_releases_still_flow():
    [rule] = [i for i in BY['pip']['ignore'] if i['dependency-name'] == 'sqlalchemy']
    assert set(rule['update-types']) == {'version-update:semver-minor', 'version-update:semver-major'}
    assert 'version-update:semver-patch' not in rule['update-types']


def test_every_ignore_rule_uses_the_prefixed_update_type_dependabot_requires():
    """`minor` instead of `version-update:semver-minor` makes the whole file invalid."""
    for eco, upd in BY.items():
        for rule in upd.get('ignore', []):
            assert rule['update-types'], (eco, rule)
            for t in rule['update-types']:
                assert re.fullmatch(r'version-update:semver-(major|minor|patch)', t), (eco, rule['dependency-name'], t)


def test_the_python_base_image_is_not_moved_automatically_but_digest_refreshes_still_arrive():
    [rule] = BY['docker']['ignore']
    assert rule['dependency-name'] == 'python'
    assert set(rule['update-types']) == {'version-update:semver-major', 'version-update:semver-minor'}


def test_every_ignore_rule_records_why_and_how_to_lift_it():
    """An ignore with no reason is how a held-back dependency gets forgotten."""
    lines = RAW.splitlines()
    rules = [i for i, ln in enumerate(lines) if ln.strip().startswith('- dependency-name:')]
    assert len(rules) == 3
    for i in rules:
        above = []
        j = i - 1
        while j >= 0 and lines[j].strip().startswith('#'):
            above.append(lines[j])
            j -= 1
        assert len(above) >= 2, f'ignore rule on line {i + 1} has no explanatory comment above it'
        assert any(re.search(r'remove|move|lift|until|then', ln, re.I) for ln in above), \
            f'ignore rule on line {i + 1} does not say when to lift it'


def test_nothing_is_blanket_ignored():
    for upd in BY.values():
        for rule in upd.get('ignore', []):
            assert rule['dependency-name'] not in ('*', ''), 'a blanket ignore hides every update'
            assert '*' not in rule['dependency-name']
