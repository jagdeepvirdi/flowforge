# Session 1 Cleanup Report

## Summary

Session 1 — Cleanup & Consolidation transformed a tangled, duplicated, script-pile codebase into a clean, importable module structure. No business logic was altered. All changes are tracked across 11 commits on `master`.

**Before:** 115 files committed, 10,256 lines added across initial commit  
**After:** 16 files (15 code + 1 SQL schema), net result of 116 files changed with 836 insertions / 6,954 deletions  
**Code reduction:** ~83% fewer lines across the active scripts

---

## Task 1 — Dead Code Deleted

| Deleted File / Directory | Reason |
|---|---|
| `code/otherPythonScripts/` (whole tree) | Unrelated experiments: multi-process, PDF merge, image download, base64, datetime tests — none connected to the pipeline system |
| `code/python/bin/AutoReportGen.py` | Superseded by JobScheduler; broken symlinks in `code/bin/` |
| `code/python/bin/FileZip.py` | One-off utility; functionality absorbed into JobScheduler |
| `code/python/bin/JVReportGenerator.py` | Prototype; replaced by ReportConfig |
| `code/python/bin/dataLoader_rough.py` | Rough draft of dataLoader |
| `code/python/bin/dataLoader_testcsv.py` | Test/scratch file |
| `code/python/bin/emailAttachment.py` | Prototype; functionality absorbed into CommunicationMonitor |
| `code/python/bin/findReplaceText.py`, `getDates.py`, `getStartDateEndate.py`, `isValidDate.py`, `strValue.py` | One-off utilities superseded by utils.py |
| `code/python/bin/gmailDrive.py`, `gmailDrive2.py` | Earlier iterations; `gmailDrive3.py` was canonical |
| `code/python/bin/gmailDrive3.py` | Renamed/moved to `drive.py`; fixed missing `import io` bug |
| `code/python/bin/loadAgentList.py`, `loadCSVdata.py`, `multiFileZip.py` | One-off loaders; logic covered by dataLoader |
| `code/python/bin/newEmail.py`, `newEmailHTML.py`, `testGetEmailText.py` | Email prototypes; absorbed into CommunicationMonitor |
| `code/python/bin/readingLog.py` | Log reader prototype; SFTP error reading absorbed into SFTPManagement |
| `code/python/bin/testDeleteFile.py`, `testJob.py`, `testQuerySQL.py`, `testSQL.py` | Test/scratch files |
| `code/python/bin/Line.py`, `list.py` | Empty or single-line scratch files |
| `code/redONE/bin/checkSubOCSStatus.py`, `checkSuspendedSubscription*.py` | Company-specific REST API scripts (telecom billing) — out of scope |
| `code/redONE/bin/restAPI_*.py`, `restAPIcall.py`, `jsonText.py`, `shellinPython.py` | Company-specific REST API scripts — out of scope |
| `code/redONE/bin/CommunicationMonitor.py`, `JobScheduler.py`, `dataLoader.py`, `ReportConfig.py` | Canonical versions promoted to `code/python/bin/`; redONE copies deleted |
| `code/work/` (whole tree) | Company-specific scripts (OCS subscription management) — out of scope |
| `code/bin/` (whole tree) | Contained only broken Linux symlinks |

---

## Task 2 — Modules Consolidated

