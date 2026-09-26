import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import ProjectCard from "../components/ProjectCard";
import DeadlineStatus from "../components/DeadlineStatus";
import "./gallery.css";

export default function Gallery() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [trackFilter, setTrackFilter] = useState("all");

  useEffect(() => {
    api
      .get("/api/projects")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const tracks = useMemo(() => {
    if (!data) return [];
    const seen = new Map();
    for (const p of data.projects) {
      if (p.track_id && !seen.has(p.track_id)) {
        seen.set(p.track_id, p.track_name);
      }
    }
    return [...seen.entries()];
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.projects.filter((p) => {
      const matchesQuery =
        !query ||
        p.title.toLowerCase().includes(query.toLowerCase()) ||
        p.summary.toLowerCase().includes(query.toLowerCase()) ||
        p.team_name.toLowerCase().includes(query.toLowerCase());
      const matchesTrack =
        trackFilter === "all" || p.track_id === trackFilter;
      return matchesQuery && matchesTrack;
    });
  }, [data, query, trackFilter]);

  if (error) {
    return (
      <div className="container gallery-page">
        <p className="error-text">Couldn't load the gallery: {error}</p>
      </div>
    );
  }

  return (
    <div className="container gallery-page">
      <div className="gallery-header">
        <div>
          <h1>Project gallery</h1>
          <p>Browse everything submitted so far. No account needed.</p>
        </div>
        {data?.event && <DeadlineStatus closesAt={data.event.submissions_close} />}
      </div>

      <div className="gallery-controls">
        <input
          type="search"
          placeholder="Search title, summary, or team..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search projects"
        />
        <select
          value={trackFilter}
          onChange={(e) => setTrackFilter(e.target.value)}
          aria-label="Filter by track"
        >
          <option value="all">All tracks</option>
          {tracks.map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {!data ? (
        <p>Loading...</p>
      ) : filtered.length === 0 ? (
        <p>No projects match that search.</p>
      ) : (
        <div className="gallery-grid">
          {filtered.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}
