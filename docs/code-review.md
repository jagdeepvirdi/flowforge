# FlowForge — Code Review (Session Zero)

**Date:** 2026-05-16  
**Scope:** All files under `D:\Project\flowforge\code\`  
**Status:** Read-only review. No code changes made.

---

## 1. FILE INVENTORY

### Structure Overview

The source code lives in three distinct areas:

| Area | Purpose | Relevance to FlowForge |
|---|---|---|
| `code/python/bin/` | Generic/reusable pipeline scripts | HIGH — core of FlowForge |
| `code/redONE/bin/` | Company-specific scripts (evolved from python/bin) | HIGH — contains latest versions, needs scrubbing |
| `code/otherPythonScripts/` | Experiments, utilities, venv | LOW — mostly throwaway code |
| `code/work/` | One-off operational scripts | LOW — telecom-specific, discard |
| `code/bin/` | Shell notes and library lists | LOW — not code |

---

### `code/python/bin/` — Core Scripts

| File | Description | ~Lines | Key Functions/Classes |
|---|---|---|---|
| `AutoReportGen.py` | Early monolithic report+email script; reads JSON config, generates Excel, sends via yagmail | 157 | `getLastMonthFirstLastdate()`, `getConnectionDetails()`, `getDailyRunDates()`, `insertReportInformation()`, `getReportData()` |
| `CommunicationMonitor.py` | Production email dispatcher; polls DB for pending email requests, sends via SMTP | 233 | `getConnectionDetails()`, `getEmailsReportAttachments()`, `getRecipientEmails()`, `replaceTextConstants()`, `updateEmailRequest()`, `attachmentToMail()` |
| `JobScheduler.py` | Core orchestrator; reads schedule config from DB, executes processes via subprocess, zips and uploads to Drive | 448 | `getConnectionDetails()`, `getFullFileName()`, `replaceTextConstants()`, `emailRequest()`, `insertSchInform()`, `execute_python_file()`, `updateProcessLastRun()`, `updateNextDateLastDate()`, `outputZipFile()`, `getReportFileName()`, `upload_file()` |
| `ReportConfig.py` | Report generator; reads report config from DB, queries data, writes Excel/CSV/JSON | 308 | `getConnectionDetails()`, `getStartEndDate()`, `getLastMonthFirstLastdate()`, `getLastMonthYear()`, `getDailyRunDates()`, `getReportSheetData()`, `BackUpData()`, `getCSVorJSONData()`, `getFullFileName()`, `insertReportInformation()` |
| `SFTPManagement.py` | SFTP download/upload/check operations; reads SFTP config from DB | 414 | `getConnectionDetails()`, `downloadFile()`, `checkFile()`, `checkFileError()`, `uploadFiles()`, `getLastRunDate()`, `updateLastRun()`, `insertSftpAudit()`, `getDates()`, `getFileName()`, `getDir()` |
| `dataLoader.py` | Loads CSV/GZ files into PostgreSQL tables; reads config from DB | 268 | `getConnectionDetails()`, `insertAuditInform()`, `updateAuditInform()`, `loadingCSVdata()`, `getFileRecords()`, `delete_file()`, `unzip_gz()` |
| `FileZip.py` | Utility to zip report files for a schedule run | 52 | `getConnectionDetails()`, `outputZipFile()` |
| `gmailDrive.py` | PyDrive-based Drive upload (v1, deprecated) | 26 | Inline script only |
| `gmailDrive2.py` | PyDrive-based Drive upload (v2, deprecated) | 25 | Inline script only |
| `gmailDrive3.py` | Drive utility using google-api-python-client + service account (latest) | 118 | `create_folder()`, `list_folder()`, `delete_files()`, `download_file()`, `upload_file()` |
| `emailAttachment.py` | Test: yagmail send with hardcoded credentials | 14 | Inline script |
| `newEmail.py` | Test: smtplib plaintext email with hardcoded credentials | 23 | `send_gmail_email()` |
| `newEmailHTML.py` | Test: smtplib HTML email with hardcoded credentials | 57 | `send_gmail_email_with_html()` |
| `refreshMaterlizedViews.py` | Calls `refresh_materializedviews()` stored procedure | 38 | `getConnectionDetails()`, `refreshMV()` |
| `refreshMaterlizedViewsNC.py` | Calls `refresh_materializedviewsNC()` with audit logging | 99 | `getConnectionDetails()`, `refreshMV()`, `insertAuditSummary()`, `updateAuditSummary()` |
| `refreshMaterlizedViews_One.py` | Calls `refresh_materializedviewprocess()` per table, driven by DB config | 129 | `getConnectionDetails()`, `refreshMV()`, `insertAuditSummary()`, `updateAuditSummary()` |
| `loadCSVdata.py` | Simple hardcoded CSV loader (scratch file) | 65 | `getConnectionDetails()`, `loadingCSVdata()` |
| `loadAgentList.py` | Hardcoded export of config tables to CSV/JSON (scratch file) | 40 | Inline script |
| `JVReportGenerator.py` | Stub/template file with argparse + logging setup only | 44 | Logging setup only |
| `getDates.py` | Date calculation scratch file | 33 | Inline script |
| `requirements.txt` | System pip freeze (not a proper project requirements.txt) | 80 | N/A |

**Test/scratch files** (contain no reusable logic):
`testSQL.py`, `testJob.py`, `testQuerySQL.py`, `testGetEmailText.py`, `strValue.py`, `isValidDate.py`, `list.py`, `findReplaceText.py`, `Line.py`, `dataLoader_rough.py`, `dataLoader_testcsv.py`, `getStartDateEndate.py`

---

### `code/redONE/bin/` — Latest (Company-Specific) Versions

These are the **most up-to-date versions** of the core scripts. They diverged from `python/bin/` with company-specific enhancements. All need scrubbing.

| File | How it differs from `python/bin/` version | Key additions |
|---|---|---|
| `CommunicationMonitor.py` | **Newer version** — adds `providerType` field; routes to SMTP_SSL (GMAIL) or STARTTLS (MICROSOFT) | Multi-provider email routing |
| `JobScheduler.py` | **Newer version** — adds `getGeneratedReportList()` for richer email bodies | Itemized report list in emails |
| `ReportConfig.py` | Identical to `python/bin/` version | — |
| `SFTPManagement.py` | Identical to `python/bin/` version | — |
| `dataLoader.py` | **Newer version** — adds `SQL_LOADER` type (CREATE/INSERT/DELETE via SQL), extended `replaceTextConstants()` | SQL-driven data loading |
| `checkSubOCSStatus.py` | Telecom-specific: checks OCS subscriber status via subprocess | DISCARD |
| `checkSuspendedSubscription.py` | Telecom-specific: checks/updates suspended subscribers | DISCARD |
| `checkSuspendedSubscription_20231102.py` | Earlier version of above | DISCARD |
| `restAPI_PROD_createPurchase.py` | Telecom REST API: create purchase against OCS | DISCARD |
| `restAPI_PROD_endProcedure.py` | Telecom REST API: end procedure | DISCARD |
| `restAPI_createPurchase.py` | Test version of above | DISCARD |
| `restAPI_endProcedure.py` | Test version of above | DISCARD |
| `restAPIcall.py` | Generic REST API caller | DISCARD |
| `refreshMaterlizedViewsNC.py` | Identical to `python/bin/` version | — |
| `jsonText.py` | JSON manipulation scratch | DISCARD |
| `shellinPython.py` | Shell-in-Python scratch | DISCARD |

---

### `code/otherPythonScripts/` — Experimental / Throwaway

| File | Description |
|---|---|
| `AutoReports/AggPassed.py` | sys.argv example — discard |
| `AutoReports/consolidateAll.py`, others | Early report experiments — discard |
| `AutoReports/config_data.json` | Contains base64-encoded SQL and DB config with credentials |
| `AutoReports/connection.json` | **Hardcoded DB credentials** — `redoneDB`, `harpal123` |
| `emailProcess/emailG.py` | yagmail test with hardcoded credentials |
| `emailProcess/gmailAuth.json` | **Hardcoded Gmail app password** |
| `mergerPDF/` | PDF merge utilities (unrelated to FlowForge) |
| `MultiProcess/` | Multiprocessing examples (unrelated) |

---

### `code/work/` — Operational One-Offs

| File | Description |
|---|---|
| `30GBData/restAPI_PROD_createPurchase.py` | Telecom REST API — discard |
| `30GBData/restAPI_PROD_endProcedure.py` | Telecom REST API — discard |
| `EndZeroPackage/removeOCSSubscriptionIDProcess.py` | OCS subscriber cleanup — discard |
| `EndZeroPackage/restAPI_PROD_endProjectZero.py` | Telecom operation — discard |

---

### Dependency Map (Imports)

```
AutoReportGen.py         → json, psycopg2, openpyxl, yagmail, calendar, datetime
CommunicationMonitor.py  → json, psycopg2, smtplib, email.mime.*, openpyxl, zipfile
JobScheduler.py          → json, psycopg2, subprocess, shlex, zipfile, google.oauth2, googleapiclient
ReportConfig.py          → json, psycopg2, openpyxl, argparse
SFTPManagement.py        → json, psycopg2, pysftp, argparse
dataLoader.py            → json, psycopg2, gzip, pandas, argparse
FileZip.py               → json, psycopg2, zipfile
gmailDrive3.py           → google.oauth2.service_account, googleapiclient
refreshMV*.py            → json, psycopg2
```

No file imports from any other file in the project. Every script is self-contained, copying functions wholesale instead of importing shared modules.

---

## 2. EXISTING CAPABILITIES

### 2a. Email Sending

**Three separate implementations exist:**

**Implementation 1 — yagmail (AutoReportGen.py, emailAttachment.py, emailProcess/emailG.py)**
- Library: `yagmail` (wrapper over smtplib for Gmail)
- Provider: Gmail only
- Credentials: **Hardcoded app passwords** in source code
- Recipients: Hardcoded as Python lists in source code
- Body: Hardcoded plain text strings
- Attachments: Single file path passed directly to `yag.send()`
- Status: **Deprecated / scratch files only** — not suitable for FlowForge

**Implementation 2 — smtplib SMTP_SSL (python/bin/CommunicationMonitor.py)**
- Library: `smtplib.SMTP_SSL` + `email.mime.*`
- Provider: Single SMTP server (Gmail-only due to `SMTP_SSL`)
- Credentials: Retrieved from `jv_emailuserdetails` table (email, passwordtxt, sftpserver, portnumber)
- Recipients: Retrieved from `jv_emailconfigrecipient` table (TO/CC/BCC by recipient type)
- Body: From `jv_emailrequest` table — both plain text (`bodytxt`) and HTML (`bodyhtml`) fields; `bodytxtboo` flag selects which to use
- Attachments: Three modes — (a) specific file path from `jv_emailrequest.attachmentpath`, (b) directory walk, (c) query `jv_allreportauditsummary` by scheduleRunID
- Template variables: Custom string tokens (e.g., `XLYYYYMMX`, `XCYYYYMMDDX`) replaced by `replaceTextConstants()`
- Trigger: Polls `jv_emailrequest` where `emailrequeststatus=1` and `senddtm <= now()`

**Implementation 3 — smtplib multi-provider (redONE/bin/CommunicationMonitor.py) — LATEST**
- Library: `smtplib` with `ssl.SSLContext`
- Providers: GMAIL (uses `SMTP_SSL`) or MICROSOFT (uses `SMTP` + `starttls()`)
- Provider selected by `jv_emailuserdetails.providertype` field
- Everything else identical to Implementation 2
- **This is the most evolved version to use as a base**

---

### 2b. Google Drive Upload

**Three separate implementations exist:**

**Implementation 1 — PyDrive (gmailDrive.py, gmailDrive2.py)**
- Library: `pydrive`
- Auth: OAuth2 `LocalWebserverAuth()` — requires browser interaction
- Status: **Deprecated** — PyDrive is unmaintained; requires interactive login

**Implementation 2 — google-api-python-client + service account (python/bin/JobScheduler.py)**
- Library: `google-api-python-client` + `google.oauth2.service_account`
- Auth: Service account JSON file at hardcoded path `/home/jagdeep/jvirdi/python/bin/file.json`
- Scope: `https://www.googleapis.com/auth/drive`
- Upload: `drive_service.files().create()` with `MediaFileUpload`
- MIME type: hardcoded as `application/zip` (only zipped files uploaded)
- Returns: file ID, link constructed manually as `https://drive.google.com/file/d/{id}/view?usp=drive_link`
- Trigger: Called from `JobScheduler.py` main loop when `uploadingAddress` is set

