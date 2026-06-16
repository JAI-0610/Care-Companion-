import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Set Authorization header for all backend requests
  const setAuthHeader = (token) => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('health_insight_token');
      const userData = localStorage.getItem('health_insight_user');
      
      if (token && userData) {
        setAuthHeader(token);
        setUser(JSON.parse(userData));
        
        // Confirm token validation with the backend
        try {
          const res = await axios.get('/api/auth/me');
          const verifiedUser = res.data;
          const names = (verifiedUser.full_name || '').split(' ');
          const mappedUser = {
            id: verifiedUser.user_id,
            email: verifiedUser.email,
            firstName: names[0] || '',
            lastName: names.slice(1).join(' ') || '',
            full_name: verifiedUser.full_name,
            onboarded: verifiedUser.onboarded
          };
          setUser(mappedUser);
          localStorage.setItem('health_insight_user', JSON.stringify(mappedUser));
        } catch (error) {
          console.error("Token verification failed, logging out", error);
          logout();
        }
      }
      setLoading(false);
    };
    
    initAuth();
  }, []);

  const login = async (email, password) => {
    try {
      const res = await axios.post('/api/auth/login', { email, password });
      const { token, user: backendUser } = res.data;
      
      const names = (backendUser.full_name || '').split(' ');
      const mappedUser = {
        id: backendUser.user_id,
        email: backendUser.email,
        firstName: names[0] || '',
        lastName: names.slice(1).join(' ') || '',
        full_name: backendUser.full_name,
        onboarded: backendUser.onboarded
      };
      
      setAuthHeader(token);
      setUser(mappedUser);
      localStorage.setItem('health_insight_token', token);
      localStorage.setItem('health_insight_user', JSON.stringify(mappedUser));
      return { success: true };
    } catch (error) {
      const msg = error.response?.data?.detail || error.message || 'Login failed';
      return { success: false, error: msg };
    }
  };

  const register = async (userData) => {
    try {
      const signupData = {
        email: userData.email,
        password: userData.password,
        full_name: `${userData.firstName} ${userData.lastName}`
      };
      
      const res = await axios.post('/api/auth/signup', signupData);
      const { token, user: backendUser } = res.data;
      
      const names = (backendUser.full_name || '').split(' ');
      const mappedUser = {
        id: backendUser.user_id,
        email: backendUser.email,
        firstName: names[0] || '',
        lastName: names.slice(1).join(' ') || '',
        full_name: backendUser.full_name,
        onboarded: backendUser.onboarded
      };
      
      setAuthHeader(token);
      setUser(mappedUser);
      localStorage.setItem('health_insight_token', token);
      localStorage.setItem('health_insight_user', JSON.stringify(mappedUser));
      
      // Update custom profile data on the backend (e.g. date of birth)
      try {
        await axios.patch('/api/profile/me', { date_of_birth: userData.dateOfBirth });
      } catch (err) {
        console.error("Failed to save profile DOB details", err);
      }
      
      return { success: true };
    } catch (error) {
      const msg = error.response?.data?.detail || error.message || 'Registration failed';
      return { success: false, error: msg };
    }
  };

  const logout = () => {
    setUser(null);
    setAuthHeader(null);
    localStorage.removeItem('health_insight_token');
    localStorage.removeItem('health_insight_user');
    axios.post('/api/auth/logout').catch(() => {});
  };

  const value = {
    user,
    login,
    register,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};