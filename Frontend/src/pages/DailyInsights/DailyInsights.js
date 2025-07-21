import React, { useState, useEffect } from 'react';
import './DailyInsights.css';

const DailyInsights = () => {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [expandedPosts, setExpandedPosts] = useState(new Set());
  const insightsPerPage = 5;

  // 데모용 목업 데이터
  const mockInsights = [
    {
      id: 1,
      date: '2025-01-20',
      headline: 'AI 기술 혁신 발표로 인한 기술주 랠리',
      summary: '주요 기술 기업들이 AI 개발 혁신 발표 이후 오늘 큰 상승세를 보였습니다. 귀하의 포트폴리오에 있는 NVDA와 MSFT는 각각 3.2%와 2.8%의 강한 성과를 보였습니다.',
      fullContent: '주요 기술 기업들이 AI 개발 혁신 발표 이후 오늘 큰 상승세를 보였습니다. 귀하의 포트폴리오에 있는 NVDA와 MSFT는 각각 3.2%와 2.8%의 강한 성과를 보였습니다. 시장 심리는 AI 관련 투자에 대해 여전히 강세를 유지하고 있습니다.\n\n특히 NVIDIA는 새로운 AI 칩셋 발표와 함께 클라우드 컴퓨팅 파트너십 확대를 발표했습니다. Microsoft는 Azure AI 서비스의 새로운 기능들을 공개하며 기업 고객들의 관심을 끌었습니다.\n\n전문가들은 이러한 AI 기술 발전이 장기적으로 생산성 향상과 새로운 비즈니스 모델 창출에 기여할 것으로 예상한다고 분석했습니다. 다만 단기적으로는 밸류에이션에 대한 우려도 제기되고 있어 신중한 접근이 필요합니다.',
      videoThumbnail: 'https://via.placeholder.com/600x300/ff6b35/ffffff?text=AI+기술+혁신+발표',
      tags: ['기술', 'AI', '포트폴리오 알림']
    },
    {
      id: 2,
      date: '2025-01-19',
      headline: '연준, 잠재적 금리 조정 신호',
      summary: '연방준비제도이사회가 다음 분기에 금리 조정 가능성을 시사했습니다. 이러한 변화는 귀하의 채권 보유와 배당 중심 주식에 영향을 미칠 수 있습니다.',
      fullContent: '연방준비제도이사회가 다음 분기에 금리 조정 가능성을 시사했습니다. 이러한 변화는 귀하의 채권 보유와 배당 중심 주식에 영향을 미칠 수 있습니다. 포트폴리오의 금융 섹터 주식은 변동성이 증가할 수 있습니다.\n\n제롬 파월 연준 의장은 최근 연설에서 인플레이션 지표와 고용 시장 상황을 종합적으로 고려하여 통화 정책을 조정할 것이라고 밝혔습니다. 시장에서는 0.25% 포인트 인하 가능성이 높다고 보고 있습니다.\n\n이에 따라 은행주들은 혼조세를 보이고 있으며, 부동산 투자신탁(REITs)과 유틸리티 주식들은 상승세를 나타내고 있습니다. 투자자들은 금리 변화에 민감한 섹터들의 동향을 주의 깊게 살펴볼 필요가 있습니다.',
      videoThumbnail: 'https://via.placeholder.com/600x300/2c5aa0/ffffff?text=연준+금리+정책',
      tags: ['연준', '금리', '채권']
    },
    {
      id: 3,
      date: '2025-01-18',
      headline: '에너지 섹터 전망: 재생 에너지 vs 전통 에너지',
      summary: '재생 에너지 주식이 계속해서 전통적인 에너지 기업들보다 좋은 성과를 보이고 있습니다. 귀하의 청정 에너지 ETF 보유량은 이번 주 4.1% 상승했습니다.',
      fullContent: '재생 에너지 주식이 계속해서 전통적인 에너지 기업들보다 좋은 성과를 보이고 있습니다. 귀하의 청정 에너지 ETF 보유량은 이번 주 4.1% 상승했습니다. 주요 석유 기업들의 기업 공시는 지속 가능한 에너지로의 전략적 전환을 시사합니다.\n\n태양광과 풍력 에너지 기업들이 새로운 프로젝트 계약을 잇따라 발표하면서 투자자들의 관심이 집중되고 있습니다. 특히 배터리 저장 기술의 발전으로 재생 에너지의 효율성이 크게 개선되고 있습니다.\n\n반면 전통적인 석유 기업들도 ESG 경영을 강화하며 청정 에너지 사업에 대한 투자를 확대하고 있어, 장기적으로는 에너지 전환 과정에서 새로운 기회를 찾을 수 있을 것으로 전망됩니다.',
      videoThumbnail: 'https://via.placeholder.com/600x300/28a745/ffffff?text=재생+에너지+전망',
      tags: ['에너지', '재생 에너지', 'ETF 성과']
    },
    {
      id: 4,
      date: '2025-01-17',
      headline: '헬스케어 혁신이 시장 낙관론 견인',
      summary: '획기적인 의학 연구 발표로 헬스케어 주식이 상승했습니다. 귀하의 제약 보유 주식은 일부 기업들이 긍정적인 임상 시험 결과를 보고하면서 혼합된 결과를 보였습니다.',
      fullContent: '획기적인 의학 연구 발표로 헬스케어 주식이 상승했습니다. 귀하의 제약 보유 주식은 일부 기업들이 긍정적인 임상 시험 결과를 보고하면서 혼합된 결과를 보였습니다. 다음 달 규제 승인이 예상됩니다.\n\n특히 알츠하이머 치료제와 암 면역치료제 분야에서 주목할 만한 진전이 있었습니다. 여러 제약회사들이 3상 임상시험에서 긍정적인 결과를 발표하며 투자자들의 기대감을 높였습니다.\n\nAI를 활용한 신약 개발 플랫폼들도 주목받고 있으며, 개발 기간 단축과 성공률 향상에 기여하고 있습니다. 바이오테크 기업들의 파이프라인 다양화와 함께 헬스케어 섹터의 장기 성장 전망이 밝아지고 있습니다.',
      videoThumbnail: 'https://via.placeholder.com/600x300/dc3545/ffffff?text=헬스케어+혁신',
      tags: ['헬스케어', '제약', '임상 시험']
    },
    {
      id: 5,
      date: '2025-01-16',
      headline: '글로벌 공급망 개선으로 제조업 활성화',
      summary: '공급망 혼란이 완화되면서 제조업 섹터가 회복 조짐을 보이고 있습니다. 귀하의 산업 주식 보유는 물류 개선과 운송 비용 감소로 혜택을 받았습니다.',
      fullContent: '공급망 혼란이 완화되면서 제조업 섹터가 회복 조짐을 보이고 있습니다. 귀하의 산업 주식 보유는 물류 개선과 운송 비용 감소로 혜택을 받았습니다. 분기별 실적 보고서는 다음 주에 예정되어 있습니다.\n\n아시아 지역의 생산 정상화와 함께 해운비 안정화가 제조업체들의 마진 개선에 기여하고 있습니다. 특히 자동차, 전자제품, 기계 부문에서 주문량이 크게 증가했습니다.\n\n스마트 팩토리와 자동화 기술 도입으로 생산 효율성도 향상되고 있어, 제조업의 디지털 전환이 가속화되고 있습니다. 이러한 변화는 장기적으로 제조업 경쟁력 강화에 긍정적인 영향을 미칠 것으로 예상됩니다.',
      videoThumbnail: 'https://via.placeholder.com/600x300/6c757d/ffffff?text=제조업+회복',
      tags: ['제조업', '공급망', '실적']
    }
  ];

  // Simulate API call
  const fetchInsights = async (page = 1) => {
    setLoading(true);

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));

    const startIndex = (page - 1) * insightsPerPage;
    const endIndex = startIndex + insightsPerPage;
    const pageInsights = mockInsights.slice(startIndex, endIndex);

    if (page === 1) {
      setInsights(pageInsights);
    } else {
      setInsights(prev => [...prev, ...pageInsights]);
    }

    setHasMore(endIndex < mockInsights.length);
    setLoading(false);
  };

  useEffect(() => {
    fetchInsights(1);
  }, []);

  const loadMore = () => {
    if (!loading && hasMore) {
      const nextPage = currentPage + 1;
      setCurrentPage(nextPage);
      fetchInsights(nextPage);
    }
  };

  const formatDate = (dateString) => {
    const options = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long'
    };
    return new Date(dateString).toLocaleDateString('ko-KR', options);
  };

  const refreshInsights = () => {
    setCurrentPage(1);
    setExpandedPosts(new Set());
    fetchInsights(1);
  };

  const toggleExpanded = (postId) => {
    setExpandedPosts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(postId)) {
        newSet.delete(postId);
      } else {
        newSet.add(postId);
      }
      return newSet;
    });
  };

  return (
    <div className="daily-insights">
      <div className="insights-container">
        {/* 헤더 */}
        <div className="insights-header">
          <h1 className="page-title">데일리 인사이트</h1>
          <p className="page-subtitle">
            귀하의 포트폴리오 보유 현황에 기반한 AI 생성 시장 분석
          </p>
          <button
            className="refresh-button"
            onClick={refreshInsights}
            disabled={loading}
          >
            {loading ? <span className="loading-spinner"></span> : '🔄'}
            인사이트 새로고침
          </button>
        </div>

        {/* 인사이트 목록 */}
        <div className="insights-list">
          {insights.map((insight) => {
            const isExpanded = expandedPosts.has(insight.id);
            return (
              <article key={insight.id} className="insight-card">
                <div className="insight-header">
                  <div className="insight-date">
                    {formatDate(insight.date)}
                  </div>
                  <div className="insight-tags">
                    {insight.tags.map((tag, index) => (
                      <span key={index} className="insight-tag">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <h2 className="insight-headline">
                  {insight.headline}
                </h2>

                {/* 동영상 썸네일 (이미지로 대체) */}
                <div className="insight-video-container">
                  <img
                    src={insight.videoThumbnail}
                    alt={insight.headline}
                    className="insight-video-thumbnail"
                  />
                  <div className="video-play-overlay">
                    <div className="play-button">▶</div>
                  </div>
                </div>

                {/* 텍스트 콘텐츠 */}
                <div className="insight-content">
                  <p className="insight-summary">
                    {isExpanded ? insight.fullContent : insight.summary}
                  </p>

                  <button
                    className="read-more-btn"
                    onClick={() => toggleExpanded(insight.id)}
                  >
                    {isExpanded ? '접기' : '더보기'}
                  </button>
                </div>

                <div className="insight-footer">
                  <span className="insight-source">
                    AI 생성 • 귀하의 포트폴리오 기반
                  </span>
                </div>
              </article>
            );
          })}
        </div>

        {/* 로딩 상태 */}
        {loading && insights.length === 0 && (
          <div className="loading-state">
            <div className="loading-spinner large"></div>
            <p>데일리 인사이트를 불러오는 중...</p>
          </div>
        )}

        {/* 더 불러오기 버튼 */}
        {!loading && hasMore && insights.length > 0 && (
          <div className="load-more-container">
            <button
              className="load-more-button"
              onClick={loadMore}
            >
              인사이트 더 불러오기
            </button>
          </div>
        )}

        {/* 콘텐츠 끝 메시지 */}
        {!loading && !hasMore && insights.length > 0 && (
          <div className="end-message">
            <p>모든 데일리 인사이트를 확인하셨습니다.</p>
          </div>
        )}

        {/* 빈 상태 */}
        {!loading && insights.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">📊</div>
            <h3>이용 가능한 인사이트가 없습니다</h3>
            <p>맞춤형 시장 분석을 위해 나중에 다시 확인해주세요.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DailyInsights;