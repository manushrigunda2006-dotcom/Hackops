# DOGFOOD Portal

One-sentence pitch: TBD once T1 is working end to end.

One-sentence pitch: A hackathon submission and judging portal with
backend-enforced roles from day one.

## Status

**T1 claimed.** T2 (judging) is not started — `judge_scores`, `peer_scores`
and `csv_export` in `.dogfood.toml` currently 404. See `acceptance-report.txt`
for what `run.py` actually verified (generate it yourself with the command
below; we don't hand-write or fake that file).

## Running it

```
docker compose up
```

- Backend + seeded API: `http://localhost:8080` (this is what `.dogfood.toml`
  and `run.py` talk to)
- Human-facing SPA: `http://localhost:5173`

No external services, no cloud accounts, nothing to install beyond Docker.
The backend seeds itself from `data/fixtures.json` on first boot.

To log in as a human through the UI, any fixture email (e.g. an email from
`data/fixtures.json`'s `judges[]` or `teams[].members`) works with the demo
password `dogfood`.

To run the acceptance checker:

```
python3 run.py .dogfood.toml > acceptance-report.txt
```

## What's built so far

- [x] Auth / role model (session cookies; same lookup path serves real
      logins and the checker's pre-issued header tokens)
- [x] Event creation (any logged-in user creates an event and becomes its
      organizer)
- [x] Team formation via invite link (`POST /api/teams/join`)
- [x] Project submission + edit until deadline (`POST` / `PATCH /api/projects`)
- [x] Deadline enforcement, backend-checked (`403` after
      `submissions_close_at`, independent of what the UI's disabled button
      shows)
- [x] Public gallery with search/filter (search + track filter run
      client-side over `GET /api/projects`; both are read-only conveniences,
      not something the backend needs to enforce)
- [ ] T2: judge assignment, weighted rubric, role-isolated scores,
      normalization, CSV export — not started

## Known limitations

- No prizes UI yet — the `Prize` model/table exists per `DATA-MODEL.md` but
  there's no route to create or read them.
- Draft vs. submitted status: the schema supports `draft`, but the current
  submit form always creates a project as `submitted` directly. There's no
  separate "save as draft, then submit" step yet.
- The SPA only ever operates against the single most-recently-created
  event (`GET /api/events/current`). Creating a second event switches the
  whole gallery/submit flow to it rather than letting a user pick which
  event they're viewing.
- No image/asset uploads — `repo_url` is a plain link field.
- `admin` role exists in the schema (per `DATA-MODEL.md`) but nothing reads
  or grants it yet; the spec doesn't define what admin should do and
  `run.py` doesn't test it.
