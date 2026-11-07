import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import api from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('trustvault_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('trustvault_token'));
  const [loading, setLoading] = useState(true);

  const refreshProfile = async () => {
    if (!localStorage.getItem('trustvault_token')) {
      setLoading(false);
      return;
    }
    try {
      const res = await api.get<User>('/auth/me');
      setUser(res.data);
      localStorage.setItem('trustvault_user', JSON.stringify(res.data));
    } catch {
      setUser(null);
      setToken(null);
      localStorage.removeItem('trustvault_token');
      localStorage.removeItem('trustvault_user');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshProfile();
  }, []);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('trustvault_token', newToken);
    localStorage.setItem('trustvault_user', JSON.stringify(newUser));
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Ignore network errors on logout
    } finally {
      setToken(null);
      setUser(null);
      localStorage.removeItem('trustvault_token');
      localStorage.removeItem('trustvault_user');
      window.location.href = '/login';
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, refreshProfile }}>
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
