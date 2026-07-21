"""Model-level tests for StepDependency (Phase 14 Option B, Milestone 1)."""
import pytest
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def pipeline_with_steps(app):
    """Create a pipeline with two steps directly via the ORM; clean up after."""
    from flowforge.db.models import Pipeline, PipelineStep, db

    with app.app_context():
        pipeline = Pipeline(name='Model Test Pipeline')
        db.session.add(pipeline)
        db.session.flush()
        step_a = PipelineStep(pipeline_id=pipeline.id, step_order=1, name='A', step_type='db_query', config={})
        step_b = PipelineStep(pipeline_id=pipeline.id, step_order=2, name='B', step_type='db_query', config={})
        db.session.add_all([step_a, step_b])
        db.session.commit()
        ids = (pipeline.id, step_a.id, step_b.id)

    yield ids

    with app.app_context():
        db.session.get(Pipeline, ids[0]) and db.session.delete(db.session.get(Pipeline, ids[0]))
        db.session.commit()


def test_valid_edge(app, pipeline_with_steps):
    from flowforge.db.models import StepDependency, db

    pipeline_id, step_a_id, step_b_id = pipeline_with_steps
    with app.app_context():
        dep = StepDependency(pipeline_id=pipeline_id, upstream_step_id=step_a_id, downstream_step_id=step_b_id)
        db.session.add(dep)
        db.session.commit()
        assert dep.id is not None


def test_self_reference_constraint(app, pipeline_with_steps):
    from flowforge.db.models import StepDependency, db

    pipeline_id, step_a_id, _ = pipeline_with_steps
    with app.app_context():
        dep = StepDependency(pipeline_id=pipeline_id, upstream_step_id=step_a_id, downstream_step_id=step_a_id)
        db.session.add(dep)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_duplicate_constraint(app, pipeline_with_steps):
    from flowforge.db.models import StepDependency, db

    pipeline_id, step_a_id, step_b_id = pipeline_with_steps
    with app.app_context():
        db.session.add(StepDependency(pipeline_id=pipeline_id, upstream_step_id=step_a_id, downstream_step_id=step_b_id))
        db.session.commit()
        db.session.add(StepDependency(pipeline_id=pipeline_id, upstream_step_id=step_a_id, downstream_step_id=step_b_id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_cascade_on_step_delete(app, pipeline_with_steps):
    from flowforge.db.models import PipelineStep, StepDependency, db

    pipeline_id, step_a_id, step_b_id = pipeline_with_steps
    with app.app_context():
        dep = StepDependency(pipeline_id=pipeline_id, upstream_step_id=step_a_id, downstream_step_id=step_b_id)
        db.session.add(dep)
        db.session.commit()
        dep_id = dep.id

        db.session.delete(db.session.get(PipelineStep, step_a_id))
        db.session.commit()

        assert db.session.get(StepDependency, dep_id) is None


def test_cascade_on_pipeline_delete(app, pipeline_with_steps):
    from flowforge.db.models import Pipeline, StepDependency, db

    pipeline_id, step_a_id, step_b_id = pipeline_with_steps
    with app.app_context():
        dep = StepDependency(pipeline_id=pipeline_id, upstream_step_id=step_a_id, downstream_step_id=step_b_id)
        db.session.add(dep)
        db.session.commit()
        dep_id = dep.id

        db.session.delete(db.session.get(Pipeline, pipeline_id))
        db.session.commit()

        assert db.session.get(StepDependency, dep_id) is None


def test_exists_for_pipeline_true_and_false(app, pipeline_with_steps):
    from flowforge.db.models import StepDependency, db

    pipeline_id, step_a_id, step_b_id = pipeline_with_steps
    with app.app_context():
        assert StepDependency.exists_for_pipeline(pipeline_id) is False

        db.session.add(StepDependency(pipeline_id=pipeline_id, upstream_step_id=step_a_id, downstream_step_id=step_b_id))
        db.session.commit()

        assert StepDependency.exists_for_pipeline(pipeline_id) is True


def test_step_dependencies_do_not_affect_loader_order(app, pipeline_with_steps):
    """Regression proof for the Phase 14 Option B backward-compatibility decision: a pipeline's
    execution order comes purely from step_order/parallel_group until Milestone 2's dual-path
    engine lands — StepDependency rows existing has zero effect on load_pipeline today, even an
    edge that (if honored) would reverse the order."""
    from flowforge.db.models import StepDependency, db
    from flowforge.engine.loader import load_pipeline

    pipeline_id, step_a_id, step_b_id = pipeline_with_steps
    with app.app_context():
        steps_before, _, _ = load_pipeline(pipeline_id)
        order_before = [s.name for s in steps_before]

        # B → A: if honored, this would reverse execution order. It must not, today.
        db.session.add(StepDependency(pipeline_id=pipeline_id, upstream_step_id=step_b_id, downstream_step_id=step_a_id))
        db.session.commit()

        steps_after, _, _ = load_pipeline(pipeline_id)
        order_after = [s.name for s in steps_after]

    assert order_before == order_after == ['A', 'B']
