import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import DeadlineStatus from "../components/DeadlineStatus";

export default function SubmitProject() {
  const { user } = useAuth();
  const [event, setEvent] = useState(null);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [status, setStatus] = useState(null); // success/error message
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get("/api/events/current")
      .then(setEvent)
      .catch(() => {});
  }, []);

  const isClosed = event && new Date(event.submissions_close) <= new Date();

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus(null);
    setBusy(true);
    try {
      await api.post("/api/projects", { title, summary, repo_url: repoUrl });
      setStatus({ ok: true, message: "Saved as draft. You can keep editing until the deadline." });
    } catch (err) {
      // The backend is the real gate here — the deadline check above is
      // just a courtesy so people aren't surprised by a rejected POST.
      setStatus({ ok: false, message: err.message });
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return (
      <div className="container" style={{ padding: "40px 24px" }}>
        <h1>Submit a project</h1>
        <p>You need to log in as a participant on a team to submit.</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ maxWidth: 560, padding: "40px 24px 64px" }}>
      <h1>Submit a project</h1>
      {event && (
        <div style={{ marginBottom: 20 }}>
          <DeadlineStatus closesAt={event.submissions_close} />
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="title">Title</label>
          <input id="title" required value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="summary">One-line summary</label>
          <textarea
            id="summary"
            required
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="repo">Repository URL</label>
          <input
            id="repo"
            type="url"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
          />
        </div>
        {status && (
          <p className={status.ok ? undefined : "error-text"}>{status.message}</p>
        )}
        <button className="btn" type="submit" disabled={busy || isClosed}>
          {isClosed ? "Submissions closed" : busy ? "Saving..." : "Save draft"}
        </button>
      </form>
    </div>
  );
}
