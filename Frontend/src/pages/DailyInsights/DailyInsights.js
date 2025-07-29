import React, { useState, useEffect, useCallback } from 'react';
import './DailyInsights.css';

const DailyInsights = () => {
  // 전체 인사이트 목록 상태 (기존 + 새로 생성)
  const [insights, setInsights] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState({ status: '', progress: 0, message: '' });
  const [error, setError] = useState(null);

  // 각 인사이트의 확장 상태를 별도로 관리 (핵심 수정!)
  const [expandedStates, setExpandedStates] = useState({});

  // API 기본 URL
  const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8001'
    : `http://${window.location.hostname}:8001`;

  // 날짜 포맷팅
  const formatDate = (dateString) => {
    const options = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long'
    };
    return new Date(dateString).toLocaleDateString('ko-KR', options);
  };

  // 확장 상태 토글 함수 (useCallback으로 최적화)
  const toggleExpanded = useCallback((insightId) => {
    setExpandedStates(prev => ({
      ...prev,
      [insightId]: !prev[insightId]
    }));
  }, []);

  // 새로운 인사이트 생성 (기존 인사이트는 유지)
  const generateNewInsight = async () => {
    console.log('새 인사이트 생성 시작');

    setIsGenerating(true);
    setError(null);
    setProgress({ status: 'starting', progress: 10, message: '새로운 인사이트 생성 중...' });

    try {
      // 1. 인사이트 생성 + 영상 생성 요청
      const response = await fetch(`${API_BASE_URL}/api/insights/generate-video/current_user?refresh_data=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          avatar_id: "default",
          voice_id: "default",
          background: "professional"  // office -> professional로 변경
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API 요청 실패: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      console.log('인사이트 생성 완료:', result);

      // 2. 새로운 인사이트 데이터 생성
      const newInsightId = `insight_${Date.now()}`;
      const newInsight = {
        id: newInsightId,
        date: new Date().toISOString().split('T')[0],
        headline: '실시간 AI 생성 투자 인사이트',
        summary: result.script_info.script.substring(0, 200) + '...',
        fullContent: result.script_info.script,
        scriptLength: result.script_info.script_length,
        readingTime: result.script_info.estimated_reading_time,
        analysisMethod: result.insight_data.analysis_method,
        modelUsed: result.insight_data.model_used,
        videoUrl: null,
        videoThumbnail: 'https://via.placeholder.com/600x300/9c27b0/ffffff?text=실시간+AI+인사이트',
        tags: ['실시간', 'AI 생성', '개인화'],
        isGenerating: true
      };

      // 3. 기존 인사이트 목록 맨 앞에 새 인사이트 추가
      setInsights(prevInsights => [newInsight, ...prevInsights]);

      const videoId = result.video_info.video_id;
      console.log('영상 ID:', videoId);

      setProgress({ status: 'processing', progress: 30, message: '영상 생성 중... 약 2-3분 소요 예상' });

      // 4. 영상 생성 상태 모니터링
      await monitorVideoProgress(videoId, newInsightId);

    } catch (error) {
      console.error('인사이트 생성 오류:', error);
      setError(`새 인사이트 생성 실패: ${error.message}`);
      setProgress({ status: 'failed', progress: 0, message: '생성 실패' });
    } finally {
      setIsGenerating(false);
    }
  };

  // 영상 생성 진행상황 모니터링 (useCallback으로 최적화)
  const monitorVideoProgress = useCallback(async (videoId, insightId) => {
    return new Promise((resolve, reject) => {
      let attempts = 0;
      const maxAttempts = 1200; // 10분

      const checkStatus = async () => {
        attempts++;

        try {
          const response = await fetch(`${API_BASE_URL}/api/insights/video-status/${videoId}`);

          if (!response.ok) {
            throw new Error('상태 확인 실패');
          }

          const data = await response.json();
          const status = data.status;

          console.log(`영상 상태 (${attempts}/${maxAttempts}):`, status);

          // 진행률 계산
          const progressPercent = Math.min(90, 30 + (attempts / maxAttempts) * 60);

          setProgress({
            status: status,
            progress: progressPercent,
            message: getStatusMessage(status, attempts, maxAttempts)
          });

          if (status === 'completed') {
            // 해당 인사이트에 비디오 URL 업데이트 (불변성 유지)
            setInsights(prevInsights =>
              prevInsights.map(insight =>
                insight.id === insightId
                  ? { ...insight, videoUrl: data.video_url, isGenerating: false }
                  : insight
              )
            );
            setProgress({ status: 'completed', progress: 100, message: '영상 생성 완료!' });
            resolve();
          } else if (status === 'failed') {
            // 생성 실패한 인사이트 표시 업데이트
            setInsights(prevInsights =>
              prevInsights.map(insight =>
                insight.id === insightId
                  ? { ...insight, isGenerating: false, videoFailed: true }
                  : insight
              )
            );
            throw new Error('영상 생성 실패');
          } else if (attempts >= maxAttempts) {
            setInsights(prevInsights =>
              prevInsights.map(insight =>
                insight.id === insightId
                  ? { ...insight, isGenerating: false, videoFailed: true }
                  : insight
              )
            );
            throw new Error('시간 초과');
          } else {
            // 5초 후 다시 확인
            setTimeout(checkStatus, 5000);
          }

        } catch (error) {
          setProgress({ status: 'failed', progress: 0, message: error.message });
          reject(error);
        }
      };

      // 첫 번째 상태 확인
      checkStatus();
    });
  }, [API_BASE_URL]);

  // 상태 메시지 생성
  const getStatusMessage = (status, attempts, maxAttempts) => {
    switch (status) {
      case 'processing':
        const remaining = Math.max(1, Math.ceil((maxAttempts - attempts) / 12));
        return `영상 처리 중... 약 ${remaining}분 남음`;
      case 'waiting':
        return '대기 중...';
      case 'pending':
        return '처리 대기 중...';
      case 'completed':
        return '영상 생성 완료!';
      case 'failed':
        return '영상 생성 실패';
      default:
        return '상태 확인 중...';
    }
  };

  // 개별 인사이트 컴포넌트 (React.memo로 최적화)
  const InsightCard = React.memo(({ insight, isLatest, isExpanded, onToggleExpand }) => {
    return (
      <article className={`insight-card ${isLatest ? 'latest' : ''}`}>
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

        {/* 영상 영역 */}
        <div className="insight-video-container">
          {insight.videoUrl ? (
            // 영상 완성됨
            <video
              src={insight.videoUrl}
              controls
              className="insight-video-thumbnail"
              poster={insight.videoThumbnail}
            />
          ) : (
            // 영상 생성 중, 대기, 또는 실패
            <>
              <img
                src={insight.videoThumbnail}
                alt={insight.headline}
                className="insight-video-thumbnail"
              />
              <div className="video-play-overlay">
                {insight.isGenerating ? (
                  // 영상 생성 중
                  <div className="video-generation-progress">
                    <div className="loading-spinner"></div>
                    <div className="progress-info">
                      <div className="progress-status">
                        {isLatest && progress.message ? progress.message : '영상 생성 중...'}
                      </div>
                      {isLatest && progress.progress > 0 && (
                        <div className="progress-bar">
                          <div
                            className="progress-fill"
                            style={{ width: `${progress.progress}%` }}
                          ></div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : insight.videoFailed ? (
                  // 영상 생성 실패
                  <div className="video-failed">
                    <span>⚠️ 영상 생성 실패</span>
                  </div>
                ) : (
                  // 기본 상태 (Mock 데이터)
                  <div className="play-button">📹</div>
                )}
              </div>
            </>
          )}
        </div>

        {/* 스크립트 내용 */}
        <div className="insight-content">
          <p className="insight-summary">
            {isExpanded ? insight.fullContent : insight.summary}
          </p>

          <button
            className="read-more-btn"
            onClick={onToggleExpand}
          >
            {isExpanded ? '접기' : '전체 스크립트 보기'}
          </button>
        </div>

        <div className="insight-footer">
          <span className="insight-source">
            AI 생성 • 귀하의 포트폴리오 기반 • {insight.analysisMethod}
          </span>
        </div>
      </article>
    );
  });

  // 컴포넌트 마운트시 Mock 데이터 로드
  useEffect(() => {
    const mockInsights = [
      {
        id: 'mock_1',
        date: '2025-01-27',
        headline: '삼성전자 반도체 부문 실적 개선 전망',
        summary: 'AI 반도체 수요 증가로 인한 메모리 가격 상승세가 지속되고 있습니다. 삼성전자의 4분기 실적 발표를 앞두고 긍정적인 전망이 이어지고 있으며...',
        fullContent: 'AI 반도체 수요 증가로 인한 메모리 가격 상승세가 지속되고 있습니다. 삼성전자의 4분기 실적 발표를 앞두고 긍정적인 전망이 이어지고 있으며, 특히 HBM(고대역폭 메모리) 부문에서의 성장이 주목받고 있습니다. 엔비디아와의 공급 계약 확대 소식과 함께 중장기적으로 안정적인 성장이 예상됩니다. 다만 중국 시장 불확실성과 환율 변동성은 여전히 리스크 요인으로 작용할 것으로 보입니다.',
        scriptLength: 187,
        readingTime: '약 1분',
        analysisMethod: 'Graph RAG + 실시간 뉴스 분석',
        modelUsed: 'GPT-4',
        videoUrl: null,
        videoThumbnail: 'https://via.placeholder.com/600x300/4285f4/ffffff?text=삼성전자+반도체+분석',
        tags: ['반도체', '삼성전자', 'AI']
      },
      {
        id: 'mock_2',
        date: '2025-01-26',
        headline: 'NAVER 클라우드 사업 확장과 AI 투자 현황',
        summary: 'NAVER가 하이퍼클로바X 기반의 B2B 사업을 본격 확장하고 있습니다. 클라우드 매출이 전년 대비 35% 증가하며 성장세를 보이고 있고...',
        fullContent: 'NAVER가 하이퍼클로바X 기반의 B2B 사업을 본격 확장하고 있습니다. 클라우드 매출이 전년 대비 35% 증가하며 성장세를 보이고 있고, 특히 금융권과 공공기관에서의 도입이 활발합니다. AI 검색 고도화와 개인화 서비스 강화로 MAU 증가세도 지속되고 있어 긍정적입니다. 다만 광고 시장 경쟁 심화와 신규 서비스 투자비용 증가는 단기 수익성에 부담을 줄 수 있습니다.',
        scriptLength: 162,
        readingTime: '약 1분',
        analysisMethod: 'DART 공시 + 뉴스 크롤링',
        modelUsed: 'GPT-4',
        videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        videoThumbnail: 'https://via.placeholder.com/600x300/03c75a/ffffff?text=NAVER+클라우드+AI',
        tags: ['NAVER', 'AI', '클라우드']
      },
      {
        id: 'mock_3',
        date: '2025-01-25',
        headline: 'SK하이닉스 HBM 시장 점유율 확대 전략',
        summary: 'SK하이닉스가 HBM3E 양산을 본격화하며 엔비디아 H200 GPU 공급을 시작했습니다. HBM 시장에서의 독점적 지위를 활용해...',
        fullContent: 'SK하이닉스가 HBM3E 양산을 본격화하며 엔비디아 H200 GPU 공급을 시작했습니다. HBM 시장에서의 독점적 지위를 활용해 마진율 개선이 기대됩니다. 2025년 HBM 매출은 전년 대비 100% 이상 증가할 것으로 전망되며, 차세대 HBM4 개발도 순조롭게 진행되고 있습니다. AMD, 구글과의 파트너십 확대도 성장 동력이 될 것으로 보입니다.',
        scriptLength: 145,
        readingTime: '약 50초',
        analysisMethod: 'Graph RAG + 실시간 시세',
        modelUsed: 'GPT-4',
        videoUrl: null,
        videoThumbnail: 'https://via.placeholder.com/600x300/ff6b35/ffffff?text=SK하이닉스+HBM',
        tags: ['SK하이닉스', 'HBM', '메모리']
      }
    ];

    setInsights(mockInsights);
  }, []);

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
            onClick={generateNewInsight}
            disabled={isGenerating}
          >
            {isGenerating ? <span className="loading-spinner"></span> : '🔄'}
            새 인사이트 생성
          </button>
        </div>

        {/* 에러 상태 */}
        {error && (
          <div className="error-state">
            <div className="error-icon">⚠️</div>
            <h3>인사이트 생성 오류</h3>
            <p>{error}</p>
            <button className="retry-button" onClick={generateNewInsight}>
              다시 시도
            </button>
          </div>
        )}

        {/* 인사이트 목록 */}
        <div className="insights-list">
          {insights.map((insight, index) => (
            <InsightCard
              key={insight.id}
              insight={insight}
              isLatest={index === 0 && insight.isGenerating}
              isExpanded={expandedStates[insight.id] || false}
              onToggleExpand={() => toggleExpanded(insight.id)}
            />
          ))}
        </div>

        {/* 빈 상태 */}
        {insights.length === 0 && !error && (
          <div className="loading-state">
            <div className="loading-spinner large"></div>
            <p>데일리 인사이트를 불러오는 중...</p>
          </div>
        )}

        {/* 디버깅 정보 (개발 환경에서만) */}
        {process.env.NODE_ENV === 'development' && (
          <div style={{
            position: 'fixed',
            bottom: '10px',
            right: '10px',
            background: 'rgba(0,0,0,0.8)',
            color: 'white',
            padding: '10px',
            borderRadius: '5px',
            fontSize: '12px',
            zIndex: 1000
          }}>
            <div>영상 생성 중: {isGenerating ? 'YES' : 'NO'}</div>
            <div>진행률: {progress.progress}%</div>
            <div>상태: {progress.status}</div>
            <div>확장된 카드: {Object.keys(expandedStates).filter(id => expandedStates[id]).length}개</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DailyInsights;