**Implementation 3 — google-api-python-client + service account (gmailDrive3.py) — LATEST**
- Same library + auth approach as Implementation 2
- Adds `create_folder()`, `list_folder()`, `delete_files()`, `download_file()` functions
- Service account file at: `/home/jagdeep/jvirdi/python/bin/redone_file.json`
- **This is the most complete Drive utility to use as a base**

---

### 2c. Report Generation

**Working formats: Excel only (EXEL). CSV/JSON implemented partially via PostgreSQL COPY — not Python-native.**

**Excel generation (ReportConfig.py, AutoReportGen.py):**
- Library: `openpyxl`
- Report metadata: `jv_reportconfig` table (name, type, extension, filename template, output directory)
- Queries: `jv_reporthasquery` table (one or more queries → one Excel sheet each, ordered by `stepnumber`)
- Date substitution in SQL: Custom string tokens `XSTARTDATEX` / `XENDDATEX` / `XYYYYMMX`
- Output filename construction: Custom tokens `YYYYMMDDHHMISS` (timestamp) and `MONYYYY` (e.g., April-2024)
- Directory structure: `{base}/{YYYY}/{YYYYMM}/filename.xlsx` (auto-created via `Path.mkdir`)
- Style: No styling — raw data, headers from cursor column names, no formatting
- Multi-sheet: Supported — each query in `jv_reporthasquery` becomes a separate sheet

