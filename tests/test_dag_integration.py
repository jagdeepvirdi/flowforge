"""Integration tests for the DAG execution engine through the full `run_pipeline`
stack with a real DB (Phase 14 Option B, Milestone 4).

Complements, does not duplicate:
  - test_dag_engine.py — 12 unit tests against run_dag() directly, _write_step_run
    mocked out, no DB.
  - test_runner_dag_gate.py — 2 integration tests proving only the engine-selection
    gate itself (which path gets called).
This file proves the branch-scoped `on_error='stop'` semantics, ancestors-only
context visibility, and real concurrency hold up through the actual `run_pipeline`
entry point with real `StepDependency` rows and real `StepRun`/`PipelineRun`
database writes — the persistence layer, not just in-memory return values.
"""
import time
import uuid

import pytest

from flowforge.steps.base import BaseStep, StepResult


def make_step(name, step_id, step_order, on_error='stop', run_fn=None,
              success=True, error_msg='step failed', output_variables=None):
    if run_fn is None:
        result = StepResult(success=success, error='' if success else error_msg,
                            output_variables=output_variables or {})

        def run_fn(ctx):
            return result

    class MockStep(BaseStep):
        def run(self, ctx):
            return run_fn(ctx)

    cfg = {'on_error': on_error, '_db_step_order': step_order, '_db_step_id': step_id}
    return MockStep(name=name, config=cfg)


@pytest.fixture
def dag_pipeline(app):
    """Factory fixture: build a real pipeline with N named steps in the test DB.

    Returns `make(names) -> (pipeline_id, {name: step_id})`. Every pipeline created
    via `make` is deleted on teardown (steps and step-dependency edges cascade;
    pipeline_runs/step_runs are orphaned with pipeline_id set NULL, matching the
    existing test_runner_dag_gate.py cleanup convention).
    """
    from flowforge.db.models import Pipeline, PipelineStep, db

    created_pipeline_ids = []

    def make(names):
        with app.app_context():
            pipeline = Pipeline(name=f'DAG Integration — {"-".join(names)} — {uuid.uuid4().hex[:8]}')
            db.session.add(pipeline)
            db.session.flush()
            steps = {}
            for i, name in enumerate(names, start=1):
                s = PipelineStep(pipeline_id=pipeline.id, step_order=i, name=name,
                                 step_type='db_query', config={})
                db.session.add(s)
                steps[name] = s
            db.session.flush()
            ids = {name: s.id for name, s in steps.items()}
            pipeline_id = pipeline.id
            db.session.commit()
        created_pipeline_ids.append(pipeline_id)
        return pipeline_id, ids

    yield make

    with app.app_context():
        for pid in created_pipeline_ids:
            p = db.session.get(Pipeline, pid)
            if p:
                db.session.delete(p)
        db.session.commit()


def add_edges(app, pipeline_id, edges):
    """edges: list of (upstream_step_id, downstream_step_id)."""
    from flowforge.db.models import StepDependency, db
    with app.app_context():
        for up, down in edges:
            db.session.add(StepDependency(pipeline_id=pipeline_id, upstream_step_id=up, downstream_step_id=down))
        db.session.commit()


# ── DAG-mode counterparts of test_runner.py's "stop halts everything" tests ────
# (test_on_error_stop_halts_pipeline / test_on_error_stop_first_step) — those stay
# unmodified and prove the wave engine still halts every remaining step; these
# prove the DAG engine's branch-scoped replacement, end to end through real
# StepRun rows, not just the in-memory PipelineResult.

def test_partial_branch_failure_writes_correct_step_run_statuses(app, dag_pipeline):
    """A (stop, fails) -> B; C is an independent root. Wave-mode's counterpart
    (test_on_error_stop_halts_pipeline) would never even attempt C. Here C must
    complete successfully and get a real 'success' StepRun row, while B gets a
    real 'skipped' row instead of never being written at all.
    """
    from flowforge.engine.runner import run_pipeline

    pipeline_id, ids = dag_pipeline(['a', 'b', 'c'])
    add_edges(app, pipeline_id, [(ids['a'], ids['b'])])  # c is independent

    a = make_step('a', ids['a'], 1, on_error='stop', success=False, error_msg='boom')
    b = make_step('b', ids['b'], 2)
    c = make_step('c', ids['c'], 3)

    with app.app_context():
        result = run_pipeline('Test', [a, b, c], pipeline_id=pipeline_id)

        assert result.success is False
        assert result.error_step == 'a'

        from flowforge.db.models import PipelineRun, StepRun, db
        run_record = db.session.query(PipelineRun).filter_by(id=result.run_id).one()
        assert run_record.status == 'failed'
        assert run_record.error_step == 'a'

        step_runs = {
            sr.step_name: sr
            for sr in db.session.query(StepRun).filter_by(pipeline_run_id=result.run_id).all()
        }
        assert step_runs['a'].status == 'failed'
        assert step_runs['b'].status == 'skipped'
        assert step_runs['c'].status == 'success'


