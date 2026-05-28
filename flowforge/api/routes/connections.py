from flask import Blueprint, jsonify, request

import flowforge.audit as audit
from flowforge.api.auth import require_auth, require_role
from flowforge.api.validators import validate_connection
from flowforge.crypto import decrypt_config, encrypt_config
from flowforge.db.models import DbConnection, db

bp = Blueprint('connections', __name__)

_SENSITIVE = {'password', 'token', 'secret', 'key'}


def _connection_dict(c: DbConnection, include_config: bool = False) -> dict:
    result = {
        'id': c.id,
        'name': c.name,
        'db_type': c.db_type,
        'is_default': c.is_default,
        'created_at': c.created_at.isoformat() if c.created_at else None,
    }
    if include_config:
        cfg = decrypt_config(c.config)
        # Mask sensitive values
        result['config'] = {
            k: '***' if any(s in k.lower() for s in _SENSITIVE) else v
            for k, v in cfg.items()
        }
    return result


@bp.get('/db-connections')
@require_auth
def list_connections():
    conns = db.session.query(DbConnection).order_by(DbConnection.name).all()
    return jsonify([_connection_dict(c) for c in conns])


@bp.post('/db-connections')
@require_role('admin')
def create_connection():
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'name is required'}), 400
    err = validate_connection(data)
    if err:
        return jsonify({'error': err}), 400
    _VALID_TYPES = {'postgresql', 'oracle', 'mysql'}
    if data.get('db_type') not in _VALID_TYPES:
        return jsonify({'error': f'db_type must be one of: {", ".join(sorted(_VALID_TYPES))}'}), 400
    if not data.get('config'):
        return jsonify({'error': 'config is required'}), 400

    conn = DbConnection(
        name=data['name'],
        db_type=data['db_type'],
        config=encrypt_config(data['config']),
        is_default=data.get('is_default', False),
    )
    db.session.add(conn)
    db.session.commit()
    audit.log_connection_change('CREATED', conn.name, conn.id)
    return jsonify(_connection_dict(conn)), 201


@bp.get('/db-connections/<uuid:conn_id>')
@require_auth
def get_connection(conn_id):
    conn = db.session.get(DbConnection, str(conn_id))
    if not conn:
        return jsonify({'error': 'Connection not found'}), 404
    return jsonify(_connection_dict(conn, include_config=True))


@bp.put('/db-connections/<uuid:conn_id>')
@require_role('admin')
def update_connection(conn_id):
    conn = db.session.get(DbConnection, str(conn_id))
    if not conn:
        return jsonify({'error': 'Connection not found'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        conn.name = data['name']
    if 'is_default' in data:
        conn.is_default = data['is_default']
    if 'config' in data:
        existing = decrypt_config(conn.config)
        # Merge: don't overwrite masked fields the client sent back as ***
        for k, v in data['config'].items():
            if v != '***':
                existing[k] = v
        conn.config = encrypt_config(existing)

    db.session.commit()
    audit.log_connection_change('UPDATED', conn.name, conn.id)
    return jsonify(_connection_dict(conn, include_config=True))


@bp.delete('/db-connections/<uuid:conn_id>')
@require_role('admin')
def delete_connection(conn_id):
    conn = db.session.get(DbConnection, str(conn_id))
    if not conn:
        return jsonify({'error': 'Connection not found'}), 404
    name, cid = conn.name, conn.id
    db.session.delete(conn)
    db.session.commit()
    audit.log_connection_change('DELETED', name, cid)
    return jsonify({'deleted': str(conn_id)})


@bp.post('/db-connections/test-raw')
@require_auth
def test_connection_raw():
    """Test a connection using raw credentials (before saving)."""
    import time
    data = request.get_json() or {}
    db_type = data.get('db_type')
    cfg = data.get('config', {})
    try:
        if db_type == 'postgresql':
            import psycopg2
            start = time.monotonic()
            conn = psycopg2.connect(
                host=cfg.get('host', 'localhost'),
                port=int(cfg.get('port', 5432)),
                database=cfg.get('database', ''),
                user=cfg.get('username') or cfg.get('user', ''),
                password=cfg.get('password', ''),
                connect_timeout=5,
                options='-c TimeZone=UTC',
            )
            conn.close()
            latency_ms = int((time.monotonic() - start) * 1000)
            return jsonify({'success': True, 'latency_ms': latency_ms})
        if db_type == 'oracle':
            try:
                import oracledb
            except ModuleNotFoundError:
                return jsonify({'success': False, 'error': 'oracledb is not installed. Run: pip install "flowforge[oracle]"'}), 400
            host         = cfg.get('host', 'localhost')
            port         = int(cfg.get('port', 1521))
            service_name = cfg.get('service_name') or cfg.get('database', '')
            user         = cfg.get('username') or cfg.get('user', '')
            password     = cfg.get('password', '')
            start = time.monotonic()
            conn = oracledb.connect(
                user=user,
                password=password,
                dsn=f"{host}:{port}/{service_name}",
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM DUAL")
            conn.close()
            latency_ms = int((time.monotonic() - start) * 1000)
            return jsonify({'success': True, 'latency_ms': latency_ms})
        if db_type == 'mysql':
            try:
                import pymysql
            except ModuleNotFoundError:
                return jsonify({'success': False, 'error': 'pymysql is not installed. Run: pip install "flowforge[mysql]"'}), 400
            start = time.monotonic()
            conn = pymysql.connect(
                host=cfg.get('host', 'localhost'),
                port=int(cfg.get('port', 3306)),
                database=cfg.get('database', ''),
                user=cfg.get('username') or cfg.get('user', ''),
                password=cfg.get('password', ''),
                connect_timeout=5,
                charset='utf8mb4',
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            latency_ms = int((time.monotonic() - start) * 1000)
            return jsonify({'success': True, 'latency_ms': latency_ms})
        return jsonify({'success': False, 'error': f'Unsupported db_type: {db_type}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f"{type(e).__name__}: {e}"}), 502


@bp.post('/db-connections/<uuid:conn_id>/test')
@require_auth
def test_connection(conn_id):
    from flowforge.connections.factory import get_connection as _get_conn
    try:
        with _get_conn(str(conn_id)) as conn:
            ok, latency_ms = conn.test()
        if ok:
            return jsonify({'success': True, 'latency_ms': latency_ms})
        return jsonify({'success': False, 'error': 'Connection test returned failure'}), 502
    except Exception as e:
        return jsonify({'success': False, 'error': f"{type(e).__name__}: {e}"}), 502
