import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./navbar.css";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <Link to="/" className="navbar-brand">
          DOGFOOD<span className="mono navbar-brand-dot">.portal</span>
        </Link>
        <nav className="navbar-links">
          <NavLink to="/" end>
            Gallery
          </NavLink>
          <NavLink to="/submit">Submit project</NavLink>
          <NavLink to="/teams/join">Join a team</NavLink>
          {user ? (
            <>
              <span className="navbar-user">{user.email}</span>
              <button className="btn btn-outline" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <NavLink to="/login" className="btn btn-outline">
              Log in
            </NavLink>
          )}
        </nav>
      </div>
    </header>
  );
}
