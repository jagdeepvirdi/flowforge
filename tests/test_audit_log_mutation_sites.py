"""Pin every place in the code that modifies or deletes audit-log rows.

The audit log is *append-only in application code* — not immutable: the database does not
block UPDATE/DELETE (see docs/security.md, "Audit log integrity"). This test keeps that
claim honest. A new function that deletes or updates ``AuditLog`` rows, or raw SQL that
does so to ``ff_audit_log``, fails the build until it is reviewed and added to the
allowlist below with a reason.
"""
import ast
import re
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / 'flowforge'

# (file relative to flowforge/, function) -> why this site may modify audit rows
ALLOWED = {
    # The scheduler job, the API purge and the CLI purge all delegate to these two functions, which
    # open the database trigger's maintenance gate and keep the hash chain verifiable.
    ('audit_chain.py', 'prune'): 'retention: deletes old rows and appends a chained AUDIT_PRUNED checkpoint',
    ('audit_chain.py', 'anonymize_actor'): 'GDPR purge: blanks the actor fields of a deleted user, records AUDIT_ANONYMIZED',
}

_MUTATORS = {'delete', 'update', 'bulk_update_mappings', 'bulk_save_objects'}
_RAW_SQL = re.compile(r'\b(update|delete\s+from|truncate|drop\s+table|alter\s+table)\b[^;\'"]*\bff_audit_log\b', re.I)


def find_mutation_sites(source: str) -> set[str]:
    """Names of functions in ``source`` that reference AuditLog and call a mutating method,
    or that contain raw SQL modifying ff_audit_log. ('<module>' for module-level code.)"""
    tree = ast.parse(source)
    sites: set[str] = set()
    # Docstrings talk about UPDATE/DELETE in prose; only real statements count.
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                  and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str)}

    def scan(node, name):
        mentions = any(isinstance(n, ast.Name) and n.id == 'AuditLog' for n in ast.walk(node))
        calls = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _MUTATORS
                    for n in ast.walk(node))
        raw = any(isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
                  and _RAW_SQL.search(n.value) for n in ast.walk(node))
        if (mentions and calls) or raw:
            sites.add(name)

    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for f in funcs:
        scan(f, f.name)
    module_level = ast.Module(body=[n for n in tree.body
                                    if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))],
                              type_ignores=[])
    scan(module_level, '<module>')
    return sites


def _all_sites() -> set[tuple[str, str]]:
    found = set()
    for path in PKG.rglob('*.py'):
        rel = path.relative_to(PKG).as_posix()
        if rel.startswith('db/migrations/'):       # migrations create/alter the table; reviewed separately
            continue
        for name in find_mutation_sites(path.read_text(encoding='utf-8')):
            found.add((rel, name))
    return found


def test_only_known_functions_modify_audit_rows():
    unexpected = _all_sites() - set(ALLOWED)
    assert not unexpected, (
        f'New code modifies audit-log rows: {sorted(unexpected)}. The audit log must stay append-only '
        'in application code; if this is intentional, review it and add it to ALLOWED with a reason.'
    )


def test_allowlist_has_no_stale_entries():
    stale = set(ALLOWED) - _all_sites()
    assert not stale, f'ALLOWED lists sites that no longer modify the audit log (remove them): {sorted(stale)}'


# -- the scanner itself (mutation checks) -------------------------------------------------

def test_scanner_flags_orm_delete_and_update():
    assert find_mutation_sites('def f():\n    db.session.query(AuditLog).filter(x).delete()') == {'f'}
    assert find_mutation_sites('def g():\n    db.session.query(AuditLog).update({"a": 1})') == {'g'}


def test_scanner_flags_raw_sql():
    assert find_mutation_sites('def h(c):\n    c.execute("DELETE FROM ff_audit_log WHERE 1=1")') == {'h'}
    assert find_mutation_sites('def i(c):\n    c.execute("TRUNCATE ff_audit_log")') == {'i'}


def test_scanner_ignores_reads_inserts_and_other_tables():
    assert find_mutation_sites('def r():\n    return db.session.query(AuditLog).filter(x).all()') == set()
    assert find_mutation_sites('def w(conn):\n    conn.execute(insert(AuditLog).values(a=1))') == set()
    assert find_mutation_sites('def o():\n    db.session.query(PipelineRun).delete()') == set()
    assert find_mutation_sites('def s(c):\n    c.execute("SELECT * FROM ff_audit_log")') == set()


def test_scanner_ignores_docstrings_but_not_real_sql():
    prose = 'The trigger blocks UPDATE and DELETE on ff_audit_log.'
    only_docs = ('"""' + prose + '"""\n'
                 'def f():\n'
                 '    """' + prose + '"""\n'
                 '    return 1\n')
    assert find_mutation_sites(only_docs) == set()
    real = ('def f(c):\n'
            '    """' + prose + '"""\n'
            '    c.execute("DELETE FROM ff_audit_log")\n')
    assert find_mutation_sites(real) == {'f'}
