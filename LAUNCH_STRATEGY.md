# FlowForge — Launch & Article Strategy

This file contains consolidated advice, templates, and recommendations for the v1.0 and v2.0 marketing push. **Note: This file is gitignored.**

---

## 1. LinkedIn Post Templates (Short-form)

### Option A: The "Maintenance-Free" Pitch
> **Stop writing boilerplate scripts for database automation. 🚀**
> I’ve spent too many hours maintaining messy Python and Bash scripts just to send a weekly SQL report to a stakeholder. So, I built something better: **FlowForge**.
> ... (Problem → Solution → Quality Evidence)

### Option B: The "Technical Excellence" Pitch
> **Quality isn't an afterthought—it's the foundation. 🏗️**
> Today I’m officially introducing **FlowForge**. We just hit a **Straight A** rating on SonarCloud for Security, Reliability, and Maintainability.
> ... (Focus on SonarCloud & Dependability)

---

## 2. LinkedIn Article Structure (Long-form)

**Title:** "Beyond the Cron Job: Why I Built FlowForge to Automate Database Pipelines"

1.  **The Hook:** The "Script Sprawl" problem.
2.  **Introducing FlowForge:** The SQL-native orchestrator.
3.  **The Philosophy:** No-YAML, No-Code (for SQL users).
4.  **Feature Deep-Dive (Gifs):**
    -   Pipeline Builder (Step-by-step logic)
    -   Smart Attachments (Drive/OneDrive routing)
    -   AI Features (SQL Explainer/Optimizer via Ollama, with optional Claude/Gemini fallback)
5.  **Engineering Standards:** SonarCloud Straight-A proof.
6.  **Roadmap:** v2.0 Hardening (SSO, MFA, Metrics).
7.  **CTA:** Star on GitHub, join the conversation.

---

## 3. Mandatory Screenshot List (for Docs & Articles)

| ID | Description | Context |
|---|---|---|
| **1** | Dashboard (Empty/First Run) | Getting Started |
| **2** | Connection Setup (Success Toast) | Reliability Proof |
| **3** | Report Designer (SQL + Preview + AI) | Core Value |
| **4** | Email Designer (Jinja2 + Smart Attachments) | "It just works" |
| **5** | Pipeline Builder (Multi-step flow) | Orchestration |
| **6** | Triggers Card (Webhook tab) | Integration / v1.0 |
| **7** | Run History (Anomaly Alerts) | Observability / v2.0 |
| **8** | SonarCloud Dashboard (Straight A's) | Trust / Security |

---

## 4. Technical "Selling Points"

-   **Zero Cost:** Self-hosted, no per-seat pricing.
-   **Oracle-First:** First-class support for Oracle packages/procedures.
-   **Smart Routing:** Auto-upload to Drive/OneDrive if attachments > 10MB.
-   **Local AI:** Privacy-first SQL help via local Ollama (Llama 3 / Mistral) — Claude or Gemini optional as a fallback/alternative.
-   **Multi-Project:** Organize by team (Finance, HR, etc.) in one instance.

---

## 5. Community Distribution Plan

1.  **r/selfhosted:** Focus on "No-YAML" and Docker simplicity.
2.  **r/Python:** Focus on Flask + Celery + APScheduler architecture.
3.  **r/dataengineering:** Focus on Oracle support and SQL-to-Email automation.
4.  **ProductHunt:** Launch on a Tuesday/Wednesday for max traffic.
5.  **Awesome Lists:** Submit to `awesome-selfhosted` and `awesome-python`.

---

## 6. Phase 5 Showcase Guide (Demo Walkthrough)

### Scenario 1: The "SQL to Insight" (Gifs & Screenshots)
- **Goal:** Show how FlowForge makes data accessible.
- **Action:** Paste the **"Top 20 products by revenue"** query from the `retail_db` README.
- **Capture:**
    - **Gif:** Click **Preview** → see rows appear → click **Visualize** (AI Chart Generator) → see the bar chart render.
    - **Screenshot:** The side-by-side view of the SQL code and the AI-generated chart.

### Scenario 2: The "Fully Automated Pipeline" (Video)
- **Goal:** Show the "Set and Forget" value.
- **Pipeline Setup:**
    1.  **Step 1 (DB Procedure):** `public.populate_monthly_revenue` with `{"p_month": "2026-05-01"}`.
    2.  **Step 2 (Report):** Use the **"Monthly revenue summary"** query.
    3.  **Step 3 (Email):** Link to the report; set "Smart Attachment" limit to 1MB (to force a Drive upload).
- **Capture:**
    - **Video:** Click **Run Now** → Switch to **Run History** → Show the logs moving through procedure, report, and email.