**CSV/JSON generation (ReportConfig.py `getCSVorJSONData()`):**
- Uses PostgreSQL `COPY` command to `/tmp/`, then `shutil.copy()` to destination
- **Broken** — the SQL string in `getCSVorJSONData()` is never interpolated (literal `{QueryTxt}` in string, not f-string)
- Not tested in production

**Backup table creation:**
- `BackUpData()` function: wraps report query in `CREATE TABLE public.REPBK_{id}_{ts} AS (...)` — creates snapshot tables

---

### 2d. Database Connections

**Database: PostgreSQL only** (psycopg2). No Oracle in any working code.

**Connection method:**
- `psycopg2.connect(host, database, user, password)` — new connection opened per function call
- **No connection pooling** — every function that touches the DB opens and closes its own connection
- In some functions, multiple DB operations each open a separate connection
- `JobScheduler.py` opens one connection at the top level but also opens additional connections inside called functions

**Credential storage:**
- Read from a JSON file: `/home/jagdeep/jvirdi/python/AutoReports/config/connection.json`
- File format: `{"logindetails": [{"connection_num": 1, "host": "...", "database": "...", "user": "...", "password": "..."}]}`
- `getConnectionDetails(connNum)` accepts a connection number; returns (host, db, user, password)
- Connection 1 is always the FlowForge config DB; connection 2 is a data/reporting DB
- **Hardcoded JSON file path** in every single script

**Stored procedures called:**

| Procedure | Called in | Purpose |
|---|---|---|
| `public.refresh_materializedviews()` | `refreshMaterlizedViews.py` | Refresh all materialized views |
| `public.refresh_materializedviewsNC()` | `refreshMaterlizedViewsNC.py` | Refresh NC subset of MVs |
| `public.refresh_materializedviewprocess(table, system_type)` | `refreshMaterlizedViews_One.py` | Refresh single MV by name |
| `dblink_connect('conn_dblink', 'pg_rep_db')` | `checkSubOCSStatus.py`, `checkSuspendedSubscription.py` | Connect to replica DB via dblink |

**How procedures are called:**
- `cursor.execute("CALL public.procedure_name()")` — direct CALL syntax
- `cursor.execute(f"CALL public.procedure_name('{param}')")` — f-string parameter injection (SQL injection risk)
- Return values not captured from procedures

---

### 2e. Scheduling

**No APScheduler. No cron library in Python.**

The scheduling model is:
1. OS-level cron triggers `JobScheduler.py` (or `redONE/bin/JobScheduler.py`) on a fixed interval
2. `JobScheduler.py` queries a database view `jv_scheduleprocessorder` which returns schedulers whose `nextrundate <= today`
3. For each scheduler due to run: execute each linked process via `subprocess.run()` in `step_order` sequence
4. Each "process" is a Python script registered in `jv_processbinary` with its full path, type, and up to 6 arguments
5. After all processes: zip outputs, upload to Drive, queue email request in `jv_emailrequest`
6. `CommunicationMonitor.py` is also cron-triggered (separately) to dispatch queued emails

**The scheduler is a process orchestrator** — it does not run code in-process; it spawns child processes. This means each step runs in a separate Python interpreter.

---

### 2f. Configuration

| What | Where | Mechanism |
|---|---|---|
| DB connection details | `/home/jagdeep/jvirdi/python/AutoReports/config/connection.json` | JSON file, hardcoded path |
| Report definitions | `jv_reportconfig` table | DB |
| Report queries | `jv_reporthasquery` table | DB |
| Email config | `jv_emailconfig` table | DB |
| Email recipients | `jv_emailconfigrecipient` table | DB |
| SMTP credentials | `jv_emailuserdetails` table | DB (plaintext password) |
| Schedule config | `jv_schedulerconfig` table | DB |
| Process definitions | `jv_processbinary` table | DB |
| SFTP config | `jv_sftpconfig` + `jv_sftpconnectiondetails` | DB |
| Data loader config | `jv_dataloaderconfig` + `jv_dataloadersql` | DB |
| MV refresh config | `jv_materializedviewrefreshconfig` | DB |
| Drive service account | `/home/jagdeep/jvirdi/python/bin/file.json` | JSON file, hardcoded path |
| Drive folder ID | `jv_schedulerconfig.uploadingaddress` | DB |
| Google OAuth secrets | `python/rough/settings.yaml` | YAML file (checked into repo!) |
| Hardcoded recipients | `AutoReportGen.py` lines 144-145 | Source code |
| Gmail app password | `AutoReportGen.py` line 143, `emailAttachment.py`, etc. | Source code |

---

## 3. DATABASE SCHEMA

### Configuration Tables

| Table | Purpose |
|---|---|
| `jv_reportconfig` | Report definitions: name, type (DAILY/MONTHLY), extension (EXEL/CSV/JSON), filename template, output directory |
| `jv_reporthasquery` | SQL queries per report, ordered by `stepnumber`; one query = one Excel sheet |
| `jv_emailconfig` | Email template: subject, body (text+html), footer, attachment flags, linked to user |
| `jv_emailconfigrecipient` | Recipient list per email config: type (TO/CC/BCC), email address |
| `jv_emailuserdetails` | SMTP credentials: email, password (plaintext), server, port, provider type |
| `jv_schedulerconfig` | Scheduler: name, last run, next run, attachment location, zip flag, email config, upload address |
| `jv_processbinary` | Process registry: type (python3), location, name, up to 6 arguments |
| `jv_schedulerhasprocess` | Links scheduler to processes with step ordering |
| `jv_sftpconfig` | SFTP task config: type (DOWNLOAD/UPLOAD/CHECK/CHECKERROR), dir, file, source/target dir |
| `jv_sftpconnectiondetails` | SFTP server credentials: hostname, port, username, password |
| `jv_sftperrorconfig` | Error pattern definitions for SFTP log monitoring |
| `jv_sftphaserrorconfig` | Links SFTP configs to error patterns |
| `jv_dataloaderconfig` | Data loader config: type (CSV_LOADER/SQL_LOADER), input path, table, delimiter, compression |
| `jv_dataloadersql` | SQL statements for SQL_LOADER type, ordered by step |
| `jv_materializedviewrefreshconfig` | Which materialized views to refresh, in what order, for which system (PROD/SIT) |

### Runtime / Audit Tables

