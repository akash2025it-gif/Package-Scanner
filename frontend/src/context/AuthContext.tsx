import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
  isAdmin: boolean;
  isInspector: boolean;
  canScan: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const stored = localStorage.getItem('packcheck_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('packcheck_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  // Validate and restore initial session on application boot/refresh
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      const storedToken = localStorage.getItem('packcheck_token');
      const storedUser = localStorage.getItem('packcheck_user');

      if (storedToken) {
        // Synchronously ensure user is restored from local storage if available
        if (storedUser && isMounted) {
          try {
            setUser(JSON.parse(storedUser));
          } catch {
            // ignore parse failure
          }
        }

        // Validate token with backend /auth/me
        try {
          const freshUser = await api.getCurrentUser();
          if (isMounted) {
            setUser(freshUser);
            localStorage.setItem('packcheck_user', JSON.stringify(freshUser));
          }
        } catch (err) {
          console.warn('Session verification notice:', err);
        }
      }

      if (isMounted) {
        setIsLoading(false);
      }
    };

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []); // Run once on initial application mount

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await api.login(email, password);
      // Synchronously store credentials before state updates to prevent race conditions
      localStorage.setItem('packcheck_token', data.access_token);
      localStorage.setItem('packcheck_user', JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('packcheck_token');
    localStorage.removeItem('packcheck_user');
  };

  const hasRole = (roles: UserRole | UserRole[]): boolean => {
    if (!user) return false;
    const allowed = Array.isArray(roles) ? roles : [roles];
    return allowed.includes(user.role);
  };

  const isAdmin = user?.role === 'admin';
  const isInspector = user?.role === 'inspector';
  const canScan = isAdmin || isInspector;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        hasRole,
        isAdmin,
        isInspector,
        canScan,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
