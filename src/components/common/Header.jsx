import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Menu, X, User, LogOut } from 'lucide-react';
import './Header.css';

const Header = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navigation = [
    { name: 'Home', path: '/' },
    { name: 'Chat', path: '/chat' },
    { name: 'Medications', path: '/medications' },
    { name: 'About', path: '/about' },
    { name: 'Disclaimer', path: '/disclaimer' }
  ];

  const handleLogout = () => {
    logout();
    setIsMobileMenuOpen(false);
  };

  // Custom Logo SVG
  const CareCompanionLogo = () => (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="logo-icon"
    >
      {/* Background Circle */}
      <circle cx="16" cy="16" r="14" fill="#2563eb" fillOpacity="0.1" />
      
      {/* Medical Cross */}
      <rect x="14" y="8" width="4" height="16" rx="2" fill="#2563eb" />
      <rect x="8" y="14" width="16" height="4" rx="2" fill="#2563eb" />
      
      {/* AI/Circuit Elements */}
      <circle cx="22" cy="10" r="1.5" fill="#2563eb" />
      <circle cx="10" cy="22" r="1" fill="#2563eb" />
      <circle cx="22" cy="22" r="1" fill="#2563eb" />
    </svg>
  );

  return (
    <header className="header">
      <div className="header-container">
        <Link to="/" className="logo">
          <CareCompanionLogo />
          <span>Care Companion</span>
        </Link>

        <nav className={`nav ${isMobileMenuOpen ? 'nav-open' : ''}`}>
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.path}
              className={`nav-link ${
                location.pathname === item.path ? 'nav-link-active' : ''
              }`}
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {item.name}
            </Link>
          ))}
        </nav>

        <div className="header-actions">
          {user ? (
            <div className="user-menu">
              <Link to="/profile" className="user-info">
                <User size={18} />
                <span>{user.firstName}</span>
              </Link>
              <button onClick={handleLogout} className="logout-btn">
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <div className="auth-links">
              <Link to="/login" className="auth-link">Login</Link>
              <Link to="/register" className="auth-link primary">Sign Up</Link>
            </div>
          )}

          <button
            className="mobile-menu-btn"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;