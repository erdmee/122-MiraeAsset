import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Header.css';

const Header = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <header className="header">
      <div className="header-container">
        {/* Logo and Brand */}
        <div className="header-brand">
          <Link to="/" className="brand-link">
            <div className="brand-logo">
              <span className="brand-text">Mirae Asset</span>
              <span className="brand-subtext">Team 122</span>
            </div>
          </Link>
        </div>

        {/* Desktop Navigation */}
        <nav className="header-nav desktop-nav">
          <Link 
            to="/" 
            className={`nav-link ${isActive('/') ? 'active' : ''}`}
          >
            홈
          </Link>
          <Link 
            to="/daily-insights" 
            className={`nav-link ${isActive('/daily-insights') ? 'active' : ''}`}
          >
            데일리 인사이트
          </Link>
          <Link 
            to="/chatbot" 
            className={`nav-link ${isActive('/chatbot') ? 'active' : ''}`}
          >
            AI 챗봇 어시스턴트
          </Link>
        </nav>

        {/* Mobile Menu Button */}
        <button 
          className="mobile-menu-btn"
          onClick={toggleMobileMenu}
          aria-label="Toggle mobile menu"
        >
          <span className={`hamburger ${isMobileMenuOpen ? 'open' : ''}`}>
            <span></span>
            <span></span>
            <span></span>
          </span>
        </button>

        {/* Mobile Navigation */}
        <nav className={`header-nav mobile-nav ${isMobileMenuOpen ? 'open' : ''}`}>
          <Link 
            to="/" 
            className={`nav-link ${isActive('/') ? 'active' : ''}`}
            onClick={() => setIsMobileMenuOpen(false)}
          >
            홈
          </Link>
          <Link 
            to="/daily-insights" 
            className={`nav-link ${isActive('/daily-insights') ? 'active' : ''}`}
            onClick={() => setIsMobileMenuOpen(false)}
          >
            데일리 인사이트
          </Link>
          <Link 
            to="/chatbot" 
            className={`nav-link ${isActive('/chatbot') ? 'active' : ''}`}
            onClick={() => setIsMobileMenuOpen(false)}
          >
            AI 챗봇 어시스턴트
          </Link>
        </nav>
      </div>
    </header>
  );
};

export default Header;