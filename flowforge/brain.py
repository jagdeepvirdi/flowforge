"""Brain attach gate.

FlowForge Core contains no AI/LLM logic. Optional AI diagnostics live in the separate
``flowforge-brain`` service (see ARCHITECTURE.md and docs/BRAIN_DECOUPLING_PLAN.md). Every
Core surface that would call it asks ``brain_enabled()`` first and stays dark when it is False.
"""
from flask import jsonify


def brain_enabled() -> bool:
    """True only when a Brain service is attached and reachable."""
    # TODO: Wire this to the new external Brain microservice API
    return False


def brain_unavailable_response():
    """503 response for any AI surface hit while no Brain is attached."""
    return jsonify({
        'error': 'brain_not_attached',
        'message': 'AI features require the Brain service. Set FLOWFORGE_BRAIN_URL.',
    }), 503
