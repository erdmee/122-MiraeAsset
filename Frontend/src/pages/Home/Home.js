import React from 'react';
import { Link } from 'react-router-dom';
import './Home.css';

const Home = () => {
  return (
    <div className="home">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-container">
          <div className="hero-content">
            <h1 className="hero-title">
              Mirae Asset Team 122
            </h1>
            <p className="hero-subtitle">
              스마트 투자 결정을 위한 고급 금융 AI 플랫폼
            </p>
            <p className="hero-description">
              최첨단 인공지능을 활용하여 시장 동향을 분석하고, 일일 인사이트를 생성하며,
              종합적인 금융 플랫폼으로 정보에 기반한 투자 결정을 내릴 수 있습니다.
            </p>
            <div className="hero-actions">
              <Link to="/daily-insights" className="cta-button primary">
                데일리 인사이트 보기
              </Link>
              <Link to="/chatbot" className="cta-button secondary">
                AI 어시스턴트 시작하기
              </Link>
            </div>
          </div>
          <div className="hero-visual">
            <div className="hero-graphic">
              <div className="graphic-element orange-cube"></div>
              <div className="graphic-element white-cube"></div>
              <div className="graphic-element small-cube"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="features-container">
          <h2 className="section-title">AI 기반 주요 기능</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">
                <div className="icon-circle">📊</div>
              </div>
              <h3 className="feature-title">데일리 마켓 인사이트</h3>
              <p className="feature-description">
                보유 주식에 기반한 맞춤형 일일 보고서를 받아보세요.
                AI가 생성한 시장 뉴스 및 기업 공시 분석 정보를 제공합니다.
              </p>
              <Link to="/daily-insights" className="feature-link">
                인사이트 살펴보기 →
              </Link>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <div className="icon-circle">🤖</div>
              </div>
              <h3 className="feature-title">AI 챗봇 어시스턴트</h3>
              <p className="feature-description">
                문서를 분석하고, 질문에 답변하며, 업로드된 파일을 기반으로
                맥락에 맞는 금융 조언을 제공하는 대화형 AI 어시스턴트입니다.
              </p>
              <Link to="/chatbot" className="feature-link">
                대화 시작하기 →
              </Link>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <div className="icon-circle">📈</div>
              </div>
              <h3 className="feature-title">스마트 분석</h3>
              <p className="feature-description">
                실시간 데이터 처리와 예측 모델링을 통한 고급 포트폴리오 분석으로
                더 나은 투자 전략을 수립할 수 있습니다.
              </p>
              <div className="feature-link disabled">
                출시 예정
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="stats-section">
        <div className="stats-container">
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-number">24/7</div>
              <div className="stat-label">AI 모니터링</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">1000+</div>
              <div className="stat-label">데이터 소스</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">실시간</div>
              <div className="stat-label">시장 분석</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">스마트</div>
              <div className="stat-label">추천 시스템</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;