| Table | Purpose |
|---|---|
| `jv_emailrequest` | Email queue: status 1=pending, 2=sent; stores full email content |
| `jv_reportauditsummary` | Report generation history: dates, filename, path, scheduleRunID |
| `jv_scheduleauditsummary` | Scheduler run log: success flag, file location, cloud address |
| `jv_sftpauditsummary` | SFTP operation log: type, filename, direction |
| `jv_dataloaderauditsummary` | Data loader log: file, table, record counts |
| `jv_materializedviewauditsummary` | MV refresh log: table name, timing |
| `jv_subscriptionocsstatus` | **TELECOM-SPECIFIC** — OCS subscription check results; discard |

### Views

| View | Purpose |
|---|---|
| `jv_scheduleprocessorder` | Drives `JobScheduler.py` — returns schedulers due to run with all config |
| `jv_allreportauditsummary` | Union of REPORTS + SFTP + DATALOADER summaries for a schedule run |

### External / Domain Tables (not FlowForge-owned)

| Table | Domain | Disposition |
|---|---|---|
| `pvsubscription` | Telecom subscriber data | DISCARD — do not include |
| `mvsit_subscription` | SIT subscriber data | DISCARD |
| `main_subscriptionallowance` | Allowance data | DISCARD |
| `fin_accountsubscriptioninfo` | Financial subscriber data | DISCARD |
| `da_subcountcurrentstats` | Subscriber aggregate stats | DISCARD |
| `redonematerializedviewstats` | Company-specific MV stats | DISCARD |

---

## 4. DUPLICATION ANALYSIS

### a. Places that send email

| File | Function | Method |
|---|---|---|
| `AutoReportGen.py` | Main block (lines 152-153) | yagmail.SMTP.send() |
| `python/bin/CommunicationMonitor.py` | Main block (lines 222-227) | smtplib.SMTP_SSL |
| `redONE/bin/CommunicationMonitor.py` | Main block (lines 237-245) | smtplib.SMTP_SSL or smtplib.SMTP+STARTTLS |
| `emailAttachment.py` | Main block (line 12) | yagmail (test only) |
| `newEmail.py` | `send_gmail_email()` | smtplib.SMTP_SSL (test only) |
| `newEmailHTML.py` | `send_gmail_email_with_html()` | smtplib.SMTP_SSL (test only) |
| `emailProcess/emailG.py` | Main block (line 10) | yagmail (test only) |

**Production email senders:** 3 (AutoReportGen, python/CommunicationMonitor, redONE/CommunicationMonitor).  
**Test/scratch senders:** 4.

### b. Separate DB connection setups

`getConnectionDetails(connNum)` is copy-pasted identically (or near-identically) in every single file. Each file opens its own connections inline.

| File | Copies of getConnectionDetails | Direct psycopg2.connect() calls in main body |
|---|---|---|
| `AutoReportGen.py` | 1 | 3 (in different functions) |
| `python/bin/CommunicationMonitor.py` | 1 | 4+ |
| `python/bin/JobScheduler.py` | 1 | 8+ (one per function + main) |
| `python/bin/ReportConfig.py` | 1 | 6+ |
| `python/bin/SFTPManagement.py` | 1 | 7+ |
| `python/bin/dataLoader.py` | 1 | 5+ |
| `python/bin/FileZip.py` | 1 | 1 |
| `python/bin/loadCSVdata.py` | 1 | 1 |
| `python/bin/loadAgentList.py` | 0 (hardcoded) | 1 |
| `python/bin/refreshMaterlizedViews.py` | 1 | 1 |
| `python/bin/refreshMaterlizedViewsNC.py` | 1 | 3 |
| `python/bin/refreshMaterlizedViews_One.py` | 1 | 3 |
| `redONE/bin/CommunicationMonitor.py` | 1 | 4+ |
| `redONE/bin/JobScheduler.py` | 1 | 8+ |
| `redONE/bin/ReportConfig.py` | 1 | 6+ |
| `redONE/bin/SFTPManagement.py` | 1 | 7+ |
| `redONE/bin/dataLoader.py` | 1 | 5+ |
| `redONE/bin/checkSuspendedSubscription.py` | 1 | 3 |
| `redONE/bin/restAPI_PROD_createPurchase.py` | 1 | 1 |
| `work/EndZeroPackage/removeOCSSubscriptionIDProcess.py` | 1 | 1 |

**Total `getConnectionDetails()` duplicates: ~19 copies** across 20 files.

### c. Copy-pasted utility functions

| Function | Files it appears in | Notes |
|---|---|---|
| `getConnectionDetails(connNum)` | 19+ files | **Exact copy in every file** |
| `replaceTextConstants(textValue)` | `python/bin/CommunicationMonitor.py`, `python/bin/JobScheduler.py`, `redONE/bin/CommunicationMonitor.py`, `redONE/bin/JobScheduler.py`, `redONE/bin/dataLoader.py` | Slight variations: redONE version has more tokens |
| `getFullFileName()` | `python/bin/JobScheduler.py`, `redONE/bin/JobScheduler.py`, `python/bin/ReportConfig.py`, `redONE/bin/ReportConfig.py` | Different signatures but same logic |
| `outputZipFile()` | `python/bin/JobScheduler.py`, `redONE/bin/JobScheduler.py`, `python/bin/FileZip.py` | Exact copy |
| `insertReportInformation()` | `AutoReportGen.py`, `python/bin/ReportConfig.py`, `redONE/bin/ReportConfig.py` | Near-identical |
| `loadingCSVdata()` | `python/bin/dataLoader.py`, `redONE/bin/dataLoader.py`, `python/bin/loadCSVdata.py` | Core logic identical |
| `getFileRecords()` | `python/bin/dataLoader.py`, `redONE/bin/dataLoader.py` | Exact copy |
| `delete_file()` | `python/bin/dataLoader.py`, `redONE/bin/dataLoader.py` | Exact copy |
| `unzip_gz()` | `python/bin/dataLoader.py`, `redONE/bin/dataLoader.py` | Exact copy |
| `getLastMonthFirstLastdate()` | `AutoReportGen.py`, `python/bin/ReportConfig.py`, `redONE/bin/ReportConfig.py` | Exact copy |
| `upload_file()` | `python/bin/JobScheduler.py`, `redONE/bin/JobScheduler.py`, `gmailDrive3.py` | Near-identical |
| `execute_python_file()` | `python/bin/JobScheduler.py`, `redONE/bin/JobScheduler.py` | Exact copy |
| `insertSchInform()` | `python/bin/JobScheduler.py`, `redONE/bin/JobScheduler.py` | Exact copy |
| `updateNextDateLastDate()` | `python/bin/JobScheduler.py`, `redONE/bin/JobScheduler.py` | Exact copy |
| `attachmentToMail()` | `python/bin/CommunicationMonitor.py`, `redONE/bin/CommunicationMonitor.py` | Exact copy |

### d. Functions that do more than one thing