def test_partial_branch_failure_skips_multi_level_descendants_only(app, dag_pipeline):
    """A (stop, fails) -> B -> C; D is an independent root. Descendants B and C
    must both be skipped (transitively, not just the direct child); D must
    complete — mirrors test_dag_engine.py's multi-level unit test, but here through
    real DB StepRun rows written by the real runner.run_pipeline path.
    """
    from flowforge.engine.runner import run_pipeline

    pipeline_id, ids = dag_pipeline(['a', 'b', 'c', 'd'])
    add_edges(app, pipeline_id, [(ids['a'], ids['b']), (ids['b'], ids['c'])])  # d independent

    a = make_step('a', ids['a'], 1, on_error='stop', success=False)
    b = make_step('b', ids['b'], 2)
    c = make_step('c', ids['c'], 3)
    d = make_step('d', ids['d'], 4)

    with app.app_context():
        result = run_pipeline('Test', [a, b, c, d], pipeline_id=pipeline_id)

        from flowforge.db.models import StepRun, db
        step_runs = {
            sr.step_name: sr
            for sr in db.session.query(StepRun).filter_by(pipeline_run_id=result.run_id).all()
        }
        assert step_runs['a'].status == 'failed'
        assert step_runs['b'].status == 'skipped'
        assert step_runs['c'].status == 'skipped'
        assert step_runs['d'].status == 'success'


# ── Real concurrency, proven at the persistence layer ───────────────────────────

def test_independent_branches_real_overlap_recorded_in_db(app, dag_pipeline):
    """Two independent DAG roots (zero edges between them, zero shared
    parallel_group — DAG mode ignores parallel_group entirely) each sleep; their
    real started_at/finished_at StepRun timestamps must overlap. This is stronger
    proof than test_dag_engine.py's wall-clock-elapsed check: it confirms genuine
    concurrency survives all the way to what gets persisted to the DB.

    x -> y is an unrelated edge included solely so the pipeline has at least one
    StepDependency row: `StepDependency.exists_for_pipeline` is the dual-path gate
    runner.run_pipeline branches on, and it's pipeline-wide, not pair-wide — a
    pipeline with *zero* edges anywhere falls back to the wave engine entirely
    (byte-for-byte, per the Milestone 1 backward-compat decision), which would
    silently make this a same-process-sequential test instead of a DAG-engine one.
    """
    from flowforge.engine.runner import run_pipeline

    pipeline_id, ids = dag_pipeline(['a', 'b', 'x', 'y'])
    add_edges(app, pipeline_id, [(ids['x'], ids['y'])])

    def sleepy(ctx):
        time.sleep(0.3)
        return StepResult(success=True)

    a = make_step('a', ids['a'], 1, run_fn=sleepy)
    b = make_step('b', ids['b'], 2, run_fn=sleepy)
    x = make_step('x', ids['x'], 3)
    y = make_step('y', ids['y'], 4)

    with app.app_context():
        result = run_pipeline('Test', [a, b, x, y], pipeline_id=pipeline_id)
        assert result.success is True

        from flowforge.db.models import StepRun, db
        runs = {
            sr.step_name: sr
            for sr in db.session.query(StepRun).filter_by(pipeline_run_id=result.run_id).all()
        }
        a_run, b_run = runs['a'], runs['b']
        # Real overlap: each step started before the other finished.
        assert a_run.started_at < b_run.finished_at
        assert b_run.started_at < a_run.finished_at


# ── Ancestors-only context, proven through real Jinja rendering ────────────────

def test_context_ancestors_only_resolves_correctly_through_jinja(app, dag_pipeline):
    """C depends on A only; B is an independent sibling. Proves ancestors-only
    context visibility (test_dag_engine.py::test_context_only_exposes_transitive_ancestors)
    holds through the real `engine.context.render()` Jinja path actual steps use to
    resolve their config, not just raw dict access.
    """
    from flowforge.engine.context import render
    from flowforge.engine.runner import run_pipeline

    pipeline_id, ids = dag_pipeline(['a', 'b', 'c'])
    add_edges(app, pipeline_id, [(ids['a'], ids['c'])])  # c depends on a only

    seen = {}

    a = make_step('a', ids['a'], 1, output_variables={'a_var': 'from_a'})
    b = make_step('b', ids['b'], 2, output_variables={'b_var': 'from_b'})

    def c_run(ctx):
        seen['a_rendered'] = render('{{ a_var }}', ctx)
        seen['b_rendered'] = render('{{ b_var }}', ctx)
        seen['a_step_entry'] = render('{{ steps.a.rows_affected }}', ctx)
        seen['b_in_steps'] = 'b' in ctx.get('steps', {})
        return StepResult(success=True)

    c = make_step('c', ids['c'], 3, run_fn=c_run)

    with app.app_context():
        result = run_pipeline('Test', [a, b, c], pipeline_id=pipeline_id)
        assert result.success is True

    assert seen['a_rendered'] == 'from_a'
    assert seen['b_rendered'] == ''       # sibling's output_variable is invisible (Undefined -> '')
    assert seen['a_step_entry'] == '0'    # ancestor's steps.* entry is visible
    assert seen['b_in_steps'] is False    # sibling never enters context['steps'] at all
