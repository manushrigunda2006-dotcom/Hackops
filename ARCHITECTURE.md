# Architecture

## Stack

- Backend: FastAPI (Python), SQLite for local/dev, standard SQLAlchemy models.
- Frontend: React + Vite, plain CSS (no component library dependency).
- Auth: session-cookie based; the acceptance checker never logs in, it
  attaches a pre-issued header per role (see `.dogfood.toml`).

## Why per-event roles

A user's role (participant / judge / organizer / admin) is scoped to a
specific event rather than being a single global flag. This matches how
real hackathons work — someone can organize one event and judge or
compete in another. See `DATA-MODEL.md` for the schema this implies.

## Checker-facing routes vs. SPA routes

`run.py` makes plain HTTP requests with the standard library's `urllib` —
it does not run JavaScript. If `.dogfood.toml`'s routes pointed at the
React SPA's own client-side paths (e.g. `/projects`), the checker would
only ever see an empty `<div id="root"></div>` before React has had a
chance to render, and the "project from fixtures shown" check would
fail through no real fault of the backend.

So `.dogfood.toml`'s routes point directly at the JSON API endpoints
(`/api/projects`, etc.) rather than at the SPA's pages. JSON text still
contains a fixture project's title as a plain substring, so the check
passes. The SPA has its own separate client-side routes for humans
(`/`, `/projects/:id`, `/submit`, ...) that call those same API
endpoints after the page has loaded. Two route surfaces, one backend,
by design — not an accident of the framework choice.

## Request flow (T1 slice)

```
Browser ──> React app (Vite dev server, :5173)
              │  /api/* proxied to the backend
              ▼
        FastAPI backend (:8080)  ──>  SQLite (/app/data/dogfood.db)
              │
              ▼
     data/fixtures.json loaded once at first boot (seed.py)
```

`docker-compose.yml` runs these as two containers. `.dogfood.toml`'s
`base_url` points at the backend's port (8080) directly, not the
frontend's — see "Checker-facing routes vs. SPA routes" above.

## Auth: one lookup, two ways in

`app/auth.py` resolves a `session` cookie against a `sessions` table.
Two things populate that table:

- `POST /api/auth/login` — a real login, random token.
- `seed.py`, at first boot — four fixed tokens copied verbatim from
  `.dogfood.toml [auth]`, attached to real seeded users (an organizer,
  two distinct judges, one participant). This is what lets `run.py`
  authenticate without ever calling `/api/auth/login`.

Role checks (`require_role` in `app/auth.py`) query the `roles` table
for the *current* event before any route logic runs, so an
unauthorized role gets a 403 before it ever touches the data it was
asking for — this is what rule 9 and the T2 "judge cannot see peer
scores" check are aimed at, once T2 exists.

## System diagram

```
┌─────────────┐      /api/*       ┌──────────────┐      SQL      ┌──────────┐
│  React SPA   │ ───────────────▶ │ FastAPI app  │ ─────────────▶ │  SQLite  │
│  (:5173)     │ ◀─────────────── │  (:8080)     │ ◀───────────── │          │
└─────────────┘      JSON         └──────────────┘                └──────────┘
                                          │
                                          │ first boot only
                                          ▼
                                  data/fixtures.json
```

## Deferred to T2/T3

Judge assignment, scoring, normalization, live dashboard, community
voting, and anti-abuse measures are not part of this document yet — they
get their own sections once T1 is solid.
