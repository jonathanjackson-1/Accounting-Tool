# Accounting Tool (Agents Workflow)

## Purpose
Deliver a cloud-enabled accounting assistant that accepts CSV/XLSX exports, orchestrates OpenAI’s Agents SDK to interpret those files, and returns structured Income Statement, Cash-Flow summary, and Expense Breakdown JSON payloads that downstream UI components render into reports and exports.

---

## Cloud Workflow Overview
1. **User Upload** – UI accepts CSV/XLSX files, performs light validation, and uploads them to your backend.
2. **Files API** – Backend streams each file to `POST /v1/files` (or the Agents SDK equivalent) with `purpose="assistants"`; captured `file.id`s are stored for the run.
3. **Agent Run** – Backend creates an agent/assistant thread, attaches the uploaded `file.id`s to a user message, and kicks off a run. System instructions enforce the JSON schemas for Income Statement, Cash-Flow, and Expense Breakdown outputs.
4. **Structured Output** – Agent returns a strictly validated JSON response (via `response_format={"type": "json_schema", "json_schema": {...}, "strict": true}`), which the backend parses into domain objects and caches for rendering/export.

Optional deterministic tools (registered with Agents) can be used to perform calculations like grouping and summing, ensuring numerical accuracy for large ledgers.

---

## JSON Schema Contracts
In the system prompt (or assistant configuration), include compact schemas the agent must satisfy. Example fragments:

```json
{
  "name": "income_statement_schema",
  "schema": {
    "type": "object",
    "required": ["periods"],
    "properties": {
      "periods": {
        "type": "array",
        "items": {
          "type": "object",
          "required": [
            "label", "revenue", "cogs", "gross_profit",
            "operating_expenses", "operating_income",
            "other_net", "taxes", "net_income", "margins"
          ],
          "properties": {
            "label": {"type": "string"},
            "revenue": {"type": "number"},
            "cogs": {"type": "number"},
            "gross_profit": {"type": "number"},
            "operating_expenses": {"type": "number"},
            "operating_income": {"type": "number"},
            "other_net": {"type": "number"},
            "taxes": {"type": "number"},
            "net_income": {"type": "number"},
            "margins": {
              "type": "object",
              "required": ["gross", "operating", "net"],
              "properties": {
                "gross": {"type": "number"},
                "operating": {"type": "number"},
                "net": {"type": "number"}
              }
            }
          }
        }
      }
    }
  },
  "strict": true
}
```

Define analogous schemas for:
- **CashFlow** – fields: `operating`, `investing`, `financing`, `net_change`.
- **ExpenseBreakdown** – nested objects: `by_category`, `by_vendor`, `by_month`, each a map of label → numeric total (or arrays of labeled totals).

Include schema names and references in the run’s `response_format`. Supply tiny example rows in the prompt to anchor format expectations.

---

## System & User Prompt Outline
- **System message**  
  - Explain high-level goal: “Read attached financial spreadsheets. Produce JSON that matches the provided schemas for IncomeStatement, CashFlow, ExpenseBreakdown. No commentary. Handle commas-as-decimals, parentheses as negatives, and blank lines gracefully.”
  - Mention available tool calls (if any), the expectation to summarize periods by month unless data suggests otherwise, and reminders to emit numbers (not strings) where schema defines `number`.
- **User message**  
  - Attaches `file.id`s and states context: provider (QuickBooks, Stripe, POS, bank). Optionally mention fiscal start month, currency, or sample chart-of-accounts categories.
  - Provide micro examples (2–3 rows) inline to highlight tricky formats.

---

## Backend Responsibilities
1. **Upload API**
   - Accept multipart file uploads from the UI.
   - Pre-clean simple quirks (strip BOM, normalize commas to periods, convert parentheses to negatives if confident).
   - Enforce file-size caps and optionally split heavy ledgers into monthly files before sending upstream.

2. **OpenAI Orchestration**
   - Authenticate requests with API key scoped to Agents SDK.
   - Maintain thread IDs per user session; reuse for multi-file workflows if appropriate.
   - Poll runs until completion; capture JSON result payload.
   - Optionally invoke deterministic aggregation tools (registered as function/tool calls) when the agent requests them.

3. **Result Processing**
   - Validate returned JSON against schemas (double-check, even though strict mode is set).
   - Persist summaries to the application database (e.g., PostgreSQL or SQLite) alongside the original file metadata.
   - Generate tabular views, charts, and exports (CSV/XLSX/PDF) locally once structured data is available.

4. **Cleanup & Retention**
   - Decide how long to retain OpenAI `file.id`s and local caches.
   - Optionally call the Files API delete endpoint after runs complete.

---

## Privacy & Compliance Considerations
- Clarify in onboarding and privacy policy that uploads are sent to OpenAI for processing. Link OpenAI’s enterprise privacy statement.
- For enterprise customers, leverage zero-retention or short-retention controls if available.
- Document retention policy for stored `file.id`s and generated reports; delete promptly on user request.
- Flag that temporary policy adjustments (e.g., legal retention holds) may affect non-enterprise tiers.