| New Module | Replaced Duplicates | What it Contains |
|---|---|---|
| `code/connections.py` | 8 copies of `getConnectionDetails()` across all scripts | Single canonical `getConnectionDetails(connNum)` reading from `connection.json` |
| `code/utils.py` | 3 copies of `replaceTextConstants()` (in CommunicationMonitor, JobScheduler, dataLoader) | Single canonical version with all 20 date-token replacements (most complete was dataLoader's redONE version) |
| `code/drive.py` | `gmailDrive3.py` + inline `upload_file()` in JobScheduler | `create_folder()`, `list_folder()`, `delete_files()`, `download_file()`, `upload_file()`. Fixed missing `import io` bug in `download_file()`. |

---

## Task 3 — Functions Split

| Original Function | Split Into | Location |
|---|---|---|
| `getGeneratedReportList()` | `get_run_summary_records(scheduleRunID)` → fetches DB rows | `JobScheduler.py` |
| | `format_run_summary(records)` → formats into text | |
| | `getGeneratedReportList()` → thin orchestrator | |
| `emailRequest()` | `get_email_config(emailConfigID)` → fetches config dict from DB | `JobScheduler.py` |
| | `build_email_body(bodyTxt, footerTxt, scheduleRunID, uploadLink)` → assembles email body | |
| | `queue_email(...)` → inserts into `jv_emailrequest` | |
| | `emailRequest()` → thin orchestrator | |
| `getCSVorJSONData()` | `get_csv_data(QueryTxt, reportFileName)` → PostgreSQL COPY to CSV | `ReportConfig.py` |
| | `get_json_data(QueryTxt, reportFileName)` → PostgreSQL COPY to JSON | |
| | `getCSVorJSONData()` → thin dispatcher | |
| `checkFileError()` | `fetch_sftp_log_lines(...)` → SFTP connection + log reading + error filtering | `SFTPManagement.py` |
| | `write_error_log(selected_log, sourceTargetDir, sftpConfigName)` → writes filtered lines to file | |
| | `checkFileError()` → thin orchestrator | |

**Main block wrapping (all 8 scripts):** All module-level execution code moved into `def main()` with `if __name__ == '__main__': main()` guard.

---

## Task 4 — Debug Prints / Unused Imports / Stale Comments Removed

### Unused Imports Removed

| File | Removed |
|---|---|
| `CommunicationMonitor.py` | `sys`, `pandas`, `shutil`, `openpyxl.Workbook`, `pathlib.Path`, `calendar` |
| `JobScheduler.py` | `calendar`, `datetime.timedelta` |
| `ReportConfig.py` | `sys` |
| `dataLoader.py` | `tarfile`, `subprocess`, `shlex`, `datetime.timedelta`, `pandas`, duplicate `calendar`, `pathlib.Path`, `zipfile` |
| `refreshMaterlizedViews.py` | `pandas`, `calendar`, `datetime` |
| `refreshMaterlizedViewsNC.py` | `pandas`, `calendar`, `datetime` |
| `refreshMaterlizedViews_One.py` | `pandas`, `calendar`, `datetime` |

### Notable Removals

- **Credential print in JobScheduler.py**: `print(f"vHost:|vDatabase:|vUserID:|vPassword:")` — printed DB credentials to stdout on every run
- **All `#print(...)` commented-out debug lines** across all files
- **Dead `parse_date()` function** in SFTPManagement.py — never called, and referenced `re` module which was never imported (would NameError if called)
- **Commented-out old SQL query block** in `getReportFileName()` (JobScheduler.py)
- **SQL query dump prints** — all `print(f"SQL Query : '{sqlQuery}'")`  calls removed
- **Variable dump prints** — all `print(f"schRunID : ...")`, `print(row)`, etc. removed

---

## Task 5 — Folder Structure Flattened

**Before:**
```
code/
  python/
    AutoReports/config/    ← config files
    bin/                   ← all Python scripts
    rough/                 ← scratch files
    sql/                   ← schema SQL
  redONE/                  ← all empty dirs
```

**After:**
```
code/
  *.py                     ← all Python scripts at one level
  *.json                   ← config files
  *.yaml                   ← credential file (flagged for Session 2 scrub)
  AutoReportSQL.sql        ← DB schema
```

The `code/python/bin/` nesting reflected the author's original Linux home directory layout (`/home/jagdeep/jvirdi/python/bin/`) — no structural meaning in this repo.

---

## Remaining Files

| File | Description |
|---|---|
| `code/connections.py` | DB connection factory — reads `connection.json` |
| `code/utils.py` | Date-token substitution (20 token patterns) |
| `code/drive.py` | Google Drive service account operations |
| `code/JobScheduler.py` | Main orchestrator — runs scheduled pipeline steps, sends emails, uploads to Drive |
| `code/CommunicationMonitor.py` | Email sender — polls `jv_emailrequest`, sends via SMTP (Gmail/Microsoft) |
| `code/ReportConfig.py` | Report generator — Excel (openpyxl), CSV, JSON |
| `code/dataLoader.py` | Data loader — CSV_LOADER (COPY from gzipped CSV), SQL_LOADER (CREATE/INSERT/DELETE) |
| `code/SFTPManagement.py` | SFTP operations — download, upload, check, check-error (log scanning) |
| `code/refreshMaterlizedViews.py` | Refresh all materialized views (calls DB stored proc) |
| `code/refreshMaterlizedViewsNC.py` | Refresh NC materialized views with audit tracking |
| `code/refreshMaterlizedViews_One.py` | Refresh one materialized view at a time with per-view audit |
| `code/AutoReportSQL.sql` | Database schema — all `jv_*` tables |
| `code/connection.json` | DB credentials (hardcoded — **flagged for Session 2 scrub**) |
| `code/config_data.json` | Additional config (contents not sensitive) |
| `code/settings.yaml` | Google OAuth credentials (**flagged for Session 2 scrub**) |

---

## Flagged for Session 2

These items were deliberately left untouched per Session 1 rules ("Do NOT change business logic, company/telecom references, or hardcoded values"):

| Item | Issue | Session 2 Action |
|---|---|---|
| `code/connection.json` | Hardcoded DB credentials (`"password":"harpal123"`) and internal IPs (`192.168.1.35`, `192.168.99.112`) | Replace with env vars; delete file from repo |
| `code/settings.yaml` | Google OAuth `client_secret: GOCSPX-2sOUD7H...` hardcoded | Replace with env vars; delete file from repo |
| `connections.py` | Hardcoded path `/home/jagdeep/jvirdi/python/AutoReports/config/connection.json` | Replace with env var or config lookup |
| `drive.py` | Hardcoded path `/home/jagdeep/jvirdi/python/bin/redone_file.json` for service account | Replace with env var |
| `JobScheduler.py` | Hardcoded log dir `/home/jagdeep/jvirdi/data/logs/` | Replace with env var |
| All scripts | SQL uses f-strings throughout — SQL injection risk | Replace with parameterized queries |
| All scripts | `jv_*` table prefix — author's initials | Rename to `ff_*` (FlowForge) in schema + all SQL |
| `refreshMaterlizedViewsNC.py` | References `redonematerializedviewstats` table | Rename to generic name |
| No connection pooling | Each function opens and closes its own psycopg2 connection | Introduce a shared pool |
