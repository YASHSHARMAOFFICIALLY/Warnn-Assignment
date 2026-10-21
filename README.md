# alert-triage

Paste an alert as JSON. The API saves it, a Temporal workflow asks an LLM for a probable cause, confidence, severity and action items, and a React page shows the result.

Django + Django Ninja, Temporal, Pydantic AI, Postgres, React + Vite.

## Flow

1. `POST /alerts` validates and saves the alert as `received`. Same service + message as an existing alert returns that alert, no new workflow.
2. The API starts workflow `triage-<id>` and returns.
3. The worker marks it `triaging`, looks up the service's team, makes one LLM call (3 attempts), saves the result, marks it `triaged`. If all 3 attempts fail it is marked `failed`.

## Run

Needs Docker, Python 3.12+, Node 20+.

```
cp .env.example .env
docker compose up -d

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver 8000     # terminal 1
python worker.py                    # terminal 2, same venv

cd frontend
cp .env.example .env
npm install
npm run dev                         # terminal 3
```

UI at http://localhost:5173, Temporal UI at http://localhost:8233. Tests: `cd backend && pytest` (Postgres must be up).

```
curl -X POST localhost:8000/alerts -H 'content-type: application/json' \
  -d '{"service":"checkout-api","message":"5xx rate above 20%","severity_hint":"high","timestamp":"2026-10-22T10:00:00Z"}'
```

With no `OPENROUTER_API_KEY`, `ai.py` uses a local stand-in (a Pydantic AI `FunctionModel`) that matches keywords like "5xx" or "timeout" and returns canned triages. It is for running the flow offline, not real analysis. Set the key (and optionally `OPENROUTER_MODEL`) in `.env` to use a real model.

## API

- `POST /alerts`: `service`, `message`, optional `severity_hint`, `timestamp`. 422 on bad input. 503 if Temporal is unreachable (the alert is not kept, so retry is safe).
- `GET /alerts`: newest first, with status, severity and received time.
- `GET /alerts/{id}`: the alert and its triage result (`null` until triaged), or 404.

## Decisions

- **Temporal for retries.** The LLM call is what fails. Temporal lets the API return immediately, the worker retry the call, and a crashed worker resume instead of leaving an alert stuck in `triaging`. Cost: a Temporal server and a worker for a small flow.
- **Dedupe on service + message.** A unique constraint with `get_or_create`, so concurrent duplicates can't create two rows. Downside: the same message a week later is also a duplicate.
- **One LLM call, structured output.** `run_triage` in `ai.py` returns a `Triage` model (confidence 0 to 1, severity Sev1 to Sev4). A bad answer counts as a failed attempt and is retried rather than saved.
- `Alert.service` is a plain string, so alerts from unknown services are still triaged, with the team shown as unknown.
- Only the LLM activity has a 3-attempt limit; the DB activities use Temporal's default retry.
- The UI polls every 3 seconds.

## Limits

- No auth, open CORS, `DEBUG` on. Local use only.
- Temporal runs as the in-memory dev server; history is lost on restart.
- A new Temporal connection per `POST /alerts`. No pagination on `GET /alerts`. A very long message can break the unique index.
- Tests call activities directly, not the workflow (the Temporal test server is a separate download). The retries and `failed` status were checked by hand with a bad API key.
- A real OpenRouter call with a valid key is untested; free models may not follow the structured format.

## Next

- Escalation: after triage, wait for an `acknowledge` signal; if none arrives within a severity-based timer, escalate.
- Run the workflow in Temporal's test environment in CI.
- Foreign key from alerts to services, and recent alerts as model context.
- Pagination, status filter, auth, persistent Temporal.
