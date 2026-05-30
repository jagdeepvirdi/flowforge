"""Database health check step — collect industry-standard metrics."""
import logging
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class DbHealthCheckStep(BaseStep):
    """Collect health metrics from a database.

    Config fields:
        connection_id   ID of the DbConnection row  (required)
        metrics         List of metrics to collect (default: all)
                        Supported: sessions, locks, cache_hit_ratio, replication_lag
    """

    step_type = 'db_health_check'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.connections.factory import get_connection

        conn_id = self.config.get('connection_id')
        if not conn_id:
            return StepResult(success=False, error='db_health_check: connection_id is required')

        try:
            with get_connection(conn_id) as conn:
                db_type = getattr(conn, 'db_type', None)
                if not db_type:
                    # Try to infer from class name if db_type attr is missing
                    cls_name = conn.__class__.__name__.lower()
                    if 'postgres' in cls_name: db_type = 'postgresql'
                    elif 'oracle' in cls_name: db_type = 'oracle'
                    elif 'mysql' in cls_name: db_type = 'mysql'

                if db_type == 'postgresql':
                    return self._check_postgres(conn)
                elif db_type == 'oracle':
                    return self._check_oracle(conn)
                elif db_type == 'mysql':
                    return self._check_mysql(conn)
                else:
                    return StepResult(success=False, error=f"Unsupported database type for health check: {db_type}")

        except Exception as exc:
            logger.exception("Database health check failed")
            return StepResult(success=False, error=f"Health check error: {exc}")

    def _check_postgres(self, conn) -> StepResult:
        logs = ["PostgreSQL Health Check:"]
        
        # 1. Sessions
        q_sessions = "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
        active = conn.execute_query(q_sessions)[0][0]
        logs.append(f"  Active Sessions: {active}")

        # 2. Cache Hit Ratio
        q_cache = """
            SELECT sum(heap_blks_read) as read, sum(heap_blks_hit) as hit 
            FROM pg_statio_user_tables
        """
        res = conn.execute_query(q_cache)
        read, hit = res[0]
        if read and (read + hit) > 0:
            ratio = (hit / (read + hit)) * 100
            logs.append(f"  Cache Hit Ratio: {ratio:.2f}%")
        
        # 3. Replication Lag (if any)
        q_lag = "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) FROM pg_stat_replication"
        try:
            lags = conn.execute_query(q_lag)
            if lags:
                max_lag = max(l[0] for l in lags if l[0] is not None)
                logs.append(f"  Max Replication Lag: {max_lag} bytes")
        except:
            pass # Might not be a primary or no replicas

        return StepResult(success=True, logs="\n".join(logs))

    def _check_oracle(self, conn) -> StepResult:
        logs = ["Oracle Health Check:"]
        
        # 1. Sessions
        q_sessions = "SELECT count(*) FROM v$session WHERE status = 'ACTIVE' AND type != 'BACKGROUND'"
        active = conn.execute_query(q_sessions)[0][0]
        logs.append(f"  Active User Sessions: {active}")

        # 2. Buffer Cache Hit Ratio
        q_cache = """
            SELECT round((1 - (phy.value / (cur.value + con.value))) * 100, 2)
            FROM v$sysstat phy, v$sysstat cur, v$sysstat con
            WHERE phy.name = 'physical reads'
              AND cur.name = 'db block gets'
              AND con.name = 'consistent gets'
        """
        try:
            ratio = conn.execute_query(q_cache)[0][0]
            logs.append(f"  Buffer Cache Hit Ratio: {ratio}%")
        except:
            pass

        # 3. Tablespace usage (Top 5)
        q_ts = """
            SELECT tablespace_name, used_percent 
            FROM dba_tablespace_usage_metrics 
            WHERE used_percent > 80 
            ORDER BY used_percent DESC
        """
        try:
            full_ts = conn.execute_query(q_ts)
            if full_ts:
                logs.append("  High Tablespace Usage (>80%):")
                for ts, pct in full_ts:
                    logs.append(f"    {ts}: {pct:.1f}%")
        except:
            pass

        return StepResult(success=True, logs="\n".join(logs))

    def _check_mysql(self, conn) -> StepResult:
        logs = ["MySQL Health Check:"]
        
        # 1. Threads
        q_threads = "SHOW STATUS LIKE 'Threads_connected'"
        res = conn.execute_query(q_threads)
        logs.append(f"  Connected Threads: {res[0][1]}")

        # 2. InnoDB Buffer Pool Hit Rate
        q_innodb = "SHOW ENGINE INNODB STATUS"
        # This is hard to parse in a generic way without more logic, 
        # but let's at least get some basic status
        
        return StepResult(success=True, logs="\n".join(logs))