| Function | File | What it does | Why it needs splitting |
|---|---|---|---|
| `emailRequest()` in `JobScheduler.py` | Both versions | Queries email config from DB AND constructs email body AND inserts into jv_emailrequest queue | Should be: `get_email_config()` + `build_email_body()` + `queue_email()` |
| `ReportConfig.py` main block | Both versions | Parses args, queries config, generates Excel/CSV, inserts audit record | Should be: `load_report_config()` + `generate_report()` + `record_audit()` |
| `JobScheduler.py` main block | Both versions | Reads schedule, loops jobs, executes processes, zips files, uploads Drive, queues email | Should be separate pipeline runner functions |
| `CommunicationMonitor.py` main block | Both versions | Queries pending emails, builds MIME message, attaches files, sends email, updates status | Should be: `get_pending_emails()` + `build_message()` + `send_email()` + `mark_sent()` |
| `checkFileError()` | `SFTPManagement.py` | Connects to SFTP, reads file line-by-line, parses log dates, checks against error patterns, writes output file, updates last-run | Should be: `read_sftp_log()` + `filter_errors()` + `write_error_file()` |
| `getCSVorJSONData()` | `ReportConfig.py` | Generates both CSV and JSON in one function via completely different code paths | Should be: `generate_csv()` + `generate_json()` |

### e. Single biggest duplication

`getConnectionDetails(connNum)` — copy-pasted **19 times** across the entire codebase. This 10-line function reads the same JSON file, loops the same data structure, and returns the same 4-tuple. It is the first thing to consolidate.

---

## 5. CODE QUALITY

### Files with no error handling at all

| File | Risk |
|---|---|
| `AutoReportGen.py` | Any DB failure, file failure, or email failure crashes with unhandled exception |
| `JobScheduler.py` (main block) | DB connection failure at startup crashes silently |
| `ReportConfig.py` | File write errors not caught; DB errors crash mid-report |
| `refreshMaterlizedViews.py` | Procedure failure not handled |
| `refreshMaterlizedViewsNC.py` | Procedure failure not handled |
| `refreshMaterlizedViews_One.py` | Loop continues after unhandled exception |
| `FileZip.py` | File-not-found not handled |
| `loadAgentList.py` | No error handling whatsoever |
| `CommunicationMonitor.py` (both versions) | Email sending failures not caught — one bad row crashes the entire loop |

### SQL built by f-string or string formatting (SQL injection risk)

Every single SQL statement in the codebase is constructed via f-string. This is a pervasive risk. Representative examples:

| File | Line | SQL Construction |
|---|---|---|
| `AutoReportGen.py` | 46 | `f"select coalesce...WHERE ReportID ="+f"{ReportID}"` |
| `AutoReportGen.py` | 64 | `f"insert into JV_REPORTAUDITSUMMARY...values({ReportID},'{ReportName}'..."` |
| `CommunicationMonitor.py` | 58 | `f"select...where je.emailconfigid ={emailConfigID}..."` |
| `CommunicationMonitor.py` | 108 | `f"update jv_emailrequest set emailrequeststatus =2 where emailrequestid = {emailRequestID}"` |
| `JobScheduler.py` | 147–156 | `f"insert into jv_emailrequest...values ('{emailSentDateTime}',{emailConfigID},'{subjectTxt}'..."` |
| `JobScheduler.py` | 250–252 | `f"update jv_schedulerconfig set nextrundate = '{nextDate}'..."` |
| `ReportConfig.py` | 116 | `f"CREATE TABLE {backupTable} AS ({sqlQuery} );"` — table name from user data |
| `SFTPManagement.py` | 123 | `f"select...where sh.sftpconfigid={sftpConfigID}..."` |
| `dataLoader.py` | 117 | `f'select count(*) from {tempTableName} jd'` — table name from config |
| `dataLoader.py` | 131 | `f'insert into {csv_tablename} select a.*,...'` — table name from config |
| `refreshMaterlizedViews_One.py` | 55 | `f"update jv_materializedviewauditsummary...where mvrunid = (select max...)"` |
| `testSQL.py` | 24 | `psycopg2.connect(host="172.27.7.230",...,password="Password@01")` |

**All SQL must be rewritten with parameterized queries before GitHub.**

### Hardcoded credentials

| File | Line(s) | What is hardcoded |
|---|---|---|
| `AutoReportGen.py` | 142–145 | Gmail address `jagdeepvirdi@advancetech.co.th`, app password `tmoowhdtvbacqwiw`, recipient list |
| `emailAttachment.py` | 2–3 | Gmail `jagdeep.singh.virdi@gmail.com`, app password `ugiewenekvqlbfhz` |
| `newEmail.py` | 4 | SMTP password `lsdqpmqqtwqoemlb` (in login call) |
| `newEmailHTML.py` | 27 | SMTP password `lsdqpmqqtwqoemlb` |
| `emailProcess/emailG.py` | 2–3 | Gmail `jagdeep.singh.virdi@gmail.com`, app password `ldnktthysezibgbt` |
| `emailProcess/gmailAuth.json` | 3 | Gmail app password `ldnktthysezibgbt` |
| `otherPythonScripts/AutoReports/connection.json` | 9, 15 | DB password `harpal123` for `redoneDB` |
| `loadAgentList.py` | 7–9 | Host `172.27.7.230`, password `Password@01` |
| `testSQL.py` | 24 | Host `172.27.7.230`, password `Password@01` |
| `python/rough/settings.yaml` | 3 | Google OAuth `client_id` and `client_secret: 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` |
| `redONE/bin/restAPI_PROD_createPurchase.py` | 41 | OCS API credentials `jagdeeps` / `Password@01` |
| `JobScheduler.py` (both) | 20–23 | Service account file paths |

### Functions over 50 lines that need breaking up

| File | Function / Block | ~Lines | Issue |
|---|---|---|---|
| `CommunicationMonitor.py` (both) | Main block | ~90 | Reads DB, builds MIME, attaches files, sends, updates — all inline |
| `python/bin/JobScheduler.py` | Main block | ~100 | Entire orchestration loop inline |
| `redONE/bin/JobScheduler.py` | Main block | ~100 | Same |
| `redONE/bin/JobScheduler.py` | `getGeneratedReportList()` | ~80 | Complex branching output builder |
| `redONE/bin/JobScheduler.py` | `emailRequest()` | ~70 | DB query + body construction + INSERT |
| `SFTPManagement.py` | `checkFileError()` | ~60 | SFTP connect + log parse + error filter + file write + DB update |
| `redONE/bin/dataLoader.py` | Main block | ~120 | Two separate loader types in one block |
| `ReportConfig.py` (both) | Main block | ~100 | Arg parse + DB query + report generation + audit insert |

### print() instead of logging

**Every file uses `print()` for all output**, except:
- `JVReportGenerator.py` (has a logging setup but does nothing else)
- `redONE/bin/restAPI_PROD_createPurchase.py` (uses a custom `LOG_MSG()` wrapper with `logging`)

