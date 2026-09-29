import { useEffect, useState } from "react";

export default function CommunityVoting() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [voting, setVoting] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadVotingData() {
    try {
      setLoading(true);
      setError("");

      // Check whether the current user has already voted.
      const statusResponse = await fetch(
        "/api/voting/status",
        {
          credentials: "include",
        }
      );

      const statusData = await statusResponse.json();

      if (!statusResponse.ok) {
        throw new Error(
          statusData.detail ||
          "Unable to check voting status."
        );
      }

      if (!statusData.voting_open) {
        throw new Error(
          "Community voting is not currently open."
        );
      }

      setHasVoted(statusData.has_voted);

      // Don't load the ballot again if the user already voted.
      if (statusData.has_voted) {
        setLoading(false);
        return;
      }

      const response = await fetch(
        "/api/voting/projects",
        {
          credentials: "include",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Unable to load voting projects."
        );
      }

      setProjects(data.projects || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function vote(projectId) {
    try {
      setVoting(true);
      setError("");
      setMessage("");

      const response = await fetch(
        `/api/voting/projects/${projectId}`,
        {
          method: "POST",
          credentials: "include",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Unable to record your vote."
        );
      }

      setHasVoted(true);
      setProjects([]);
      setMessage(
        "Your vote has been recorded successfully."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setVoting(false);
    }
  }

  useEffect(() => {
    loadVotingData();
  }, []);

  if (loading) {
    return (
      <main>
        <h1>Community Voting</h1>
        <p>Loading projects...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main>
        <h1>Community Voting</h1>

        <div>
          <p>{error}</p>
          <button onClick={loadVotingData}>
            Try Again
          </button>
        </div>
      </main>
    );
  }

  if (hasVoted) {
    return (
      <main>
        <h1>Community Voting</h1>

        <section>
          <h2>Thank you for voting!</h2>
          <p>
            Your community vote has already been
            recorded for this event.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main>
      <header>
        <h1>Community Voting</h1>

        <p>
          Review the submitted projects and vote
          for the project you think deserves the
          community vote.
        </p>
      </header>

      {message && (
        <div>
          <p>{message}</p>
        </div>
      )}

      <section>
        {projects.length === 0 ? (
          <p>
            No projects are currently available
            for voting.
          </p>
        ) : (
          projects.map((project) => (
            <article key={project.id}>
              <h2>{project.title}</h2>

              <p>
                {project.summary}
              </p>

              <p>
                Track: {project.track_id}
              </p>

              {project.repo_url && (
                <a
                  href={project.repo_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  View project repository
                </a>
              )}

              <div>
                <button
                  disabled={voting}
                  onClick={() =>
                    vote(project.id)
                  }
                >
                  {voting
                    ? "Submitting..."
                    : "Vote for this project"}
                </button>
              </div>
            </article>
          ))
        )}
      </section>
    </main>
  );
}