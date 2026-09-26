import { Link } from "react-router-dom";
import "./project-card.css";

const TRACK_COLORS = [
  "var(--trk-1)",
  "var(--trk-2)",
  "var(--trk-3)",
  "var(--trk-4)",
  "var(--trk-5)",
  "var(--trk-6)",
  "var(--trk-7)",
  "var(--trk-8)",
];

// Deterministic color per track id so the same track always renders the
// same edge color across the whole gallery, without needing a lookup table.
function colorForTrack(trackId) {
  if (!trackId) return "var(--line)";
  let hash = 0;
  for (let i = 0; i < trackId.length; i++) {
    hash = (hash * 31 + trackId.charCodeAt(i)) % TRACK_COLORS.length;
  }
  return TRACK_COLORS[hash];
}

export default function ProjectCard({ project }) {
  const edgeColor = colorForTrack(project.track_id);

  return (
    <Link
      to={`/projects/${project.id}`}
      className="project-card"
      style={{ borderLeftColor: edgeColor }}
    >
      <div className="project-card-top">
        <h3>{project.title}</h3>
        {project.track_name && (
          <span className="project-card-track" style={{ color: edgeColor }}>
            {project.track_name}
          </span>
        )}
      </div>
      <p className="project-card-summary">{project.summary}</p>
      <div className="project-card-meta">
        <span>{project.team_name}</span>
      </div>
    </Link>
  );
}
