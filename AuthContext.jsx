import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../utils/api";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // restore session on load
  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setLoading(false);
      return;
    }

    api.authMe(token)
      .then(res => {
        // Handle both {user} and direct user object responses
        setUser(res.user || res);
      })
      .catch(() => {
        localStorage.removeItem("auth_token");
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const res = await api.login(email, password);
    localStorage.setItem("auth_token", res.token);
    setUser(res.user || res);
  };

  const signup = async (email, password) => {
    const res = await api.signup(email, password);
    localStorage.setItem("auth_token", res.token);
    setUser(res.user || res);
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

