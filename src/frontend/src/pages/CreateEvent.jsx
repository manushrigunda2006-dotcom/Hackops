import { useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function CreateEvent() {
  const { user } = useAuth();
  const [name, setName] = useState("");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [tracks, setTracks] = useState("");
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus(null);
    setBusy(true);
    try {
      const event = await api.post("/api/events", {
        name,
        submissions_open_at: opensAt,
        submissions_close_at: closesAt,
        tracks: tracks
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setStatus({ ok: true, message: `Created "${event.name}".` });
    } catch (err) {
      setStatus({ ok: false, message: err.message });
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <div className="container" style={{ padding: "40px 24px" }}>
        <h1>Create an event</h1>
        <p>Log in as an organizer to create an event.</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ maxWidth: 520, padding: "40px 24px 64px" }}>
      <h1>Create an event</h1>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="name">Event name</label>
          <input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="opens">Submissions open</label>
          <input
            id="opens"
            type="datetime-local"
            required
            value={opensAt}
            onChange={(e) => setOpensAt(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="closes">Submissions close</label>
          <input
            id="closes"
            type="datetime-local"
            required
            value={closesAt}
            onChange={(e) => setClosesAt(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="tracks">Tracks (comma-separated)</label>
          <input
            id="tracks"
            placeholder="Developer tools, Climate, Health"
            value={tracks}
            onChange={(e) => setTracks(e.target.value)}
          />
        </div>
        {status && (
          <p className={status.ok ? undefined : "error-text"}>{status.message}</p>
        )}
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Creating..." : "Create event"}
        </button>
      </form>
    </div>
  );
}
