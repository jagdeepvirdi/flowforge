import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><style>
  body { font-family: Arial, sans-serif; font-size: 12px; }
  h1   { color: #333; }
  table { border-collapse: collapse; width: 100%; }
  th { background: #D9D9D9; font-weight: bold; padding: 6px; border: 1px solid #ccc; }
  td { padding: 5px; border: 1px solid #ddd; }
  tr:nth-child(even) { background: #f9f9f9; }
</style></head>
<body>
  <h1>{{ title }}</h1>
  <p>Generated: {{ generated_at }}</p>
  <table>
    <thead><tr>{% for col in columns %}<th>{{ col }}</th>{% endfor %}</tr></thead>
    <tbody>
      {% for row in rows %}
      <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""


def generate(
    rows: list[tuple],
    columns: list[str],
    output_path: Path,
    title: str = 'Report',
    template_path: Path | None = None,
) -> Path:
    """Render rows to a PDF via WeasyPrint. Install with: pip install flowforge[pdf]"""
    try:
        from weasyprint import HTML
    except ImportError:
        raise ImportError(
            "weasyprint is required for PDF reports: pip install flowforge[pdf]"
        )
    try:
        from jinja2 import BaseLoader, Environment, FileSystemLoader, select_autoescape
    except ImportError:
        raise ImportError("jinja2 is required: pip install jinja2")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if template_path and template_path.exists():
        env = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
            autoescape=select_autoescape(['html']),
        )
        tmpl = env.get_template(template_path.name)
    else:
        env = Environment(loader=BaseLoader(), autoescape=select_autoescape(['html']))
        tmpl = env.from_string(_DEFAULT_TEMPLATE)

    html_content = tmpl.render(
        title=title,
        columns=columns,
        rows=rows,
        generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )
    HTML(string=html_content).write_pdf(str(output_path))
    logger.info("PDF report written: %s (%d rows)", output_path, len(rows))
    return output_path
