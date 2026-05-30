# Scenario: Daily Infrastructure Health Monitoring

Build a pipeline that collects SSH system metrics and database health stats every morning, generates an Excel report, and emails it to your team. An alerting variant fires email only when thresholds are breached.

---

## What This Pipeline Does

```
[SSH: load average] ──┐
[SSH: memory usage] ──┤
[SSH: disk usage]   ──┼──▶ [Excel report] ──▶ [Email with attachment]
[DB health check]   ──┘
```

| Step | Type | Purpose |
|---|---|---|
| `collect_load` | `ssh_command` | `uptime` — 1/5/15-min load averages |
| `collect_memory` | `ssh_command` | `free -m` — RAM total / used / free |
| `collect_disk` | `ssh_command` | `df -h` as CSV — per-filesystem usage |
| `check_db` | `db_health_check` | Sessions, cache hit ratio, replication lag |
| `generate_report` | `data_report` | Turn disk CSV into an Excel attachment |
| `send_report` | `email` | Send report + inline metrics in email body |

---

## Prerequisites

1. **SSH Connection** — add your server in **Connections → SSH** (host, port, username, password or key path). Note its UUID.
2. **DB Connection** — add your database in **Connections → Database**. Note its UUID.
3. **Email Config** — set up an email config with recipient list and HTML body template (see below). Note its UUID.

---

## Variant 1 — Daily Digest (always emails)

Import `examples/health-monitoring-pipeline.yaml` via **Settings → Import Pipeline**, then replace the three `<YOUR_*_ID>` placeholders with your actual connection/config UUIDs.

The pipeline runs at 7:00 AM on weekdays and always sends the report.

### Email Body Template

Paste this into your Email Config's body template. It uses the `load_average` and `memory_usage` pipeline variables captured by the SSH steps:

```html
<h2>Daily Infrastructure Report — {{ current_date }}</h2>

<table style="border-collapse:collapse;font-family:monospace;font-size:13px">
  <tr><td style="padding:4px 12px 4px 0;color:#666">Load Average (1/5/15 min)</td>
      <td style="padding:4px 0"><strong>{{ load_average }}</strong></td></tr>
  <tr><td style="padding:4px 12px 4px 0;color:#666">Memory</td>
      <td style="padding:4px 0"><strong>{{ memory_usage }}</strong></td></tr>
</table>

<p style="margin-top:16px;color:#444">
  Full disk usage breakdown is attached as an Excel file.<br>
  Database health metrics are in the
  <a href="{{ env.FLOWFORGE_URL }}/runs">Run History</a> step logs.
</p>
```

---

## Variant 2 — Threshold Alert (only emails on breach)

Import `examples/health-monitoring-alerting.yaml` instead. This variant:

- Sets `send_only_on_failure: true` on the pipeline — no email on a healthy run
- Adds a threshold-check SSH step that exits with code 1 if any filesystem exceeds 90% — failing the step, triggering the email

```
[SSH: check disk threshold] ──▶ fails if >90% ──▶ [Email: alert sent]
                                 succeeds if OK ──▶ [Email: suppressed]
```

The threshold command:
```bash
df -h | awk 'NR>1 { gsub(/%/, "", $5); if ($5+0 > 90) { print "ALERT: "$6" at "$5"%"; found=1 } } END { exit (found ? 1 : 0) }'
```

Adjust `90` to your desired threshold. The step fails if any mount point exceeds it, and the stdout ("ALERT: /data at 94%") is captured and included in the email body via `{{ threshold_alert }}`.

### Alert Email Body Template

```html
<h2>⚠ Disk Threshold Alert — {{ current_date }}</h2>

<pre style="background:#fef2f2;border:1px solid #fca5a5;padding:12px;border-radius:4px">{{ threshold_alert }}</pre>

<p>Check the server immediately. Full disk report is attached.</p>
```

---

## Standard SSH Commands Reference

These commands produce clean output suitable for `output_var` or CSV parsing. Copy them directly into your `ssh_command` step configs.

