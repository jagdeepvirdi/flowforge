from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth
from flowforge.db.models import RecipientGroup, db

bp = Blueprint('recipients', __name__)


def _group_dict(g: RecipientGroup) -> dict:
    return {
        'id': g.id,
        'name': g.name,
        'description': g.description,
        'addresses': g.addresses or [],
        'created_at': g.created_at.isoformat() if g.created_at else None,
    }


@bp.get('/recipient-groups')
@require_auth
def list_groups():
    groups = db.session.query(RecipientGroup).order_by(RecipientGroup.name).all()
    return jsonify([_group_dict(g) for g in groups])


@bp.post('/recipient-groups')
@require_auth
def create_group():
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'name is required'}), 400
    if not data.get('addresses'):
        return jsonify({'error': 'addresses is required'}), 400

    group = RecipientGroup(
        name=data['name'],
        description=data.get('description', ''),
        addresses=data['addresses'],
    )
    db.session.add(group)
    db.session.commit()
    return jsonify(_group_dict(group)), 201


@bp.get('/recipient-groups/<uuid:group_id>')
@require_auth
def get_group(group_id):
    group = db.session.get(RecipientGroup, str(group_id))
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    return jsonify(_group_dict(group))


@bp.put('/recipient-groups/<uuid:group_id>')
@require_auth
def update_group(group_id):
    group = db.session.get(RecipientGroup, str(group_id))
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    data = request.get_json() or {}
    for field in ('name', 'description', 'addresses'):
        if field in data:
            setattr(group, field, data[field])

    db.session.commit()
    return jsonify(_group_dict(group))


@bp.delete('/recipient-groups/<uuid:group_id>')
@require_auth
def delete_group(group_id):
    group = db.session.get(RecipientGroup, str(group_id))
    if not group:
        return jsonify({'error': 'Group not found'}), 404
    db.session.delete(group)
    db.session.commit()
    return jsonify({'deleted': str(group_id)})
