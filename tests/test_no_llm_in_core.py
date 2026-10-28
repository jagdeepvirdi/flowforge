"""Guard: Core (Muscle) must contain no LLM SDK imports or dependencies.

All AI/LLM logic lives in the external ``flowforge-brain`` service (see ARCHITECTURE.md).
"""
import ast
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DENIED_MODULES = {
    'anthropic', 'openai', 'google.generativeai', 'google.genai', 'vertexai',
    'langchain', 'langchain_core', 'langchain_openai', 'litellm', 'ollama',
    'cohere', 'mistralai', 'transformers',
}
DENIED_DISTS = {
    'anthropic', 'openai', 'google-generativeai', 'google-genai', 'google-cloud-aiplatform',
    'langchain', 'litellm', 'ollama', 'cohere', 'mistralai', 'transformers',
}


def _is_denied(module: str) -> bool:
    return any(module == d or module.startswith(d + '.') for d in DENIED_MODULES)


def test_no_llm_sdk_imports_in_flowforge_package():
    offenders = []
    for path in (ROOT / 'flowforge').rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            else:
                continue
            offenders += [f'{path.relative_to(ROOT)}:{node.lineno} imports {n}'
                          for n in names if _is_denied(n)]
    assert not offenders, 'LLM SDK imports found in Core:\n' + '\n'.join(offenders)


def _dist_name(spec: str) -> str:
    return re.split(r'[\s\[<>=!~;@]', spec.strip(), maxsplit=1)[0].lower().replace('_', '-')


def test_no_llm_dependencies_declared():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    specs = list(project.get('dependencies', []))
    for extra in project.get('optional-dependencies', {}).values():
        specs += extra
    declared = {_dist_name(s) for s in specs}
    assert not declared & DENIED_DISTS, f'LLM dependencies declared: {sorted(declared & DENIED_DISTS)}'
