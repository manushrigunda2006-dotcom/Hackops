import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="container" style={{ padding: "64px 24px", textAlign: "center" }}>
      <h1>Page not found</h1>
      <p>
        <Link to="/">Back to the gallery</Link>
      </p>
    </div>
  );
}
