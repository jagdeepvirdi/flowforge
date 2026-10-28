-- Pre-upgrade check for FlowForge v2.0.0+: the built-in AI was removed from Core.
-- Run against your FlowForge config database (the one FLOWFORGE_DB_URL points to). Read-only.
--
--   psql "$FLOWFORGE_DB_URL" -f scripts/check_ai_analyze.sql
--
-- After upgrading, a saved ai_analyze step FAILS when it runs ("requires the Brain service").
-- Set its on_error to 'continue', disable it, or delete it. {{ ai_summary }} renders empty.

\echo '== 1. Saved ai_analyze steps (these will fail after the upgrade) =='
SELECT p.name            AS pipeline,
       p.enabled         AS pipeline_enabled,
       s.step_order,
       s.name            AS step,
       s.enabled         AS step_enabled,
       s.on_error,
       s.config ->> 'provider' AS provider
FROM   ff_pipeline_steps s
JOIN   ff_pipelines p ON p.id = s.pipeline_id
WHERE  s.step_type = 'ai_analyze'
ORDER  BY p.name, s.step_order;

\echo '== 2. Templates that still use {{ ai_summary }} or steps.*.ai_summary (will render empty) =='
SELECT 'email_config' AS kind, e.name, e.id::text AS id
FROM   ff_email_configs e
WHERE  e.subject LIKE '%ai_summary%' OR e.body_template LIKE '%ai_summary%'
UNION ALL
SELECT 'pipeline_step', p.name || ' / ' || s.name, s.id::text
FROM   ff_pipeline_steps s
JOIN   ff_pipelines p ON p.id = s.pipeline_id
WHERE  s.config::text LIKE '%ai_summary%' AND s.step_type <> 'ai_analyze'
UNION ALL
SELECT 'report_config', r.name, r.id::text
FROM   ff_report_configs r
WHERE  r.query LIKE '%ai_summary%'
ORDER  BY 1, 2;

\echo '== 3. ai_analyze runs in the last 30 days (shows whether anyone is still relying on it) =='
SELECT count(*)         AS runs,
       max(started_at)  AS last_run
FROM   ff_step_runs
WHERE  step_type = 'ai_analyze'
  AND  started_at > now() - interval '30 days';
