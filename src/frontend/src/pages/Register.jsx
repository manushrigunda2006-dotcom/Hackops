import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { refresh } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();

    setError(null);
    setBusy(true);

    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to create account."
        );
      }

      // Registration automatically creates a session.
      await refresh();

      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="container"
      style={{
        maxWidth: 380,
        padding: "56px 24px",
      }}
    >
      <h1>Create account</h1>

      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="name">
            Name
          </label>

          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={(e) =>
              setName(e.target.value)
            }
          />
        </div>

        <div className="field">
          <label htmlFor="email">
            Email
          </label>

          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) =>
              setEmail(e.target.value)
            }
          />
        </div>

        <div className="field">
          <label htmlFor="password">
            Password
          </label>

          <input
            id="password"
            type="password"
            minLength={6}
            required
            value={password}
            onChange={(e) =>
              setPassword(e.target.value)
            }
          />
        </div>

        {error && (
          <p className="error-text">
            {error}
          </p>
        )}

        <button
          className="btn"
          type="submit"
          disabled={busy}
        >
          {busy
            ? "Creating account..."
            : "Create account"}
        </button>
      </form>

      <p style={{ marginTop: 20 }}>
        Already have an account?{" "}
        <Link to="/login">
          Log in
        </Link>
      </p>
    </div>
  );
}