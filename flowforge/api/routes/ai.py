"""AI route shells.

FlowForge Core has no AI logic; these endpoints exist so the URLs stay stable and answer
``503 brain_not_attached`` until the external Brain service is wired in (see
docs/BRAIN_DECOUPLING_PLAN.md). Auth and rate limits are kept so the contract does not change.
"""
from flask import Blueprint

from flowforge.api.app import limiter
from flowforge.api.auth import require_auth
from flowforge.brain import brain_unavailable_response

bp = Blueprint('ai', __name__)


@bp.post('/ai/data-profile')
@require_auth
@limiter.limit('20 per minute')
def data_profile():
    # TODO: Wire this to the new external Brain microservice API
    return brain_unavailable_response()


@bp.post('/ai/chart-config')
@require_auth
@limiter.limit('20 per minute')
def chart_config():
    # TODO: Wire this to the new external Brain microservice API
    return brain_unavailable_response()


@bp.post('/ai/query')
@require_auth
@limiter.limit('20 per minute')
def ai_query():
    # TODO: Wire this to the new external Brain microservice API
    return brain_unavailable_response()


@bp.post('/ai/anomaly-narrative')
@require_auth
@limiter.limit('20 per minute')
def anomaly_narrative():
    # TODO: Wire this to the new external Brain microservice API
    return brain_unavailable_response()
