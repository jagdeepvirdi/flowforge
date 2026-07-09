"""Tests for the `flowforge cleanup` CLI command's --days 0 confirmation guard."""
import time

from click.testing import CliRunner

from flowforge.cli import cli


def _make_file(path, age_days=0):
    path.write_text('data')
    if age_days:
        old_time = time.time() - age_days * 86_400
        import os
        os.utime(path, (old_time, old_time))


def test_days_zero_without_yes_prompts_for_confirmation(tmp_path):
    _make_file(tmp_path / 'recent.txt')
    runner = CliRunner()
    result = runner.invoke(cli, ['cleanup', '--days', '0', '--dir', str(tmp_path)], input='n\n')
    assert 'Continue?' in result.output
    assert (tmp_path / 'recent.txt').exists()  # declined — nothing deleted
    assert result.exit_code != 0


def test_days_zero_confirmed_deletes_everything(tmp_path):
    _make_file(tmp_path / 'recent.txt')
    runner = CliRunner()
    result = runner.invoke(cli, ['cleanup', '--days', '0', '--dir', str(tmp_path)], input='y\n')
    assert result.exit_code == 0
    assert not (tmp_path / 'recent.txt').exists()


def test_days_zero_with_yes_flag_skips_prompt(tmp_path):
    _make_file(tmp_path / 'recent.txt')
    runner = CliRunner()
    result = runner.invoke(cli, ['cleanup', '--days', '0', '--dir', str(tmp_path), '--yes'])
    assert 'Continue?' not in result.output
    assert result.exit_code == 0
    assert not (tmp_path / 'recent.txt').exists()


def test_days_zero_dry_run_skips_prompt_and_deletes_nothing(tmp_path):
    _make_file(tmp_path / 'recent.txt')
    runner = CliRunner()
    result = runner.invoke(cli, ['cleanup', '--days', '0', '--dir', str(tmp_path), '--dry-run'])
    assert 'Continue?' not in result.output
    assert result.exit_code == 0
    assert (tmp_path / 'recent.txt').exists()


def test_nonzero_days_never_prompts(tmp_path):
    _make_file(tmp_path / 'old.txt', age_days=10)
    runner = CliRunner()
    result = runner.invoke(cli, ['cleanup', '--days', '5', '--dir', str(tmp_path)])
    assert 'Continue?' not in result.output
    assert result.exit_code == 0
    assert not (tmp_path / 'old.txt').exists()
