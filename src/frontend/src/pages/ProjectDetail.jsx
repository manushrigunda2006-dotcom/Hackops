import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function ProjectDetail() {
  const { id } = useParams();
  const { user } = useAuth();

  const [project, setProject] = useState(null);
  const [comments, setComments] = useState([]);

  const [commentText, setCommentText] = useState("");
  const [commenting, setCommenting] = useState(false);

  const [error, setError] = useState(null);
  const [commentError, setCommentError] = useState(null);

  useEffect(() => {
    api
      .get(`/api/projects/${id}`)
      .then(setProject)
      .catch((e) => setError(e.message));

    api
      .get(`/api/comments/projects/${id}`)
      .then((data) => {
        setComments(data.comments || []);
      })
      .catch((e) => {
        setCommentError(e.message);
      });
  }, [id]);

  async function submitComment(e) {
    e.preventDefault();

    const content = commentText.trim();

    if (!content) {
      return;
    }

    try {
      setCommenting(true);
      setCommentError(null);

      const newComment = await api.post(
        `/api/comments/projects/${id}`,
        {
          content,
        }
      );

      setComments((current) => [
        ...current,
        newComment,
      ]);

      setCommentText("");
    } catch (e) {
      setCommentError(e.message);
    } finally {
      setCommenting(false);
    }
  }

  if (error) {
    return (
      <div
        className="container"
        style={{ padding: "40px 24px" }}
      >
        <p className="error-text">
          Couldn't load this project: {error}
        </p>

        <Link to="/">
          &larr; Back to gallery
        </Link>
      </div>
    );
  }

  if (!project) {
    return (
      <div
        className="container"
        style={{ padding: "40px 24px" }}
      >
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div
      className="container"
      style={{
        padding: "40px 24px 64px",
        maxWidth: 720,
      }}
    >
      <Link to="/">
        &larr; Back to gallery
      </Link>

      <h1 style={{ marginTop: 16 }}>
        {project.title}
      </h1>

      <p style={{ color: "var(--ink-soft)" }}>
        {project.team_name} · {project.track_name}
      </p>

      <p>{project.summary}</p>

      {project.repo_url && (
        <p>
          <a
            href={project.repo_url}
            target="_blank"
            rel="noreferrer"
          >
            View repository &rarr;
          </a>
        </p>
      )}

      <hr
        style={{
          margin: "40px 0",
          border: 0,
          borderTop: "1px solid var(--line)",
        }}
      />

      <section>
        <h2>Community comments</h2>

        {comments.length === 0 ? (
          <p style={{ color: "var(--ink-soft)" }}>
            No comments yet. Be the first to comment.
          </p>
        ) : (
          <div>
            {comments.map((comment) => (
              <article
                key={comment.id}
                style={{
                  padding: "16px 0",
                  borderBottom:
                    "1px solid var(--line)",
                }}
              >
                <strong>
                  {comment.user_name}
                </strong>

                <p
                  style={{
                    marginTop: 6,
                    marginBottom: 4,
                  }}
                >
                  {comment.content}
                </p>

                <small
                  style={{
                    color: "var(--ink-soft)",
                  }}
                >
                  {new Date(
                    comment.created_at
                  ).toLocaleString()}
                </small>
              </article>
            ))}
          </div>
        )}

        {user ? (
          <form
            onSubmit={submitComment}
            style={{ marginTop: 28 }}
          >
            <div className="field">
              <label htmlFor="comment">
                Add a comment
              </label>

              <textarea
                id="comment"
                value={commentText}
                onChange={(e) =>
                  setCommentText(
                    e.target.value
                  )
                }
                maxLength={2000}
                placeholder="Share your thoughts about this project..."
                rows={4}
              />
            </div>

            {commentError && (
              <p className="error-text">
                {commentError}
              </p>
            )}

            <button
              className="btn"
              type="submit"
              disabled={
                commenting ||
                !commentText.trim()
              }
            >
              {commenting
                ? "Posting..."
                : "Post comment"}
            </button>
          </form>
        ) : (
          <p style={{ marginTop: 28 }}>
            <Link to="/login">
              Log in
            </Link>{" "}
            to leave a comment.
          </p>
        )}
      </section>
    </div>
  );
}