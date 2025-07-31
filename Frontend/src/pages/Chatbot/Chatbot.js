import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { tomorrow } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useUser } from '../../context/UserContext';
import NaturalLanguageProfileSetup from '../../components/NaturalLanguageProfileSetup/NaturalLanguageProfileSetup';
import "./Chatbot.css";

const Chatbot = () => {
  const { user, isLoggedIn, isLoading } = useUser();
  const [showProfileSetup, setShowProfileSetup] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "bot",
      content:
        "안녕하세요! 저는 AI 금융 어시스턴트입니다. 문서 분석, 투자에 관한 질문 답변, 시장 인사이트 제공 등을 도와드릴 수 있습니다. 오늘 어떻게 도와드릴까요?",
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // 로그인 상태 확인
  useEffect(() => {
    if (!isLoading && !isLoggedIn) {
      setShowProfileSetup(true);
    }
  }, [isLoggedIn, isLoading]);

  const handleProfileSetupComplete = (userProfile) => {
    setShowProfileSetup(false);
    // 프로필 설정 완료 후 환영 메시지 업데이트
    setMessages(prev => [
      {
        id: 1,
        type: "bot",
        content: `안녕하세요 ${userProfile.name}님! 저는 AI 금융 어시스턴트입니다. 귀하의 투자 프로필을 바탕으로 개인화된 투자 조언과 시장 분석을 제공해드릴 수 있습니다. 오늘 어떻게 도와드릴까요?`,
        timestamp: new Date(),
      }
    ]);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const sendMessageToAPI = async (message, files = []) => {
    return new Promise((resolve, reject) => {
      let fullContent = "";
      let isComplete = false;
      let botMsgId = Date.now() + 1;
      
      // 사용자 정보를 쿼리 파라미터에 포함
      const params = new URLSearchParams({ 
        query: message,
        user_id: user?.user_id || 'anonymous',
        user_name: user?.name || '',
        user_context: JSON.stringify({
          investment_experience: user?.investment_experience || '',
          risk_tolerance: user?.risk_tolerance || '',
          preferred_sectors: user?.preferred_sectors || [],
          portfolio_count: user?.portfolio?.length || 0
        })
      });
      
      const eventSource = new window.EventSource(
        `http://localhost:8001/api/chat/stream?${params.toString()}`
      );

      // 미리 bot 메시지 placeholder 추가
      setMessages((prev) => [
        ...prev,
        {
          id: botMsgId,
          type: "bot",
          content: "",
          timestamp: new Date(),
        },
      ]);
      setIsTyping(true);

      eventSource.onmessage = (event) => {
        console.log("SSE 받은 데이터:", event.data);

        try {
          const data = JSON.parse(event.data);
          console.log("파싱된 데이터:", data);

          // 백엔드 응답 형태에 맞게 처리
          if (data.status === "processing") {
            console.log("처리 중:", data.message);
            // 처리 중 상태는 이미 isTyping으로 표시되므로 별도 처리 불필요
          } else if (data.status === "completed" && data.response) {
            fullContent = data.response;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botMsgId ? { ...m, content: fullContent } : m
              )
            );
            isComplete = true;
            eventSource.close();
            setIsTyping(false);
            resolve({ content: fullContent, success: true });
          } else if (data.status === "error") {
            isComplete = true;
            eventSource.close();
            setIsTyping(false);
            reject(new Error(data.error || "알 수 없는 오류가 발생했습니다."));
          } else if (data.type === "text_chunk") {
            // 기존 형태도 지원 (하위 호환성)
            fullContent += data.content;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botMsgId ? { ...m, content: fullContent } : m
              )
            );
          }
        } catch (e) {
          console.error("JSON 파싱 에러:", e, "원본 데이터:", event.data);

          if (event.data && event.data.trim()) {
            fullContent += event.data;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botMsgId ? { ...m, content: fullContent } : m
              )
            );
          }
        }
      };

      eventSource.onerror = (err) => {
        if (!isComplete) {
          eventSource.close();
          setIsTyping(false);
          reject(err);
        }
      };
    });
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() && uploadedFiles.length === 0) return;

    const userMessage = {
      id: Date.now(),
      type: "user",
      content: inputMessage,
      files: uploadedFiles,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setUploadedFiles([]);

    try {
      // sendMessageToAPI에서 이미 bot 메시지를 처리하므로 여기서는 추가 처리 불필요
      await sendMessageToAPI(inputMessage, uploadedFiles);
    } catch (error) {
      console.error("API 호출 에러:", error);
      const errorMessage = {
        id: Date.now() + 1,
        type: "bot",
        content: "죄송합니다, 오류가 발생했습니다. 나중에 다시 시도해 주세요.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    const fileData = files.map((file) => ({
      id: Date.now() + Math.random(),
      name: file.name,
      size: file.size,
      type: file.type,
      file: file,
    }));

    setUploadedFiles((prev) => [...prev, ...fileData]);
    e.target.value = "";
  };

  const removeFile = (fileId) => {
    setUploadedFiles((prev) => prev.filter((file) => file.id !== fileId));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 바이트";
    const k = 1024;
    const sizes = ["바이트", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // 마크다운 렌더링을 위한 커스텀 컴포넌트
  const MarkdownRenderer = ({ content }) => {
    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            return !inline && match ? (
              <SyntaxHighlighter
                style={tomorrow}
                language={match[1]}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            ) : (
              <code className={`inline-code ${className}`} {...props}>
                {children}
              </code>
            );
          },
          table({ children }) {
            return <table className="markdown-table">{children}</table>;
          },
          th({ children }) {
            return <th className="markdown-th">{children}</th>;
          },
          td({ children }) {
            return <td className="markdown-td">{children}</td>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="markdown-blockquote">
                {children}
              </blockquote>
            );
          },
          h1({ children }) {
            return <h1 className="markdown-h1">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="markdown-h2">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="markdown-h3">{children}</h3>;
          },
          ul({ children }) {
            return <ul className="markdown-ul">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="markdown-ol">{children}</ol>;
          },
          li({ children }) {
            return <li className="markdown-li">{children}</li>;
          },
          p({ children }) {
            return <p className="markdown-p">{children}</p>;
          },
          strong({ children }) {
            return <strong className="markdown-strong">{children}</strong>;
          },
          em({ children }) {
            return <em className="markdown-em">{children}</em>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  return (
    <div className="chatbot">
      {/* 사용자 프로필 설정 모달 */}
      {showProfileSetup && (
        <NaturalLanguageProfileSetup onComplete={handleProfileSetupComplete} />
      )}

      {/* 로딩 상태 */}
      {isLoading && (
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>사용자 정보를 불러오는 중...</p>
        </div>
      )}

      {/* 로그인된 사용자만 접근 가능 */}
      {!isLoading && isLoggedIn && (
        <div className="chatbot-container">
        <div className="chatbot-header">
          <h1 className="chatbot-title">AI 챗봇 어시스턴트</h1>
          <p className="chatbot-subtitle">
            문서를 업로드하고 지능형 금융 인사이트를 받아보세요
          </p>
        </div>

        <div className="messages-container">
          <div className="messages-list">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message ${
                  message.type === "user" ? "user-message" : "bot-message"
                }`}
              >
                <div className="message-content">
                  <div className="message-text">
                    {message.type === "bot" ? (
                      <MarkdownRenderer content={message.content} />
                    ) : (
                      message.content
                    )}
                  </div>

                  {message.files && message.files.length > 0 && (
                    <div className="message-files">
                      {message.files.map((file) => (
                        <div key={file.id} className="uploaded-file-display">
                          <span className="file-icon">📄</span>
                          <span className="file-name">{file.name}</span>
                          <span className="file-size">
                            ({formatFileSize(file.size)})
                          </span>
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

        <div className="input-container">
          {uploadedFiles.length > 0 && (
            <div className="file-preview-container">
              {uploadedFiles.map((file) => (
                <div key={file.id} className="file-preview">
                  <span className="file-icon">📄</span>
                  <div className="file-info">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">
                      {formatFileSize(file.size)}
                    </span>
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
              style={{ display: "none" }}
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
      )}
    </div>
  );
};

export default Chatbot;
