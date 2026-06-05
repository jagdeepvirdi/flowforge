"""Tests for ScriptReportStep."""
from unittest.mock import patch

from flowforge.steps.script_report import ScriptReportStep


def test_script_report_csv_parsing(tmp_path):
    csv_data = "id,name\n1,Alice\n2,Bob"
    config = {
        'data_var': 'my_data',
        'data_format': 'csv',
        'format': 'csv',
        'output_filename': 'test.csv'
    }
    step = ScriptReportStep(name='report', config=config)
    
    context = {'my_data': csv_data}
    
    with patch('flowforge.reports.csv_report.generate') as mock_gen:
        result = step.run(context)
        
    assert result.success
    assert result.rows_affected == 2
    mock_gen.assert_called_once()
    rows, cols, path = mock_gen.call_args[0]
    assert cols == ['id', 'name']
    assert rows == [('1', 'Alice'), ('2', 'Bob')]


def test_script_report_json_parsing(tmp_path):
    json_data = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'}
    ]
    config = {
        'data_var': 'my_data',
        'data_format': 'json',
        'format': 'json',
        'output_filename': 'test.json'
    }
    step = ScriptReportStep(name='report', config=config)
    
    context = {'my_data': json_data}
    
    with patch('flowforge.reports.json_report.generate') as mock_gen:
        result = step.run(context)
        
    assert result.success
    assert result.rows_affected == 2
    mock_gen.assert_called_once()
    rows, cols, path = mock_gen.call_args[0]
    assert cols == ['id', 'name']
    assert rows == [(1, 'Alice'), (2, 'Bob')]


def test_script_report_json_string_parsing():
    json_str = '[{"id": 1, "name": "Alice"}]'
    config = {
        'data_var': 'my_data',
        'data_format': 'json',
        'format': 'csv',
        'output_filename': 'test.csv'
    }
    step = ScriptReportStep(name='report', config=config)
    
    with patch('flowforge.reports.csv_report.generate'):
        result = step.run({'my_data': json_str})
        
    assert result.success
    assert result.rows_affected == 1


def test_script_report_missing_data_var():
    step = ScriptReportStep(name='report', config={})
    result = step.run({})
    assert not result.success
    assert 'data_var is required' in result.error


def test_script_report_empty_data():
    step = ScriptReportStep(name='report', config={'data_var': 'x'})
    result = step.run({'x': ''})
    assert not result.success
    assert 'empty or not found' in result.error
