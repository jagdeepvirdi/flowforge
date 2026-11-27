"""Audit log API endpoints."""
import csv
from io import StringIO

from flask import Blueprint, Response, jsonify, request

# ... (keep existing imports)
from sqlalchemy import desc

from flowforge.api.auth import require_role
from flowforge.db.models import AuditLog

bp = Blueprint('audit', __name__)

@bp.get('/audit-logs/verify/status')
@require_role('admin')
def verify_status():
    """Is the scheduled chain verification running and passing? (state ok/failed/stale/never/pending/disabled)"""
    from flowforge import audit_chain
    from flowforge.db.models import db
    with db.engine.connect() as conn:
        return jsonify(audit_chain.verification_status(conn))


@bp.get('/audit-logs/verify')
@require_role('admin')
def verify_audit_chain():
    """Recompute the audit hash chain (O(rows); streams, so memory stays flat).

    Query: ``anchor=<seq>:<hash>`` to also prove the chain was not cut back past a saved point.
    """
    from flowforge import audit_chain
    from flowforge.db.models import db
    try:
        with db.engine.connect() as conn:
            rep = audit_chain.verify(conn, anchor=request.args.get('anchor') or None)
    except ValueError:
        # fixed text, never the exception's own message (the only ValueError here is a malformed anchor)
        return jsonify({'error': 'anchor must look like "<seq>:<64 hex chars>" (the CHAIN line in the audit log)'}), 400
    return jsonify(rep.to_dict())


@bp.get('/audit-logs/export')
@require_role('admin')
def export_audit_logs():
    """Export filtered audit logs as CSV."""
    query = AuditLog.query

    # Filters
    action = request.args.get('action')
    if action:
        query = query.filter(AuditLog.action.ilike(f'%{action}%'))
    
    username = request.args.get('username')
    if username:
        query = query.filter(AuditLog.username.ilike(f'%{username}%'))
        
    user_id = request.args.get('user_id')
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    query = query.order_by(desc(AuditLog.timestamp))

    # Pre-fetch all rows within the request context so the generator
    # never needs a DB session after the response has been returned.
    rows = [
        (
            str(log.id),
            log.timestamp.isoformat() if log.timestamp else '',
            log.action,
            log.username,
            str(log.user_id) if log.user_id else '',
            log.ip_address or '',
            str(log.details),
        )
        for log in query.all()
    ]

    def generate():
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(['ID', 'Timestamp', 'Action', 'Username', 'User ID', 'IP Address', 'Details'])
        yield si.getvalue()
        si.seek(0)
        si.truncate(0)

        for row in rows:
            writer.writerow(row)
            yield si.getvalue()
            si.seek(0)
            si.truncate(0)

    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=audit_logs.csv'
    })

@bp.get('/audit-logs')
@require_role('admin')
def get_audit_logs():
    """Fetch paginated, filtered audit logs."""
    query = AuditLog.query

    # Filters
    action = request.args.get('action')
    if action:
        query = query.filter(AuditLog.action.ilike(f'%{action}%'))
    
    username = request.args.get('username')
    if username:
        query = query.filter(AuditLog.username.ilike(f'%{username}%'))
        
    user_id = request.args.get('user_id')
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    # Pagination
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
    except ValueError:
        return jsonify({'error': 'Invalid pagination parameters'}), 400

    query = query.order_by(desc(AuditLog.timestamp))
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'logs': [
            {
                'id': str(log.id),
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'action': log.action,
                'username': log.username,
                'user_id': str(log.user_id) if log.user_id else None,
                'ip_address': log.ip_address,
                'details': log.details,
            }
            for log in paginated.items
        ],
        'total': paginated.total,
        'page': paginated.page,
        'pages': paginated.pages,
    })
