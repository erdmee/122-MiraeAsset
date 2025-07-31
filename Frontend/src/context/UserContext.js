import React, { createContext, useContext, useState, useEffect } from 'react';

const UserContext = createContext();

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};

export const UserProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // 컴포넌트 마운트 시 localStorage에서 사용자 정보 복원
  useEffect(() => {
    const savedUser = localStorage.getItem('userProfile');
    if (savedUser) {
      try {
        const userProfile = JSON.parse(savedUser);
        setUser(userProfile);
      } catch (error) {
        console.error('Failed to parse saved user profile:', error);
        localStorage.removeItem('userProfile');
      }
    }
    setIsLoading(false);
  }, []);

  // 사용자 정보 저장
  const saveUser = (userProfile) => {
    console.log('UserContext saveUser 호출됨:', userProfile);
    setUser(userProfile);
    localStorage.setItem('userProfile', JSON.stringify(userProfile));
    console.log('UserContext 사용자 정보 저장 완료');
  };

  // 사용자 정보 삭제 (로그아웃)
  const clearUser = () => {
    setUser(null);
    localStorage.removeItem('userProfile');
  };

  // 포트폴리오 업데이트
  const updatePortfolio = (portfolio) => {
    const updatedUser = { ...user, portfolio };
    saveUser(updatedUser);
  };

  const value = {
    user,
    isLoading,
    saveUser,
    clearUser,
    updatePortfolio,
    isLoggedIn: !!user
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
};
