# alert-triage

Small test project. You paste a raw alert as JSON, the backend saves it and starts a Temporal workflow. The workflow looks up the owning team, asks an LLM for a triage (probable cause, confidence, severity, action items), saves the result and marks the alert triaged. A React page shows the alerts and their results.

Stack: Django + Django Ninja, Temporal (Python SDK), Pydantic AI, PostgreSQL, React + Vite.

## Run it

You need Docker, Python 3.12+ and Node 20+.

1. Start Postgres and Temporal:

   ```
   cp .env.example .env
   docker compose up -d
   ```

2. Backend setup:

   ```
   cd backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py seed
   ```

3. Start the API (terminal 1) and the Temporal worker (terminal 2, same venv):

   ```
   python manage.py runserver 8000
   python worker.py
   ```

4. Start the frontend (terminal 3):

   ```
   cd frontend
   cp .env.example .env
   npm install
   npm run dev
   ```

   Open http://localhost:5173. The Temporal UI is at http://localhost:8233.

5. Try it from the shell instead:

   ```
   curl -X POST localhost:8000/alerts -H 'content-type: application/json' \
     -d '{"service":"checkout-api","message":"5xx rate above 20%","severity_hint":"high","timestamp":"2026-10-22T10:00:00Z"}'
   curl localhost:8000/alerts
   curl localhost:8000/alerts/1
   ```

Tests: `cd backend && pytest` (needs the Postgres container running).

LLM: with no `OPENROUTER_API_KEY` the AI call uses Pydantic AI's `TestModel`, which returns dummy data. Set the key in `.env` (and optionally `OPENROUTER_MODEL`) to use a real free model.

## API

- `POST /alerts` saves an alert and returns it. Same service and message returns the existing alert.
- `GET /alerts` lists alerts with status.
- `GET /alerts/{id}` returns the alert and its triage result (null until triaged).

Status goes received, triaging, triaged. If the AI call fails 3 times the status is failed.

## Design decisions and trade-offs

- Dedupe is a unique constraint on (service, message) plus `get_or_create`, so two concurrent posts cannot create duplicates. The workflow only starts when the alert is new. A long message could hit the btree index size limit; hashing the message would fix that.
- Activities are plain sync functions run in a thread pool, so the Django ORM works without async wrappers.
- Retries live in the Temporal retry policy (3 attempts on the AI activity only). After the last failure the workflow catches the error and runs a `mark_failed` activity.
- The whole AI call is one function, `run_triage` in `alerts/ai.py`. Swapping the model or provider touches only that file.
- Only the service name and team go into the prompt. The alert is not linked to `Service` by foreign key, so alerts from unknown services still work (team is empty).
- Temporal runs as the dev server in Docker (in-memory), so workflow history is lost when the container restarts. Fine for testing.
- The frontend polls every 3 seconds instead of using websockets. Simple, and enough here.
- No auth, no pagination, CORS is open. Test setup only.
- The failed-AI test calls the activities directly and checks the status afterwards. It does not run the workflow, because the Temporal test server needs a separate binary download. The retry and failure path was checked by hand against the real worker using an invalid API key.
- The status passes through received and triaging quickly with the test model, so on the page you will often see it jump to triaged.

## What I'd do next

- SLA timers and escalation with Temporal signals: after triage, the workflow waits for an `acknowledge` signal from the on-call person. If it does not arrive before a timer based on severity (for example 5 minutes for Sev1), the workflow escalates to the next contact. An `acknowledge` or `resolve` signal from the API ends the wait.
- Run the workflow in the Temporal test environment in CI so the retry behaviour is tested, not only the activities.
- Link alerts to services by foreign key and pass recent alerts for the same service to the model as context.
- Pagination and filters on the alert list.
- Proper config per environment, auth, and a persistent Temporal setup.
