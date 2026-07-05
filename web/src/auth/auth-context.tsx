import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, getErrorMessage } from "../api/client";
import { getCurrentUser, logoutUser } from "../api/auth";
import type { User } from "../api/types";

type AuthContextValue = {
  authReady: boolean;
  authError: string | null;
  currentUser: User | null;
  refreshAuth: () => Promise<void>;
  setAuthenticatedUser: (user: User | null) => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authReady, setAuthReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const setAuthenticatedUser = useCallback((user: User | null) => {
    setCurrentUser(user);
    setAuthReady(true);
    setAuthError(null);
  }, []);

  const refreshAuth = useCallback(async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
      setAuthError(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setCurrentUser(null);
        setAuthError(null);
      } else {
        setCurrentUser(null);
        setAuthError(getErrorMessage(error));
      }
    } finally {
      setAuthReady(true);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 401)) {
        setAuthError(getErrorMessage(error));
        throw error;
      }
    } finally {
      setCurrentUser(null);
      setAuthReady(true);
    }
  }, []);

  useEffect(() => {
    void refreshAuth();
  }, [refreshAuth]);

  const value = useMemo<AuthContextValue>(
    () => ({
      authReady,
      authError,
      currentUser,
      refreshAuth,
      setAuthenticatedUser,
      logout,
    }),
    [authReady, authError, currentUser, logout, refreshAuth, setAuthenticatedUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
