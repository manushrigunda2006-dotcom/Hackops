import "./deadline-status.css";

// Renders the single fact that matters most during a live event: is
// submission still open. Deliberately the loudest element on the page —
// everything else stays quiet by comparison.
export default function DeadlineStatus({ closesAt }) {
  if (!closesAt) return null;
  const closeDate = new Date(closesAt);
  const isOpen = closeDate.getTime() > Date.now();

  return (
    <div className={`deadline-status ${isOpen ? "is-open" : "is-closed"}`}>
      <span className="deadline-dot" />
      <span>
        {isOpen ? "Submissions open" : "Submissions closed"} —{" "}
        {isOpen ? "closes " : "closed "}
        {closeDate.toLocaleString(undefined, {
          dateStyle: "medium",
          timeStyle: "short",
        })}
      </span>
    </div>
  );
}