No file uses the Python `logging` module properly for production output.

---

## 6. SCRUB LIST

| File | Line(s) | What it is | Priority |
|---|---|---|---|
| **COMPANY NAMES** | | | |
| All `code/redONE/` files | (dir name) | "redONE" in directory name | MUST REMOVE |
| `refreshMaterlizedViewsNC.py` | 42 | Table name `redonematerializedviewstats` | MUST REMOVE |
| `gmailDrive3.py` | 10 | `redone_file.json` in service account path | MUST REMOVE |
| `redONE/bin/JobScheduler.py` | 20 | `redone_file.json` in SERVICE_ACCOUNT_FILE | MUST REMOVE |
| `loadCSVdata.py` | 54 | `redONE_CDR_2024-06-18_...csv` — company + CDR in filename | MUST REMOVE |
| `otherPythonScripts/AutoReports/connection.json` | 4,10 | `redoneDB` database name | MUST REMOVE |
| **PERSONAL NAMES & PATHS** | | | |
| ALL files | Multiple | `/home/jagdeep/jvirdi/...` hardcoded paths | MUST REMOVE |
| `AutoReportGen.py` | 27,95 | `jagdeep` in file path | MUST REMOVE |
| `AutoReportGen.py` | 142 | `jagdeepvirdi@advancetech.co.th` email | MUST REMOVE |
| `AutoReportGen.py` | 150 | `Regards,\nJagdeep\n` in email body | MUST REMOVE |
| `AutoReportGen.py` | 145 | `jagdeepvirdi@advancetech.co.th` in CC list | MUST REMOVE |
| `emailAttachment.py` | 2 | `jagdeep.singh.virdi@gmail.com` | MUST REMOVE |
| `emailProcess/emailG.py` | 2 | `jagdeep.singh.virdi@gmail.com` | MUST REMOVE |
| `emailProcess/gmailAuth.json` | 2 | `jagdeep.singh.virdi@gmail.com` | MUST REMOVE |
| `newEmail.py` | 5–6 | `jagdeepvirdi@advancetech.co.th` addresses | MUST REMOVE |
| `newEmailHTML.py` | 48–49 | `jagdeepvirdi@advancetech.co.th` addresses | MUST REMOVE |
| `loadAgentList.py` | 7 | `172.27.7.230` internal server IP | MUST REMOVE |
| `testSQL.py` | 24 | `172.27.7.230` internal server IP | MUST REMOVE |
| `FileZip.py` | 46 | `/home/jagdeep/jvirdi/data/DataAnalysis/...` hardcoded path | MUST REMOVE |
| `gmailDrive.py` | 11 | `/home/jagdeep/jvirdi/data/FinanceReports/...` hardcoded path | MUST REMOVE |
| `gmailDrive2.py` | 12 | Same hardcoded path | MUST REMOVE |
| `gmailDrive3.py` | 110 | `/home/jagdeep/jvirdi/data/FinanceReports/...` path | MUST REMOVE |
| **CREDENTIALS** | | | |
| `AutoReportGen.py` | 143 | `app_password = 'tmoowhdtvbacqwiw'` | MUST REMOVE |
| `emailAttachment.py` | 3 | `app_password = 'ugiewenekvqlbfhz'` | MUST REMOVE |
| `emailProcess/emailG.py` | 3 | `app_password = 'ldnktthysezibgbt'` | MUST REMOVE |
| `emailProcess/gmailAuth.json` | 3 | `"app_password":"ldnktthysezibgbt"` | MUST REMOVE |
| `newEmail.py` | 12 | Password `'lsdqpmqqtwqoemlb'` in login | MUST REMOVE |
| `newEmailHTML.py` | 27 | Password `'lsdqpmqqtwqoemlb'` in login | MUST REMOVE |
| `loadAgentList.py` | 9 | `password='Password@01'` | MUST REMOVE |
| `testSQL.py` | 24 | `password="Password@01"` | MUST REMOVE |
| `python/rough/settings.yaml` | 2–3 | OAuth `client_id` and `client_secret` | MUST REMOVE |
| `otherPythonScripts/AutoReports/connection.json` | 9,15 | `"password":"harpal123"` | MUST REMOVE |
| `redONE/bin/restAPI_PROD_createPurchase.py` | 41 | `'password': 'Password@01'` | MUST REMOVE |
| **INTERNAL NETWORK** | | | |
| `loadAgentList.py` | 7 | `172.27.7.230` internal DB IP | MUST REMOVE |
| `testSQL.py` | 24 | `172.27.7.230` internal DB IP | MUST REMOVE |
| `otherPythonScripts/AutoReports/connection.json` | 5,11 | `192.168.1.35`, `192.168.99.112` internal IPs | MUST REMOVE |
| `redONE/bin/restAPI_PROD_createPurchase.py` | 44 | `172.27.6.115:9000` OCS internal URL | MUST REMOVE |
| `redONE/bin/restAPI_PROD_createPurchase.py` | 110 | `172.27.6.115:9000` in URL template | MUST REMOVE |
| **INTERNAL EMAILS** | | | |
| `AutoReportGen.py` | 144 | `operations@redone.co.th` | MUST REMOVE |
| `AutoReportGen.py` | 145 | `surakun.paenoi@redone.co.th`, `ameera.useng@redone.co.th`, `suwit.manggornsilanon@redone.co.th` | MUST REMOVE |
| `emailAttachment.py` | 5 | `jagdeepvirdi@advancetech.co.th` | MUST REMOVE |
| `newEmail.py` | 5–6 | `jagdeepvirdi@advancetech.co.th` | MUST REMOVE |
| **TELECOM-SPECIFIC TERMS** | | | |
| `redONE/bin/checkSubOCSStatus.py` | Throughout | `MSISDN`, `OCS`, `subscription`, `networkserialnumber`, `pvsubscription`, `pg_rep_db` | MUST REMOVE (file) |
| `redONE/bin/checkSuspendedSubscription.py` | Throughout | `OCS`, `subscription`, `networkserialnumber`, `pvsubscription` | MUST REMOVE (file) |
| `redONE/bin/restAPI_PROD_createPurchase.py` | Throughout | `POSTPAID`, `purchase`, `REDDP`, `mvsit_subscription` | MUST REMOVE (file) |
| `refreshMaterlizedViewsNC.py` | 42 | `redonematerializedviewstats` table name | MUST REMOVE |
| `loadCSVdata.py` | 54 | CDR filename reference | MUST REMOVE |
| **TABLE NAME PREFIX** | | | |
| All files | Throughout | `jv_` prefix on all tables (author's initials) | SHOULD REMOVE |
| **INTERNAL COMPANY NAMES** | | | |
| `AutoReportGen.py` | 145 | `advancetech.co.th` domain | MUST REMOVE |
| Various | Multiple | `advancetech` references | MUST REMOVE |
| **BASE64-ENCODED SQL** | | | |
| `otherPythonScripts/AutoReports/config_data.json` | 10,16,28 | Base64 SQL queries referencing internal tables | SHOULD REMOVE |

---

## 7. REUSE PLAN

### Mapping existing code to FlowForge step types

**`db_procedure` step**
- Existing code: `refreshMaterlizedViews.py`, `refreshMaterlizedViewsNC.py`, `refreshMaterlizedViews_One.py`
- What they do: Call PostgreSQL stored procedures/functions via `cursor.execute("CALL ...")`
- Reuse verdict: **Can be wrapped with minor refactoring.** Extract the execute logic into a `PostgreSQLConnection.execute_procedure()` method. The DB-driven config table (`jv_materializedviewrefreshconfig`) already exists and can inform the FlowForge `db_procedure` step config structure.
- Changes needed: Parameterized queries, connection from env/DB not JSON file, error handling

**`db_query` step**
- Existing code: `dataLoader.py` (SQL_LOADER type), `BackUpData()` in `ReportConfig.py`
- What they do: Execute arbitrary SQL, write results to tables (`CREATE TABLE AS`, `INSERT INTO`)
- Reuse verdict: **Core logic reusable, needs significant refactoring.** The `SQL_LOADER` type in `redONE/dataLoader.py` is the closest match to FlowForge's `db_query` step. Needs: parameterized queries, proper `replace/append/truncate_insert` modes, error handling, logging.
- Changes needed: Major refactor. Currently uses f-string SQL and table names from config without sanitization.

**`report` step**
- Existing code: `python/bin/ReportConfig.py` or `redONE/bin/ReportConfig.py` (preferred — same logic)
- What it does: Reads report config from DB, executes multi-sheet queries, generates Excel file, records audit
- Reuse verdict: **Core Excel generation logic is solid — wrap as a class.** The `openpyxl` Workbook creation, sheet-per-query pattern, and audit trail are all correct.
- Changes needed: Extract into `ExcelReport` class, replace custom date tokens with Jinja2, parameterize SQL, remove hardcoded paths, add error handling, support PDF/CSV formats.

**`email` step**
- Existing code: `redONE/bin/CommunicationMonitor.py` (newest version)
- What it does: Reads pending email requests from queue, builds MIME messages, sends via SMTP_SSL or STARTTLS, supports attachments
- Reuse verdict: **Architecture needs rethinking but core SMTP logic is reusable.** The current design uses a queue table (`jv_emailrequest`) as an intermediary — FlowForge will call the email provider directly in-process, not via a separate monitor process. The MIME construction and multi-provider routing logic can be extracted.
- Changes needed: Significant restructuring. Extract SMTP send logic into `SMTPProvider` class. Remove queue-based design. Smart attachment logic (Drive fallback) needs to be added — it doesn't exist yet.

**`drive_upload` step**
- Existing code: `gmailDrive3.py` `upload_file()` function, also duplicated in `JobScheduler.py`
- What it does: Uploads files to Drive using service account, returns file ID
- Reuse verdict: **Can be wrapped as-is with one important change.** The existing service account auth works but CLAUDE.md plans OAuth2 auth instead (user's own account rather than a service account). The `files().create()` call itself is identical regardless of auth method.
- Changes needed: Swap service account for OAuth2 flow, add `make_shareable=True` permission setting (not currently implemented — link is only returned, not made public), switch from hardcoded zip MIME to dynamic MIME detection.

**`sftp` step (backlog v2)**
- Existing code: `SFTPManagement.py`
- What it does: DOWNLOAD/UPLOAD/CHECK/CHECKERROR operations via pysftp
- Reuse verdict: **Full SFTP management ready — add to backlog, not v1.** CLAUDE.md doesn't include SFTP in v1 step types but the code is complete.

### Existing DB tables that become FlowForge config tables

| Existing Table | Becomes FlowForge Table | Notes |
|---|---|---|
| `jv_reportconfig` | `report_configs` | Rename, add `connection_id` FK, rename `reportextentiontype` → `format` |
| `jv_reporthasquery` | Merge into `report_configs.query` | FlowForge puts query directly in report_configs for simplicity; if multi-sheet needed, keep as separate table |
| `jv_emailconfig` + `jv_emailuserdetails` | `email_configs` + `email_providers` | Split: provider credentials → `email_providers` (encrypted); email template → `email_configs` |
| `jv_emailconfigrecipient` | `recipient_groups` | Rename, restructure |
| `jv_schedulerconfig` + `jv_schedulerhasprocess` + `jv_processbinary` | `pipelines` + `pipeline_steps` | Major restructuring — current model is process-centric; FlowForge is step-type-centric |
| `jv_reportauditsummary` + `jv_scheduleauditsummary` | `pipeline_runs` + `step_runs` | Combine audit tables into unified run history |
| `jv_sftpconfig` + `jv_sftpconnectiondetails` | (backlog) | Keep for SFTP step v2 |
| `jv_dataloaderconfig` + `jv_dataloadersql` | Merge into `pipeline_steps` config JSONB | Becomes `db_query` step config |

### Tables that must be created fresh (do not exist in current schema)

- `db_connections` — current code reads from JSON file; no DB table for connection config
- `pipeline_variables` — no equivalent
- `email_providers` — credentials currently in `jv_emailuserdetails` (plaintext, no encryption)
- `crypto` infrastructure — no encryption exists today

---

## 8. CONTRADICTIONS WITH PLANNED ARCHITECTURE

**All contradictions between the existing codebase and CLAUDE.md's planned architecture:**

| CLAUDE.md Assumption | Reality in Existing Code | Impact |
|---|---|---|
| **Auth: Google Drive via OAuth2** | Service account JSON file (`file.json`) | Must implement OAuth2 flow; service account won't work for user-specific Drive folders |
| **Auth: Gmail via OAuth2 + google-auth library** | Existing code uses SMTP app password (yagmail) or generic SMTP | Gmail OAuth2 is the correct target; SMTP app passwords are deprecated by Google |
| **All config stored in PostgreSQL DB** | DB connections read from `connection.json` file with hardcoded path | Must add `db_connections` table; cannot use any file-based config |
| **Scheduler: APScheduler with PostgreSQL job store** | OS cron + custom subprocess orchestrator in `JobScheduler.py` | Complete rewrite of scheduling layer; existing scheduler code not reusable |
| **Flask REST API frontend** | No web API exists — all scripts are CLI-only | Full greenfield build for API + frontend |
| **Jinja2 variable system** (`{{ current_month }}`) | Custom string token system (`XYYYYMMX`, `XCYYYYMMX`, `XLYYYYMMX`, etc.) | Token system must be replaced with Jinja2; mapping: `XCYYYYMMX` → `{{ current_month }}` etc. |
| **Parameterized SQL (no string formatting)** | 100% of SQL uses f-strings | Every SQL statement must be rewritten |
| **AES-256-GCM credential encryption** | Plaintext passwords in DB and JSON files | Encryption layer is entirely new; no existing implementation to build on |
| **Oracle + PostgreSQL equal support** | PostgreSQL only (psycopg2); no Oracle code anywhere | Oracle support is greenfield |
| **Step types include: db_procedure, db_query, report, email, drive_upload** | No typed step abstraction; each script is its own monolith | Step type abstraction is new; existing scripts map approximately to step types but need wrapping |
| **Report formats: Excel, PDF, CSV** | Excel only (openpyxl); CSV via PostgreSQL COPY (broken); no PDF | PDF is greenfield (weasyprint); CSV needs rewrite in Python |
| **Email providers: Gmail OAuth2, Microsoft 365 MSAL, SMTP** | Only SMTP and SMTP_SSL implemented; no MSAL | Microsoft 365 via MSAL is greenfield |
| **Smart attachment: Drive upload if > threshold** | Not implemented — all attachments sent directly or all via Drive; no size threshold logic | Smart attachment logic is new |
| **Recipient groups** (`recipient_groups` table) | `jv_emailconfigrecipient` with TO/CC/BCC per email config (not reusable groups) | Minor schema restructuring needed |
| **Pipeline variables** with `is_secret` flag | No equivalent — variables are hardcoded or passed as CLI args | New table required |
| **Single-user JWT auth** | No auth at all | Greenfield |
| **Connection pooling** | No pooling — fresh connection per function call | Must add `ThreadedConnectionPool` |
| **No YAML for normal operation** | No YAML currently used (except `settings.yaml` credentials file) | Actually aligned — current code is already DB-driven for config |
| **SFTP as backlog item (not in v1)** | Full SFTP implementation already exists and is production-ready | SFTP step could be added to v1 with less effort than planned |

---

## 9. RECOMMENDATIONS

### a. Top 3 duplications to eliminate first

1. **`getConnectionDetails()` — extract to a single `connections.py` module.** This is copied 19 times. Every file needs to import one function. This also enables swapping the JSON file for the `db_connections` table in one place.

2. **`replaceTextConstants()` — replace entirely with Jinja2.** This is the existing variable system. Rather than consolidating the 5 copies, replace it with Jinja2 rendering. Map each `XYYYYMMX` token to a `{{ current_month }}` equivalent. This also eliminates the function entirely.

3. **`getConnectionDetails()` + the JSON file config — replace both with `db_connections` table.** The JSON config file is the root cause of 19 copies. Once DB-driven, all scripts can share a single connection-loading function that reads from the DB.

### b. Safest refactor order

1. **Scrub first** — remove all credentials, internal names, and telecom-specific files before any restructuring. A dirty scrub of a flat codebase is safer than a dirty scrub of a refactored one.

2. **Extract `getConnectionDetails()` into a shared module** — lowest risk change. Every script can import it. Test by running each script in sequence.

3. **Extract `replaceTextConstants()` to a Jinja2 context builder** — medium risk. Test by verifying output filenames and email subjects still resolve correctly.

4. **Wrap report generation into `ExcelReport` class** — low risk, well-isolated. The Excel logic is already functionally correct.

5. **Wrap SMTP email into `SMTPProvider` class** — medium risk. Test with real email send.

6. **Wrap Drive upload into `GoogleDriveStorage` class** — low risk, already isolated in `gmailDrive3.py`.

7. **Build `pipeline_runner.py` as the new `JobScheduler.py`** — highest risk. Do this last, after step implementations are tested.

### c. What to keep vs rewrite

**Keep with minor cleanup:**
- Excel report generation (`openpyxl` Workbook logic from `ReportConfig.py`) — solid, tested in production
- SFTP operations (`SFTPManagement.py`) — complete, tested, add to v1 as bonus step type
- Date calculation logic from `replaceTextConstants()` — correct, just needs Jinja2 wrapping
- Drive upload core (`upload_file()` from `gmailDrive3.py`) — correct, just needs auth swap
- Audit trail structure (report, schedule, SFTP audit tables) — good pattern, rename and restructure

**Needs significant refactoring (rewrite structure, not logic):**
- `CommunicationMonitor.py` → `SMTPProvider` class — extract send logic, add multi-provider support, remove queue dependency
- `ReportConfig.py` → `ExcelReport` class — extract Excel logic, add parameterized SQL, add Jinja2 filename
- `dataLoader.py` → `db_query` step — generalize, add proper modes (replace/append/truncate_insert), parameterize SQL

**Full rewrite (architecture too different):**
- `JobScheduler.py` → FlowForge pipeline runner + APScheduler — the subprocess-orchestrator model is incompatible with the in-process step execution model
- Email queue (`jv_emailrequest`) pattern → direct provider call in step — the queue intermediary adds unnecessary complexity for FlowForge's model
- `getConnectionDetails()` + JSON file → `db_connections` table + connection factory

### d. Risks and surprises

1. **The Google Drive auth model mismatch is the most impactful surprise.** The existing code uses a service account (Google Workspace admin setup required). CLAUDE.md plans OAuth2 (user-consent-based). These are completely different auth flows. If the target users don't have Google Workspace admin access, service account setup is a barrier. OAuth2 is the right choice for an open-source tool but requires implementing the entire refresh-token flow from scratch.

2. **There is no Oracle code anywhere.** CLAUDE.md plans "equal support" for Oracle. This is entirely greenfield work. Plan extra time; cx_Oracle with Instant Client is notoriously difficult to set up correctly on different platforms.

3. **The CSV generation is broken** (`getCSVorJSONData()` uses a literal string `{QueryTxt}` instead of an f-string). This means CSV reports have never worked in production. Do not carry forward this implementation.

4. **The `jv_emailrequest` queue architecture will cause a design decision.** Currently, `JobScheduler.py` writes to `jv_emailrequest` and a separate `CommunicationMonitor.py` process polls and sends it. FlowForge's in-process model calls the provider directly. This means the queue table is eliminated — but if you want to keep the "send at a scheduled time" feature (the `senddtm` field in `jv_emailrequest`), that logic needs to move to the scheduler layer.

5. **All Gmail app passwords in the code may be revoked.** Google deprecated app passwords for most accounts. Do not test with these — they may trigger security alerts or fail entirely. Use OAuth2 from day one.

6. **The `jv_` table prefix is pervasive** — every table starts with it. Renaming to neutral FlowForge names (`pipelines`, `pipeline_steps`, etc.) will require a full schema migration and updates across all scripts. Budget time for this in the scrub phase.

7. **The existing scheduler has a "run now" gap.** `JobScheduler.py` only runs schedulers whose `nextrundate` is due. There is no "run immediately" trigger — this would need to be added for the FlowForge "Run Now" button. The APScheduler model handles this natively.

---

*Review complete. All findings above are based on reading source code only. No code was changed.*