---

## Implementation Roadmap
1. **Project Setup**
   - Finalize Python backend scaffold (FastAPI/Flask) or Node/TypeScript equivalent.
   - Configure environment variables for OpenAI keys, retention toggles, and storage locations.
   - Add schema definitions (shared module) used by both prompts and backend validation.

2. **File Intake Service**
   - Build upload endpoint with size/type validation.
   - Integrate light preprocessing (encoding fixes, decimal normalization).
   - Store files temporarily (local or object storage) before forwarding to OpenAI.

3. **OpenAI Integration**
   - Implement Files API wrapper.
   - Create Agent/Thread service: generates system prompt, attaches files, submits user message, polls runs, handles errors/timeouts.
   - Add structured output enforcement and fallback logic if schema validation fails.

4. **Deterministic Tooling (Optional MVP+)**
   - Register simple aggregation tool with the agent for sums/grouping.
   - Provide backend endpoint executed when model invokes tool calls.

5. **Result Rendering**
   - Map structured JSON to report DTOs.
   - Build UI components to render Income Statement, Cash-Flow, and Expense Breakdown.
   - Implement local export pipeline (pandas/pyarrow for CSV/XLSX, WeasyPrint/ReportLab for PDF).

6. **Persistence & Audit**
   - Log uploaded file metadata, agent run IDs, and outputs.
   - Track user sessions and export requests for analytics/audit.

7. **Compliance & UX Polish**
   - Add privacy/terms links, retention disclaimers, user consent checkboxes.
   - Implement delete flow to erase stored data and optionally trigger OpenAI file deletion.
   - Add notifications when runs complete or fail; surface retry options.

8. **Testing & Monitoring**
   - Unit tests for schema validation, API clients, and export generation.
   - Integration tests hitting OpenAI’s sandbox (or mocked responses) to verify prompt/response pipeline.
   - Metrics/logging for run durations, error rates, schema violations.

---

## Deployment Plan
1. **Staging Environment**
   - Deploy backend (e.g., to Render, Heroku, Fly.io, or containerized on AWS ECS/EKS).
   - Configure environment secrets (OpenAI API key, database credentials).
   - Connect to managed database (PostgreSQL) for metadata storage.

2. **Front-End**
   - Host static UI (React/Vue/Svelte) on Vercel/Netlify or integrate directly into backend.
   - Ensure chunked uploads and progress indicators for large files.

3. **Observability**
   - Add structured logging (request IDs, run IDs).
   - Wire error reporting (Sentry, Honeybadger).
   - Monitor OpenAI usage quotas and rate limits; set alerts.

4. **Security**
   - Enforce HTTPS, CSRF protection, and authenticated access (OAuth, email link, or SSO).
   - Sanitize filenames and store files in dedicated, access-controlled buckets.

5. **Go-Live Checklist**
   - Run regression suite on staging with representative files.
   - Verify structured JSON outputs persist and render correctly.
   - Confirm privacy disclosures, ToS links, and optional retention toggles are visible.
   - Prepare customer support playbook for upload errors or schema mismatch responses.

---

## Backend Skeleton (This Repository)
- Minimal FastAPI staging backend providing:
  - `POST /api/uploads` – accepts CSV/XLSX files and forwards them to OpenAI's Files API.
  - `POST /api/runs` – triggers agent orchestration with provided file IDs and instructions.
  - `GET /health` – health probe used for readiness checks.
- Configuration via environment variables:
  - `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_ASSISTANT_ID`, `ENVIRONMENT`, `CORS_ALLOW_ORIGINS`, `DATA_DIRECTORY`, `DATABASE_PATH`.
  - Upload and run metadata persist to a lightweight SQLite store at `DATABASE_PATH` (defaults to `<DATA_DIRECTORY>/metadata.db`).

### Local Development Quickstart
- Create environment and install deps:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e .
  ```
- Launch API with reload:
  ```bash
  uvicorn app.main:create_app --factory --reload
  ```
- Smoke test endpoints:
  - `curl http://127.0.0.1:8000/health`
  - `curl -F "file=@sample.csv" http://127.0.0.1:8000/api/uploads`

Set `OPENAI_API_KEY` and `OPENAI_ASSISTANT_ID` to enable real OpenAI integrations. Without these values, requests will return 502 errors indicating missing configuration.

Update `app/services/agent_service.py` to replace stubs with real OpenAI calls when ready, and extend API routes as orchestration requirements grow.

---

## Good Practices Recap
- Keep uploads lean; split very large ledgers.
- Pre-clean obvious formatting quirks before sending to the agent.
- Provide example snippets in prompts to guide consistent output.
- Delete OpenAI files after retrieval if retention is not required.
- Register deterministic tools for numerical operations where precision is critical.

---

This README now reflects the OpenAI Agents-based architecture, structured output workflow, and deployment plan needed to ship the cloud-integrated accounting assistant. 
