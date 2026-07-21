"""Integration tests for runner.run_pipeline's dual-path engine gate
(Phase 14 Option B, Milestone 2): a pipeline_id with real StepDependency rows in the DB routes
execution to the DAG engine; a pipeline_id with none keeps using the wave engine untouched.
"""
from unittest.mock import patch

import pytest

from flowforge.steps.base import BaseStep, StepResult


class _MockStep(BaseStep):
    def run(self, ctx):
        return StepResult(success=True)


@pytest.fixture
def two_steps_no_dependency(app):
    from flowforge.db.models import Pipeline, PipelineStep, db

    with app.app_context():
        pipeline = Pipeline(name='DAG Gate — No Deps')
        db.session.add(pipeline)
        db.session.flush()
        s1 = PipelineStep(pipeline_id=pipeline.id, step_order=1, name='A', step_type='db_query', config={})
        s2 = PipelineStep(pipeline_id=pipeline.id, step_order=2, name='B', step_type='db_query', config={})
        db.session.add_all([s1, s2])
        db.session.commit()
        ids = (pipeline.id, s1.id, s2.id)

    yield ids

    with app.app_context():
        p = db.session.get(Pipeline, ids[0])
        if p:
            db.session.delete(p)
            db.session.commit()


@pytest.fixture
def two_steps_with_dependency(app, two_steps_no_dependency):
    from flowforge.db.models import StepDependency, db

    pipeline_id, s1_id, s2_id = two_steps_no_dependency
    with app.app_context():
        db.session.add(StepDependency(pipeline_id=pipeline_id, upstream_step_id=s1_id, downstream_step_id=s2_id))
        db.session.commit()

    return pipeline_id, s1_id, s2_id


def test_run_pipeline_uses_dag_engine_when_step_dependencies_exist(app, two_steps_with_dependency):
    from flowforge.engine.runner import run_pipeline

    pipeline_id, s1_id, s2_id = two_steps_with_dependency
    step_a = _MockStep(name='A', config={'_db_step_id': s1_id, '_db_step_order': 1})
    step_b = _MockStep(name='B', config={'_db_step_id': s2_id, '_db_step_order': 2})

    with app.app_context(), \
         patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('flowforge.engine.dag.run_dag') as mock_run_dag:
        run_pipeline('Test', [step_a, step_b], pipeline_id=pipeline_id)

    mock_run_dag.assert_called_once()
    call_steps, call_edges = mock_run_dag.call_args[0][0], mock_run_dag.call_args[0][1]
    assert {s.name for s in call_steps} == {'A', 'B'}
    assert (s1_id, s2_id) in call_edges


def test_run_pipeline_uses_wave_engine_when_no_step_dependencies(app, two_steps_no_dependency):
    from flowforge.engine.runner import run_pipeline

    pipeline_id, s1_id, s2_id = two_steps_no_dependency
    step_a = _MockStep(name='A', config={'_db_step_id': s1_id, '_db_step_order': 1})
    step_b = _MockStep(name='B', config={'_db_step_id': s2_id, '_db_step_order': 2})

    with app.app_context(), \
         patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'), \
         patch('flowforge.engine.dag.run_dag') as mock_run_dag:
        result = run_pipeline('Test', [step_a, step_b], pipeline_id=pipeline_id)

    mock_run_dag.assert_not_called()
    assert result.success is True
    assert result.steps_run == 2
