import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

// Handles two cases: /teams/join (paste a link/token) and
// /teams/join/:token (arrived via a shared invite link directly).
export default function TeamJoin() {
  const { token: tokenFromUrl } = useParams();
  const { user } = useAuth();
  const [token, setToken] = useState(tokenFromUrl || "");
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus(null);
    setBusy(true);
    try {
      const team = await api.post("/api/teams/join", { invite_token: token });
      setStatus({ ok: true, message: `Joined ${team.name}.` });
    } catch (err) {
      setStatus({ ok: false, message: err.message });
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <div className="container" style={{ padding: "40px 24px" }}>
        <h1>Join a team</h1>
        <p>Log in first, then come back to this link to join.</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ maxWidth: 460, padding: "40px 24px 64px" }}>
      <h1>Join a team</h1>
      <p>Paste the invite link or code a teammate sent you.</p>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="token">Invite code</label>
          <input
            id="token"
            required
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </div>
        {status && (
          <p className={status.ok ? undefined : "error-text"}>{status.message}</p>
        )}
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Joining..." : "Join team"}
        </button>
      </form>
    </div>
  );
}
