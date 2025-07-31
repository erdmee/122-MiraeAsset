import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useUser } from '../../context/UserContext';
import './Header.css';

const Header = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const { user, clearUser, isLoggedIn } = useUser();

  // 디버깅: 사용자 정보 로그
  console.log('Header - 현재 사용자 정보:', user);
  console.log('Header - 로그인 상태:', isLoggedIn);
  console.log('Header - localStorage userProfile:', localStorage.getItem('userProfile'));

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

        {/* User Profile Section */}
        <div className="header-user">
          {isLoggedIn ? (
            <div className="user-info">
              <span className="user-name">안녕하세요, {user?.name || '사용자'}님</span>
              <button 
                onClick={clearUser} 
                className="logout-btn"
                title="로그아웃"
              >
                로그아웃
              </button>
            </div>
          ) : (
            <div className="login-prompt">
              <span>로그인이 필요합니다</span>
            </div>
          )}
        </div>

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
          
          {/* Mobile User Info */}
          {isLoggedIn && (
            <div className="mobile-user-info">
              <span className="user-name">{user?.name || '사용자'}님</span>
              <button onClick={clearUser} className="logout-btn">
                로그아웃
              </button>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
};

export default Header;