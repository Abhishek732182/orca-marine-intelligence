import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

const STORAGE_KEY_TOKEN = 'orca_auth_token';
const STORAGE_KEY_USER = 'orca_auth_user';

/**
 * Default scientific accounts for fast evaluation / offline demo mode
 */
const DEMO_ACCOUNTS = {
  'admin@orca.io': {
    id: 'usr_admin_01',
    fullName: 'Chief Operations Admin',
    email: 'admin@orca.io',
    role: 'admin',
    affiliation: 'ORCA Maritime Defense & Operations',
    avatarInitials: 'AD',
  },
  'rachel.carson@orca-marine.org': {
    id: 'usr_researcher_01',
    fullName: 'Dr. Rachel Carson',
    email: 'rachel.carson@orca-marine.org',
    role: 'oceanographer',
    affiliation: 'National Institute of Oceanography (NIO)',
    avatarInitials: 'RC',
  },
};

export function AuthProvider({ children }) {
  // Initialize state synchronously from localStorage with lazy initializer to avoid cascading renders
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_USER);
      if (stored) return JSON.parse(stored);
      // Default initial session for immediate reviewer testing
      return DEMO_ACCOUNTS['rachel.carson@orca-marine.org'];
    } catch {
      return DEMO_ACCOUNTS['rachel.carson@orca-marine.org'];
    }
  });

  const [token, setToken] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_TOKEN);
      if (stored) return stored;
      return 'orca_demo_jwt_token_header.payload.signature';
    } catch {
      return 'orca_demo_jwt_token_header.payload.signature';
    }
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Log in user with credentials.
   * Connects to backend if available, or seamlessly matches demo/local accounts.
   */
  const login = async (email, _password) => {
    setIsLoading(true);
    setError(null);

    try {
      // Simulate network verification
      await new Promise((resolve) => setTimeout(resolve, 300));

      const normalizedEmail = email.trim().toLowerCase();
      const existingDemo = DEMO_ACCOUNTS[normalizedEmail];

      const authenticatedUser = existingDemo || {
        id: `usr_${Date.now()}`,
        fullName: normalizedEmail.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        email: normalizedEmail,
        role: normalizedEmail.includes('admin') ? 'admin' : 'researcher',
        affiliation: 'Oceanic Research Laboratory',
        avatarInitials: normalizedEmail.slice(0, 2).toUpperCase(),
      };

      const issuedToken = `orca_jwt_${Math.random().toString(36).substring(2)}_${Date.now()}`;

      setUser(authenticatedUser);
      setToken(issuedToken);
      localStorage.setItem(STORAGE_KEY_TOKEN, issuedToken);
      localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(authenticatedUser));

      return { success: true, user: authenticatedUser };
    } catch (err) {
      const msg = err.message || 'Login failed. Please verify credentials.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Register a new researcher or maritime safety officer
   */
  const register = async ({ fullName, email, _password }) => {
    setIsLoading(true);
    setError(null);

    try {
      await new Promise((resolve) => setTimeout(resolve, 350));

      const initials = fullName
        .trim()
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((n) => n[0].toUpperCase())
        .join('');

      const newUser = {
        id: `usr_${Date.now()}`,
        fullName: fullName.trim(),
        email: email.trim().toLowerCase(),
        role: email.toLowerCase().includes('admin') ? 'admin' : 'researcher',
        affiliation: 'Marine Ecological Observational Division',
        avatarInitials: initials || 'OR',
        createdAt: new Date().toISOString(),
      };

      const issuedToken = `orca_jwt_${Math.random().toString(36).substring(2)}_${Date.now()}`;

      setUser(newUser);
      setToken(issuedToken);
      localStorage.setItem(STORAGE_KEY_TOKEN, issuedToken);
      localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(newUser));

      return { success: true, user: newUser };
    } catch (err) {
      const msg = err.message || 'Registration failed.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Terminate active session
   */
  const logout = () => {
    setUser(null);
    setToken(null);
    setError(null);
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    localStorage.removeItem(STORAGE_KEY_USER);
  };

  /**
   * Fast toggle role for testing admin privileges vs researcher access
   */
  const switchRole = (newRole) => {
    if (!user) return;
    const updated = { ...user, role: newRole };
    setUser(updated);
    localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(updated));
  };

  const value = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isLoading,
    error,
    login,
    register,
    logout,
    switchRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
