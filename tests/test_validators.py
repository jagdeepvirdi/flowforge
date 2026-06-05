"""Unit tests for API input validators (FEAT-8).

Pure unit tests — no DB, no Flask app context required.
"""
from flowforge.api.validators import (
    _check_len,
    validate_connection,
    validate_email_config,
    validate_pipeline,
    validate_pipeline_step,
    validate_pipeline_variable,
    validate_project,
    validate_provider,
    validate_recipient_group,
    validate_report,
)

# ── _check_len ────────────────────────────────────────────────────────────────

def test_check_len_under_limit():
    assert _check_len('hello', 'name', 255) is None


def test_check_len_at_limit():
    assert _check_len('a' * 255, 'name', 255) is None


def test_check_len_over_limit():
    err = _check_len('a' * 256, 'name', 255)
    assert err is not None
    assert '255' in err
    assert '256' in err
    assert 'name' in err


def test_check_len_none_returns_none():
    assert _check_len(None, 'name', 100) is None


def test_check_len_empty_string_returns_none():
    assert _check_len('', 'name', 100) is None


def test_check_len_error_includes_field_name():
    err = _check_len('x' * 101, 'my_field', 100)
    assert 'my_field' in err


def test_check_len_error_includes_actual_length():
    value = 'x' * 150
    err = _check_len(value, 'col', 100)
    assert '150' in err


def test_check_len_single_char_over_limit():
    assert _check_len('ab', 'f', 1) is not None


def test_check_len_exactly_zero_limit():
    # Empty string passes (falsy → skipped); non-empty fails
    assert _check_len('', 'f', 0) is None
    assert _check_len('x', 'f', 0) is not None


# ── validate_pipeline ─────────────────────────────────────────────────────────

def test_validate_pipeline_all_valid():
    assert validate_pipeline({
        'name': 'My Pipeline',
        'description': 'Runs every morning',
        'schedule': '0 8 * * *',
    }) is None


def test_validate_pipeline_empty_dict_valid():
    assert validate_pipeline({}) is None


def test_validate_pipeline_name_at_limit():
    assert validate_pipeline({'name': 'n' * 255}) is None


def test_validate_pipeline_name_too_long():
    err = validate_pipeline({'name': 'n' * 256})
    assert err is not None
    assert 'name' in err


def test_validate_pipeline_description_too_long():
    err = validate_pipeline({'description': 'd' * 2001})
    assert err is not None
    assert 'description' in err


def test_validate_pipeline_schedule_too_long():
    err = validate_pipeline({'schedule': 's' * 101})
    assert err is not None
    assert 'schedule' in err


def test_validate_pipeline_returns_first_error_only():
    # name over-limit AND description over-limit → only first returned
    result = validate_pipeline({'name': 'n' * 256, 'description': 'd' * 2001})
    assert result is not None
    assert 'name' in result  # name is validated first


def test_validate_pipeline_none_values_ok():
    assert validate_pipeline({'name': None, 'description': None}) is None


# ── validate_pipeline_step ────────────────────────────────────────────────────

def test_validate_pipeline_step_valid():
    assert validate_pipeline_step({'name': 'Generate Report'}) is None


def test_validate_pipeline_step_at_limit():
    assert validate_pipeline_step({'name': 'n' * 255}) is None


def test_validate_pipeline_step_name_too_long():
    err = validate_pipeline_step({'name': 'n' * 256})
    assert err is not None
    assert 'name' in err


def test_validate_pipeline_step_no_name():
    assert validate_pipeline_step({}) is None


# ── validate_pipeline_variable ────────────────────────────────────────────────

def test_validate_pipeline_variable_valid():
    assert validate_pipeline_variable({'var_key': 'report_month'}) is None


def test_validate_pipeline_variable_at_limit():
    assert validate_pipeline_variable({'var_key': 'k' * 100}) is None


def test_validate_pipeline_variable_key_too_long():
    err = validate_pipeline_variable({'var_key': 'k' * 101})
    assert err is not None
    assert 'var_key' in err


def test_validate_pipeline_variable_missing_key():
    assert validate_pipeline_variable({}) is None


# ── validate_report ───────────────────────────────────────────────────────────

def test_validate_report_all_fields_valid():
    assert validate_report({
        'name': 'Monthly Revenue',
        'output_filename': 'report_{{ current_month }}.xlsx',
        'title': 'Revenue Summary',
        'sheet_name': 'Data',
        'template_path': '/templates/base.xlsx',
    }) is None


def test_validate_report_name_too_long():
    err = validate_report({'name': 'n' * 256})
    assert err is not None and 'name' in err


def test_validate_report_output_filename_at_limit():
    assert validate_report({'output_filename': 'f' * 500}) is None


def test_validate_report_output_filename_too_long():
    err = validate_report({'output_filename': 'f' * 501})
    assert err is not None and 'output_filename' in err


def test_validate_report_title_too_long():
    err = validate_report({'title': 't' * 256})
    assert err is not None and 'title' in err


def test_validate_report_sheet_name_too_long():
    err = validate_report({'sheet_name': 's' * 101})
    assert err is not None and 'sheet_name' in err


def test_validate_report_template_path_too_long():
    err = validate_report({'template_path': 'p' * 501})
    assert err is not None and 'template_path' in err


def test_validate_report_empty_dict_valid():
    assert validate_report({}) is None


# ── validate_email_config ─────────────────────────────────────────────────────

def test_validate_email_config_all_valid():
    assert validate_email_config({
        'name': 'Monthly Email',
        'subject': 'Your Report is Ready',
        'header_text': 'FlowForge Automated Report',
        'from_name': 'Reports Team',
    }) is None


def test_validate_email_config_name_too_long():
    err = validate_email_config({'name': 'n' * 256})
    assert err is not None and 'name' in err


def test_validate_email_config_subject_at_limit():
    assert validate_email_config({'subject': 's' * 500}) is None


def test_validate_email_config_subject_too_long():
    err = validate_email_config({'subject': 's' * 501})
    assert err is not None and 'subject' in err


def test_validate_email_config_header_text_too_long():
    err = validate_email_config({'header_text': 'h' * 501})
    assert err is not None and 'header_text' in err


def test_validate_email_config_from_name_too_long():
    err = validate_email_config({'from_name': 'f' * 256})
    assert err is not None and 'from_name' in err


# ── validate_recipient_group / connection / provider / project ────────────────

def test_validate_recipient_group_valid():
    assert validate_recipient_group({'name': 'Finance Team'}) is None


def test_validate_recipient_group_at_limit():
    assert validate_recipient_group({'name': 'n' * 100}) is None


def test_validate_recipient_group_too_long():
    err = validate_recipient_group({'name': 'n' * 101})
    assert err is not None and 'name' in err


def test_validate_connection_valid():
    assert validate_connection({'name': 'Production DB'}) is None


def test_validate_connection_too_long():
    err = validate_connection({'name': 'n' * 101})
    assert err is not None and 'name' in err


def test_validate_provider_valid():
    assert validate_provider({'name': 'Company Gmail'}) is None


def test_validate_provider_too_long():
    err = validate_provider({'name': 'n' * 101})
    assert err is not None and 'name' in err


def test_validate_project_valid():
    assert validate_project({'name': 'Finance Reports'}) is None


def test_validate_project_at_limit():
    assert validate_project({'name': 'n' * 100}) is None


def test_validate_project_too_long():
    err = validate_project({'name': 'n' * 101})
    assert err is not None and 'name' in err
