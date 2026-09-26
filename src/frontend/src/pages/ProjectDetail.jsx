import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";

export default function ProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get(`/api/projects/${id}`)
      .then(setProject)
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="container" style={{ padding: "40px 24px" }}>
        <p className="error-text">Couldn't load this project: {error}</p>
        <Link to="/">&larr; Back to gallery</Link>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="container" style={{ padding: "40px 24px" }}>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ padding: "40px 24px 64px", maxWidth: 720 }}>
      <Link to="/">&larr; Back to gallery</Link>
      <h1 style={{ marginTop: 16 }}>{project.title}</h1>
      <p style={{ color: "var(--ink-soft)" }}>
        {project.team_name} · {project.track_name}
      </p>
      <p>{project.summary}</p>
      {project.repo_url && (
        <p>
          <a href={project.repo_url} target="_blank" rel="noreferrer">
            View repository &rarr;
          </a>
        </p>
      )}
    </div>
  );
}
