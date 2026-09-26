# Data Model

## Entities (T1 slice)

**User**
`id, email, password_hash, name, created_at`
Global identity. Role is NOT stored here — see Role below.

**Role** (user × event × role)
`id, user_id, event_id, role`
`role` is one of `participant | judge | organizer | admin`.
Decision: roles are scoped per-event, not global, so one person can be
an organizer of their own event and a participant/judge in someone
else's. Open question we're still deciding: whether `admin` should stay
per-event or become a single platform-wide `is_admin` flag on `User`
instead — the spec requires the role to exist but never defines what
admin actually does, since `run.py` doesn't test it.

**Event**
`id, name, description, submissions_open_at, submissions_close_at, created_by, created_at`

**Track**
`id, event_id, name`

**Prize**
`id, event_id, name, description, rank_or_category`

**Team**
`id, event_id, name, invite_token, created_at`

**TeamMember**
`team_id, user_id, joined_at`

**Project**
`id, team_id, track_id, title, summary, repo_url, status, submitted_at, updated_at`
`status` is `draft | submitted`. Edits are allowed in either status as
long as `now() < event.submissions_close_at`; the backend rejects any
write after that regardless of what the UI shows.

**ProjectRevision** (optional, cheap insurance for later audit-trail needs)
`id, project_id, snapshot_json, edited_at`

**Session**
`token, user_id, created_at`
Not in the original slice above — added once auth was implemented.
Holds both real login sessions (random token) and the acceptance
checker's four fixed tokens from `.dogfood.toml [auth]`, seeded at
first boot. See `ARCHITECTURE.md` "Auth: one lookup, two ways in".

## fixtures.json mapping

- `event` → one `Event` row
- `tracks[]` → `Track` rows
- `judges[]` → `User` + `Role(role='judge')` rows, scoped to this event
- `teams[].members` (emails) → `User` + `TeamMember` rows
- `projects[]` → `Project` rows (`status='submitted'`)
- `scores[]` → ignored for T1; consumed starting at T2

## Import / export paths

TBD — will document CSV export format here once T2 lands.