### Load Average
```bash
uptime | awk -F'load average: ' '{print $2}'
```
Output example: `0.42, 0.38, 0.31`

### Memory Usage (human-readable)
```bash
free -m | awk 'NR==2{printf "%s MB total / %s MB used / %s MB free", $2, $3, $4}'
```
Output example: `7986 MB total / 3421 MB used / 4565 MB free`

### Memory as CSV (for data_report)
```bash
free -m | awk 'NR==1{print "Type,Total_MB,Used_MB,Free_MB"} NR==2{printf "Memory,%s,%s,%s\n",$2,$3,$4} NR==3{printf "Swap,%s,%s,%s\n",$2,$3,$4}'
```

### Disk Usage as CSV (for data_report)
```bash
df -h | awk 'NR==1{print "Filesystem,Size,Used,Available,Use%,Mounted"} NR>1{printf "%s,%s,%s,%s,%s,%s\n",$1,$2,$3,$4,$5,$6}'
```

### Top 10 CPU Processes
```bash
ps aux --sort=-%cpu | awk 'NR==1{print "User,CPU%,MEM%,Command"} NR>1 && NR<=11{printf "%s,%s,%s,%s\n",$1,$3,$4,$11}'
```

### Disk I/O (requires `sysstat` package)
```bash
iostat -x 1 1 | awk '/^[a-z]/{printf "%s,%s,%s\n",$1,$6,$7}' | sed '1s/^/Device,r_await,w_await\n/'
```

---

## Standard DB Health Commands Reference

The `db_health_check` step runs these queries automatically. Results appear in Run History → step logs.

### PostgreSQL

| Metric | Query |
|---|---|
| Active sessions | `SELECT count(*) FROM pg_stat_activity WHERE state = 'active'` |
| Cache hit ratio | `SELECT round(sum(heap_blks_hit)::numeric / nullif(sum(heap_blks_hit)+sum(heap_blks_read),0) * 100, 2) FROM pg_statio_user_tables` |
| Replication lag | `SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) FROM pg_stat_replication` |

To run these ad hoc, use a `db_query` step with `output_variable` to capture the result into the pipeline context and include it in the email body.

### Oracle

| Metric | Query |
|---|---|
| Active user sessions | `SELECT count(*) FROM v$session WHERE status='ACTIVE' AND type!='BACKGROUND'` |
| Buffer cache hit ratio | `SELECT round((1-(phy.value/(cur.value+con.value)))*100,2) FROM v$sysstat phy, v$sysstat cur, v$sysstat con WHERE phy.name='physical reads' AND cur.name='db block gets' AND con.name='consistent gets'` |
| High tablespace usage | `SELECT tablespace_name, used_percent FROM dba_tablespace_usage_metrics WHERE used_percent > 80 ORDER BY used_percent DESC` |

---

## Combining with AI Analysis (Optional)

Add an `ai_analyze` step after the DB health check to generate a natural-language summary of the metrics:

```yaml
- name: summarise_health
  step_type: ai_analyze
  step_order: 5
  config:
    connection_id: <YOUR_PG_CONNECTION_ID>
    query: >
      SELECT datname, numbackends, blks_hit, blks_read,
             round(blks_hit::numeric / nullif(blks_hit+blks_read,0) * 100, 1) AS cache_pct
      FROM pg_stat_database
      WHERE datname NOT LIKE 'template%'
    prompt: >
      You are a database reliability engineer. Summarise these PostgreSQL stats in 3 sentences.
      Flag anything concerning. Be concise — this goes in an ops email.
    output_variable: db_summary
    provider: ollama
```

Then use `{{ db_summary }}` in the email body template.

---

## Scheduling

| Schedule | Cron | When |
|---|---|---|
| 7 AM weekdays | `0 7 * * 1-5` | Monday–Friday morning |
| 8 AM daily | `0 8 * * *` | Every day |
| Every 4 hours | `0 */4 * * *` | Continuous monitoring |
| Every 15 minutes | `*/15 * * * *` | Near-realtime (high-frequency) |

Set the schedule in the Pipeline Builder's **Schedule** field using any cron expression.
