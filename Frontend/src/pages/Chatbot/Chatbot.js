import React, { useState, useRef, useEffect } from 'react';
import './Chatbot.css';

const Chatbot = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: '안녕하세요! 저는 AI 금융 어시스턴트입니다. 문서 분석, 투자에 관한 질문 답변, 시장 인사이트 제공 등을 도와드릴 수 있습니다. 오늘 어떻게 도와드릴까요?',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // 새 메시지가 도착하면 자동으로 하단으로 스크롤
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 백엔드 API 호출 시뮬레이션
  const sendMessageToAPI = async (message, files = []) => {
    // TODO: FastAPI 백엔드로의 실제 API 호출로 대체
    // const response = await fetch('/api/chat', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ message, files })
    // });
    // return await response.json();

    // 데모용 응답 시뮬레이션
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const responses = [
      "현재 시장 상황을 고려할 때, 다양한 섹터에 걸쳐 포트폴리오를 분산하는 것을 추천합니다. 특히 기술, 헬스케어, 소비재 섹터의 균형 있는 배분이 중요합니다.",
      "업로드하신 문서를 분석했습니다. 발견한 주요 금융 인사이트는 다음과 같습니다: 1) 현금 흐름이 안정적으로 증가하고 있음, 2) 부채 비율이 산업 평균보다 낮음, 3) 연간 수익 성장률이 15% 이상으로 양호함.",
      "최근 주식 시장은 변동성을 보이고 있습니다. 귀하의 보유 자산에 영향을 미치는 주요 요인으로는 금리 정책 변화, 인플레이션 우려, 글로벌 공급망 이슈가 있습니다. 단기적으로는 방어적 포지션을 유지하는 것이 좋겠습니다.",
      "이 재무제표를 이해하는 데 도움을 드릴 수 있습니다. 이 회사는 다음과 같은 강력한 기본 요소를 보여주고 있습니다: 안정적인 이익 마진, 낮은 부채 수준, 그리고 지속적인 연구개발 투자가 인상적입니다.",
      "시장 동향에 관한 질문에 기반하여, 데이터는 다음과 같은 결과를 시사합니다: 1) ESG 투자가 계속해서 증가할 것으로 예상됨, 2) 디지털 전환 관련 기업들이 장기적으로 성장 가능성이 높음, 3) 신흥 시장에서의 기회가 확대되고 있음."
    ];
    
    return {
      content: responses[Math.floor(Math.random() * responses.length)],
      success: true
    };
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() && uploadedFiles.length === 0) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      files: uploadedFiles,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setUploadedFiles([]);
    setIsTyping(true);

    try {
      const response = await sendMessageToAPI(inputMessage, uploadedFiles);
      
      if (response.success) {
        const botMessage = {
          id: Date.now() + 1,
          type: 'bot',
          content: response.content,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: '죄송합니다, 오류가 발생했습니다. 나중에 다시 시도해 주세요.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    const fileData = files.map(file => ({
      id: Date.now() + Math.random(),
      name: file.name,
      size: file.size,
      type: file.type,
      file: file
    }));
    
    setUploadedFiles(prev => [...prev, ...fileData]);
    e.target.value = ''; // Reset input
  };

  const removeFile = (fileId) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 바이트';
    const k = 1024;
    const sizes = ['바이트', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString('ko-KR', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="chatbot">
      <div className="chatbot-container">
        {/* 헤더 */}
        <div className="chatbot-header">
          <h1 className="chatbot-title">AI 챗봇 어시스턴트</h1>
          <p className="chatbot-subtitle">
            문서를 업로드하고 지능형 금융 인사이트를 받아보세요
          </p>
        </div>

        {/* 메시지 영역 */}
        <div className="messages-container">
          <div className="messages-list">
            {messages.map((message) => (
              <div 
                key={message.id} 
                className={`message ${message.type === 'user' ? 'user-message' : 'bot-message'}`}
              >
                <div className="message-content">
                  <div className="message-text">
                    {message.content}
                  </div>
                  
                  {/* 업로드된 파일 표시 */}
                  {message.files && message.files.length > 0 && (
                    <div className="message-files">
                      {message.files.map((file) => (
                        <div key={file.id} className="uploaded-file-display">
                          <span className="file-icon">📄</span>
                          <span className="file-name">{file.name}</span>
                          <span className="file-size">({formatFileSize(file.size)})</span>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="message-time">
                    {formatTime(message.timestamp)}
                  </div>
                </div>
              </div>
            ))}

            {/* 타이핑 표시기 */}
            {isTyping && (
              <div className="message bot-message">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* 입력 영역 */}
        <div className="input-container">
          {/* 파일 업로드 미리보기 */}
          {uploadedFiles.length > 0 && (
            <div className="file-preview-container">
              {uploadedFiles.map((file) => (
                <div key={file.id} className="file-preview">
                  <span className="file-icon">📄</span>
                  <div className="file-info">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{formatFileSize(file.size)}</span>
                  </div>
                  <button 
                    className="remove-file-btn"
                    onClick={() => removeFile(file.id)}
                    title="파일 제거"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* 입력 컨트롤 */}
          <div className="input-controls">
            <button 
              className="file-upload-btn"
              onClick={() => fileInputRef.current?.click()}
              title="파일 업로드"
            >
              📎
            </button>
            
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.jpg,.jpeg,.png"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            
            <textarea
              className="message-input"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="메시지를 입력하세요... (Enter 키를 눌러 전송)"
              rows="1"
            />
            
            <button 
              className="send-btn"
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() && uploadedFiles.length === 0}
            >
              <span className="send-icon">➤</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;