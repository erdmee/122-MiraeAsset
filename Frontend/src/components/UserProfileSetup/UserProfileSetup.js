import React, { useState } from 'react';
import { useUser } from '../../context/UserContext';
import './UserProfileSetup.css';

const UserProfileSetup = ({ onComplete }) => {
  const { saveUser } = useUser();
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    investment_experience: '',
    risk_tolerance: '',
    investment_goals: [],
    preferred_sectors: [],
    investment_style: '',
    investment_amount_range: '',
    news_keywords: []
  });
  const [portfolio, setPortfolio] = useState([]);
  const [newStock, setNewStock] = useState({
    symbol: '',
    company_name: '',
    shares: '',
    avg_price: '',
    sector: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };



  const handleCheckboxChange = (e) => {
    const { name, value, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: checked 
        ? [...prev[name], value]
        : prev[name].filter(item => item !== value)
    }));
  };

  const addStock = () => {
    if (newStock.symbol && newStock.company_name && newStock.shares && newStock.avg_price) {
      setPortfolio(prev => [...prev, {
        ...newStock,
        shares: parseInt(newStock.shares),
        avg_price: parseFloat(newStock.avg_price)
      }]);
      setNewStock({
        symbol: '',
        company_name: '',
        shares: '',
        avg_price: '',
        sector: ''
      });
    }
  };

  const removeStock = (index) => {
    setPortfolio(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // 사용자 ID 생성 (이름 + 타임스탬프)
      const userId = `${formData.name.replace(/\s+/g, '_')}_${Date.now()}`;
      
      // 사용자 프로필 저장
      const profileResponse = await fetch('http://localhost:8001/api/user/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          ...formData,
          age: parseInt(formData.age)
        }),
      });

      if (!profileResponse.ok) {
        throw new Error('프로필 저장에 실패했습니다.');
      }

      // 포트폴리오 저장 (있는 경우)
      if (portfolio.length > 0) {
        const portfolioResponse = await fetch('http://localhost:8001/api/user/portfolio', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: userId,
            holdings: portfolio
          }),
        });

        if (!portfolioResponse.ok) {
          throw new Error('포트폴리오 저장에 실패했습니다.');
        }
      }

      // 로컬 상태에 사용자 정보 저장
      const userProfile = {
        user_id: userId,
        name: formData.name,
        ...formData,
        portfolio: portfolio
      };

      saveUser(userProfile);
      
      if (onComplete) {
        onComplete(userProfile);
      }

    } catch (error) {
      console.error('사용자 설정 저장 실패:', error);
      alert('설정 저장에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const nextStep = () => {
    setCurrentStep(prev => prev + 1);
  };

  const prevStep = () => {
    setCurrentStep(prev => prev - 1);
  };

  const isStep1Valid = formData.name && formData.age && formData.investment_experience && formData.risk_tolerance;
  const isStep2Valid = formData.investment_goals.length > 0 && formData.preferred_sectors.length > 0;

  return (
    <div className="user-profile-setup">
      <div className="setup-container">
        <div className="setup-header">
          <h2>개인화된 투자 인사이트를 위한 프로필 설정</h2>
          <div className="step-indicator">
            <span className={currentStep >= 1 ? 'active' : ''}>1</span>
            <span className={currentStep >= 2 ? 'active' : ''}>2</span>
            <span className={currentStep >= 3 ? 'active' : ''}>3</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="setup-form">
          {currentStep === 1 && (
            <div className="form-step">
              <h3>기본 정보</h3>
              
              <div className="form-group">
                <label htmlFor="name">이름 *</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="홍길동"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="age">나이 *</label>
                <input
                  type="number"
                  id="age"
                  name="age"
                  value={formData.age}
                  onChange={handleInputChange}
                  placeholder="30"
                  min="18"
                  max="100"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="investment_experience">투자 경험 *</label>
                <select
                  id="investment_experience"
                  name="investment_experience"
                  value={formData.investment_experience}
                  onChange={handleInputChange}
                  required
                >
                  <option value="">선택하세요</option>
                  <option value="초급">초급 (1년 미만)</option>
                  <option value="중급">중급 (1-5년)</option>
                  <option value="고급">고급 (5년 이상)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="risk_tolerance">위험 허용도 *</label>
                <select
                  id="risk_tolerance"
                  name="risk_tolerance"
                  value={formData.risk_tolerance}
                  onChange={handleInputChange}
                  required
                >
                  <option value="">선택하세요</option>
                  <option value="보수적">보수적 (안정성 우선)</option>
                  <option value="중위험">중위험 (균형 추구)</option>
                  <option value="공격적">공격적 (수익성 우선)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="investment_amount_range">투자 규모</label>
                <select
                  id="investment_amount_range"
                  name="investment_amount_range"
                  value={formData.investment_amount_range}
                  onChange={handleInputChange}
                >
                  <option value="">선택하세요</option>
                  <option value="1천만원 미만">1천만원 미만</option>
                  <option value="1천만원-3천만원">1천만원-3천만원</option>
                  <option value="3천만원-5천만원">3천만원-5천만원</option>
                  <option value="5천만원-1억원">5천만원-1억원</option>
                  <option value="1억원 이상">1억원 이상</option>
                </select>
              </div>

              <div className="step-buttons">
                <button
                  type="button"
                  onClick={nextStep}
                  disabled={!isStep1Valid}
                  className="btn-next"
                >
                  다음 단계
                </button>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="form-step">
              <h3>투자 선호도</h3>
              
              <div className="form-group">
                <label>투자 목표 * (복수 선택 가능)</label>
                <div className="checkbox-group">
                  {['장기투자', '자산증식', '월배당', '은퇴준비', '목돈마련'].map(goal => (
                    <label key={goal} className="checkbox-label">
                      <input
                        type="checkbox"
                        name="investment_goals"
                        value={goal}
                        checked={formData.investment_goals.includes(goal)}
                        onChange={handleCheckboxChange}
                      />
                      {goal}
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>관심 섹터 * (복수 선택 가능)</label>
                <div className="checkbox-group">
                  {['IT', '바이오', '에너지', '금융', '제조업', '소비재', '부동산'].map(sector => (
                    <label key={sector} className="checkbox-label">
                      <input
                        type="checkbox"
                        name="preferred_sectors"
                        value={sector}
                        checked={formData.preferred_sectors.includes(sector)}
                        onChange={handleCheckboxChange}
                      />
                      {sector}
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="investment_style">투자 스타일</label>
                <select
                  id="investment_style"
                  name="investment_style"
                  value={formData.investment_style}
                  onChange={handleInputChange}
                >
                  <option value="">선택하세요</option>
                  <option value="성장주">성장주 (높은 성장 잠재력)</option>
                  <option value="가치주">가치주 (저평가된 우량주)</option>
                  <option value="배당주">배당주 (안정적 배당 수익)</option>
                  <option value="균형투자">균형투자 (다양한 투자 혼합)</option>
                </select>
              </div>

              <div className="step-buttons">
                <button type="button" onClick={prevStep} className="btn-prev">
                  이전 단계
                </button>
                <button
                  type="button"
                  onClick={nextStep}
                  disabled={!isStep2Valid}
                  className="btn-next"
                >
                  다음 단계
                </button>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="form-step">
              <h3>포트폴리오 (선택사항)</h3>
              
              <div className="portfolio-section">
                <h4>보유 종목 추가</h4>
                <div className="stock-input-grid">
                  <input
                    type="text"
                    placeholder="종목코드 (예: 005930)"
                    value={newStock.symbol}
                    onChange={(e) => setNewStock(prev => ({...prev, symbol: e.target.value}))}
                  />
                  <input
                    type="text"
                    placeholder="회사명 (예: 삼성전자)"
                    value={newStock.company_name}
                    onChange={(e) => setNewStock(prev => ({...prev, company_name: e.target.value}))}
                  />
                  <input
                    type="number"
                    placeholder="보유 주식 수"
                    value={newStock.shares}
                    onChange={(e) => setNewStock(prev => ({...prev, shares: e.target.value}))}
                  />
                  <input
                    type="number"
                    placeholder="평균 매입가"
                    value={newStock.avg_price}
                    onChange={(e) => setNewStock(prev => ({...prev, avg_price: e.target.value}))}
                  />
                  <select
                    value={newStock.sector}
                    onChange={(e) => setNewStock(prev => ({...prev, sector: e.target.value}))}
                  >
                    <option value="">섹터 선택</option>
                    <option value="IT/기술">IT/기술</option>
                    <option value="바이오/제약">바이오/제약</option>
                    <option value="에너지">에너지</option>
                    <option value="금융">금융</option>
                    <option value="제조업">제조업</option>
                    <option value="소비재">소비재</option>
                  </select>
                  <button type="button" onClick={addStock} className="btn-add-stock">
                    추가
                  </button>
                </div>

                {portfolio.length > 0 && (
                  <div className="portfolio-list">
                    <h4>추가된 종목</h4>
                    {portfolio.map((stock, index) => (
                      <div key={index} className="portfolio-item">
                        <span>{stock.company_name} ({stock.symbol})</span>
                        <span>{stock.shares}주</span>
                        <span>{stock.avg_price.toLocaleString()}원</span>
                        <button type="button" onClick={() => removeStock(index)} className="btn-remove">
                          삭제
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="step-buttons">
                <button type="button" onClick={prevStep} className="btn-prev">
                  이전 단계
                </button>
                <button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="btn-submit"
                >
                  {isSubmitting ? '저장 중...' : '설정 완료'}
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default UserProfileSetup;
