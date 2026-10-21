# alert-triage

You paste a raw alert as JSON. The backend saves it and a Temporal workflow triages it: it finds the team that owns the service, asks an LLM for a probable cause, confidence, severity and action items, and saves the result. A small React page shows the alerts and their results.

Stack: Django + Django Ninja, Temporal (Python SDK), Pydantic AI, PostgreSQL, React + Vite.

## What happens to one alert

1. `POST /alerts` validates the JSON and saves it with status `received`. If the same service and message already exist, it returns that alert and stops.
2. For a new alert the API starts a Temporal workflow (`triage-<id>`) and returns right away.
3. A worker picks up the workflow: status becomes `triaging`, then it looks up the service and its team in Postgres.
4. One LLM call returns a structured triage. If it fails it is retried, 3 attempts in total.
5. The result is saved and status becomes `triaged`. If all 3 attempts fail the status becomes `failed`.

## Where is what

- `docker-compose.yml`: Postgres and Temporal containers.
- `.env.example`: all environment variables, copy to `.env`.
- `backend/manage.py`: Django entry point (migrate, seed, runserver).
- `backend/worker.py`: starts the Temporal worker.
- `backend/alert_triage/settings.py`: Django settings (database, Temporal address, task queue).
- `backend/alert_triage/urls.py`: mounts the API.
- `backend/alerts/models.py`: Team, Service, Alert, TriageResult.
- `backend/alerts/api.py`: the three routes, `POST /alerts`, `GET /alerts`, `GET /alerts/{id}`.
- `backend/alerts/start_workflow.py`: starts the Temporal workflow for a new alert.
- `backend/alerts/workflow.py`: the workflow, which runs the activities in order and handles the retries.
- `backend/alerts/activities.py`: the steps: mark triaging, look up team, call the LLM, save result, mark triaged, mark failed.
- `backend/alerts/ai.py`: the one Pydantic AI call (test model without a key, OpenRouter with one).
- `backend/alerts/management/commands/seed.py`: creates 2 teams and 3 services.
- `backend/alerts/test_alerts.py`: the pytest tests.
- `frontend/src/App.jsx`: page layout and the 3 second refresh of the list.
- `frontend/src/AlertForm.jsx`: JSON textarea and Submit button.
- `frontend/src/AlertList.jsx`: the alert table.
- `frontend/src/AlertDetail.jsx`: probable cause, confidence, severity, action items.
- `frontend/src/api.js`: fetch calls to the backend, URL from `VITE_API_URL`.
- `frontend/src/style.css`: all styles.

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

5. Or try it from the shell:

   ```
   curl -X POST localhost:8000/alerts -H 'content-type: application/json' \
     -d '{"service":"checkout-api","message":"5xx rate above 20%","severity_hint":"high","timestamp":"2026-10-22T10:00:00Z"}'
   curl localhost:8000/alerts
   curl localhost:8000/alerts/1
   ```

Tests: `cd backend && pytest` (needs the Postgres container running).

LLM: with no `OPENROUTER_API_KEY` the call uses Pydantic AI's `TestModel`, which returns dummy data (cause "a", confidence 0). Put a key in `.env`, and optionally `OPENROUTER_MODEL`, to use a real free model.

## API

- `POST /alerts` takes `service`, `message`, optional `severity_hint` and `timestamp`. Returns the alert. Bad input gives 422. If the workflow service is down it gives 503 and the alert is not kept, so the caller can just retry.
- `GET /alerts` lists alerts with their status, newest first.
- `GET /alerts/{id}` returns the alert and its triage result (`null` until triaged), or 404.

## Design decisions and trade-offs

**Why Temporal for the retries.** The LLM call is the part that fails: rate limits, timeouts, bad output. I did not want a retry loop inside a request handler, and I did not want a request to wait for the model. With Temporal the API returns right away, the worker does the slow part, and the retry policy (3 attempts, one line in `workflow.py`) is not code I have to write or test. If the worker dies halfway, Temporal continues the workflow when it comes back instead of leaving the alert stuck in `triaging`. The cost is two more moving parts (a Temporal server and a worker process) for a very small flow.

**Why dedupe on service plus message.** Monitoring tools often send the same alert again and again. The same service with the same message is the same problem, so I return the existing alert and do not start a second workflow. It is a unique constraint in the database plus `get_or_create`, so two requests arriving at the same moment still cannot create two rows. The downside is that the same message sent a week later is also treated as a duplicate. A time window or a fingerprint field would fix that, but the brief did not ask for it.

**Why one AI call.** One call with one structured answer is easy to retry, easy to test and easy to swap. All of it lives in one function, `run_triage` in `ai.py`, so changing the model, the prompt or the provider touches one file. Splitting it into several calls (cause, then severity, then actions) would add more places to fail and more cost with no clear gain at this size.

**Why structured output.** The result goes into database columns and a UI, so it must have a known shape. Pydantic AI makes the model return the `Triage` class: confidence has to be between 0 and 1 and severity has to be one of Sev1 to Sev4. If the model answers with something that does not fit, that counts as a failed attempt and gets retried, instead of saving bad data.

**Other choices.**
- Only the AI activity has a retry limit. The database activities use Temporal's default retry, which is fine for short database calls.
- Activities are plain sync functions run in a thread pool, so the Django ORM works without async wrappers.
- `Alert.service` is a plain string, not a foreign key to `Service`. Alerts from unknown services are still accepted and triaged with the team marked unknown.
- `save_result` uses `update_or_create`, so a retried activity does not fail on the one-to-one.
- The frontend polls every 3 seconds. Simple, and enough here.

## Known limits

- No auth, open CORS, `DEBUG` on. This is for local testing only.
- The Temporal container is the in-memory dev server. Workflow history is lost when it restarts.
- A new Temporal connection is opened for every `POST /alerts`. Fine here, a shared client would be better under load.
- A very long alert message can break the unique index in Postgres.
- No pagination on `GET /alerts`.
- With the test model the status moves through `triaging` too fast to see in the UI.
- The tests call the activities directly. They do not run the workflow itself, because the Temporal test server needs a separate download. I checked the 3 retries and the `failed` status by hand with an invalid API key.
- A real OpenRouter call with a valid key is not tested. Free models may not always follow the structured format.

## What I'd do next

- SLA timers and escalation with Temporal signals: after triage the workflow waits for an `acknowledge` signal from the on-call person. If it does not arrive before a timer based on severity (for example 5 minutes for Sev1), the workflow escalates to the next contact. An API call sends the signal and ends the wait.
- Run the workflow in the Temporal test environment in CI so the retry behaviour is tested, not only the activities.
- Link alerts to services with a foreign key and give the model recent alerts of the same service as context.
- Pagination and a status filter on the alert list.
- Per-environment config, auth, and a persistent Temporal setup.
