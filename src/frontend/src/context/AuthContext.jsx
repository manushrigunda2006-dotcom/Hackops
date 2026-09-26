import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // { email, roles: [{event_id, role}] }
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      const me = await api.get("/api/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function login(email, password) {
    await api.post("/api/auth/login", { email, password });
    await refresh();
  }

  async function logout() {
    await api.post("/api/auth/logout");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

// Convenience: does the user hold `role` for this specific event?
// This is purely a UI convenience for showing/hiding nav links — the
// backend is the actual enforcement boundary, not this check.
export function hasRole(user, eventId, role) {
  if (!user || !user.roles) return false;
  return user.roles.some((r) => r.event_id === eventId && r.role === role);
}
