"""Downstream pipeline-dependency fan-out, fired after a pipeline succeeds."""
import logging

logger = logging.getLogger(__name__)


def _trigger_downstream_pipelines(pipeline_id: str) -> None:
    """After a successful run, check and launch eligible downstream pipelines.

    A downstream pipeline is eligible when ALL its upstream dependencies have
    a successful run that completed after the downstream's last run started
    (or ever, if the downstream has never run).
    """
    try:
        from flowforge.db.models import Pipeline, PipelineDependency, PipelineRun, db
        from flowforge.engine.launcher import launch_run

        # Find all downstream pipelines that list this pipeline as an upstream
        fanout = db.session.query(PipelineDependency).filter_by(upstream_id=pipeline_id).all()
        if not fanout:
            return

        for dep in fanout:
            downstream_id = dep.downstream_id
            downstream = db.session.get(Pipeline, downstream_id)
            if not downstream or not downstream.enabled:
                continue

            # When did downstream last run?
            last_run = (
                db.session.query(PipelineRun)
                .filter_by(pipeline_id=downstream_id)
                .order_by(PipelineRun.started_at.desc())
                .first()
            )
            since = last_run.started_at if last_run else None

            # Check ALL upstreams of that downstream have a success run after `since`
            all_upstream_deps = (
                db.session.query(PipelineDependency)
                .filter_by(downstream_id=downstream_id)
                .all()
            )
            all_satisfied = True
            for up_dep in all_upstream_deps:
                q = (
                    db.session.query(PipelineRun)
                    .filter_by(pipeline_id=up_dep.upstream_id, status='success')
                )
                if since is not None:
                    q = q.filter(PipelineRun.finished_at > since)
                if not q.first():
                    all_satisfied = False
                    break

            if all_satisfied:
                logger.info(
                    "Dependency trigger: launching '%s' (all upstreams satisfied)",
                    downstream.name,
                )
                try:
                    launch_run(downstream, triggered_by='dependency')
                except Exception:
                    logger.exception("Failed to trigger downstream pipeline '%s'", downstream.name)
    except Exception:
        logger.exception("Error in _trigger_downstream_pipelines for pipeline %s", pipeline_id)
