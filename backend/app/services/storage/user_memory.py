# app/services/user_memory.py

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import sqlite3
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class UserMemorySystem:
    """사용자 메모리 및 컨텍스트 관리 시스템"""
    
    def __init__(self, db_path: str = "data/user_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            # 사용자 프로필 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    age INTEGER,
                    investment_experience TEXT,  -- beginner, intermediate, expert
                    risk_tolerance TEXT,         -- conservative, moderate, aggressive
                    investment_goals TEXT,       -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 보유 주식 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    stock_code TEXT,
                    stock_name TEXT,
                    quantity INTEGER,
                    avg_price REAL,
                    purchase_date DATE,
                    sector TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            """)
            
            # 관심 종목 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    stock_code TEXT,
                    stock_name TEXT,
                    sector TEXT,
                    reason TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            """)
            
            # 대화 기록 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    session_id TEXT,
                    message_type TEXT,    -- user, assistant
                    content TEXT,
                    entities TEXT,        -- JSON array of extracted entities
                    intent TEXT,          -- 의도 분류
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            """)
            
            # 사용자 선호도 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    preference_key TEXT,
                    preference_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            """)
            
            conn.commit()
            logger.info("사용자 메모리 데이터베이스 초기화 완료")
    
    # === 사용자 프로필 관리 ===
    
    async def create_user_profile(self, user_data: Dict) -> bool:
        """사용자 프로필 생성"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_profiles 
                    (user_id, name, age, investment_experience, risk_tolerance, investment_goals, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_data["user_id"],
                    user_data.get("name"),
                    user_data.get("age"),
                    user_data.get("investment_experience"),
                    user_data.get("risk_tolerance"),
                    json.dumps(user_data.get("investment_goals", [])),
                    datetime.now()
                ))
                conn.commit()
                logger.info(f"사용자 프로필 생성: {user_data['user_id']}")
                return True
        except Exception as e:
            logger.error(f"사용자 프로필 생성 실패: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """사용자 프로필 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT user_id, name, age, investment_experience, 
                           risk_tolerance, investment_goals, created_at, updated_at
                    FROM user_profiles WHERE user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "user_id": row[0],
                        "name": row[1],
                        "age": row[2],
                        "investment_experience": row[3],
                        "risk_tolerance": row[4],
                        "investment_goals": json.loads(row[5] or "[]"),
                        "created_at": row[6],
                        "updated_at": row[7]
                    }
                return None
        except Exception as e:
            logger.error(f"사용자 프로필 조회 실패: {e}")
            return None
    
    # === 보유 주식 관리 ===
    
    async def add_holding(self, user_id: str, holding_data: Dict) -> bool:
        """보유 주식 추가"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_holdings 
                    (user_id, stock_code, stock_name, quantity, avg_price, purchase_date, sector)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    holding_data["stock_code"],
                    holding_data["stock_name"],
                    holding_data["quantity"],
                    holding_data["avg_price"],
                    holding_data["purchase_date"],
                    holding_data.get("sector")
                ))
                conn.commit()
                logger.info(f"보유 주식 추가: {user_id} - {holding_data['stock_name']}")
                return True
        except Exception as e:
            logger.error(f"보유 주식 추가 실패: {e}")
            return False
    
    async def get_user_holdings(self, user_id: str) -> List[Dict]:
        """사용자 보유 주식 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT stock_code, stock_name, quantity, avg_price, 
                           purchase_date, sector, created_at
                    FROM user_holdings WHERE user_id = ?
                    ORDER BY created_at DESC
                """, (user_id,))
                
                holdings = []
                for row in cursor.fetchall():
                    holdings.append({
                        "stock_code": row[0],
                        "stock_name": row[1],
                        "quantity": row[2],
                        "avg_price": row[3],
                        "purchase_date": row[4],
                        "sector": row[5],
                        "created_at": row[6]
                    })
                return holdings
        except Exception as e:
            logger.error(f"보유 주식 조회 실패: {e}")
            return []
    
    # === 관심 종목 관리 ===
    
    async def add_interest(self, user_id: str, interest_data: Dict) -> bool:
        """관심 종목 추가"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_interests 
                    (user_id, stock_code, stock_name, sector, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    interest_data["stock_code"],
                    interest_data["stock_name"],
                    interest_data.get("sector"),
                    interest_data.get("reason")
                ))
                conn.commit()
                logger.info(f"관심 종목 추가: {user_id} - {interest_data['stock_name']}")
                return True
        except Exception as e:
            logger.error(f"관심 종목 추가 실패: {e}")
            return False
    
    async def get_user_interests(self, user_id: str) -> List[Dict]:
        """사용자 관심 종목 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT stock_code, stock_name, sector, reason, added_at
                    FROM user_interests WHERE user_id = ?
                    ORDER BY added_at DESC
                """, (user_id,))
                
                interests = []
                for row in cursor.fetchall():
                    interests.append({
                        "stock_code": row[0],
                        "stock_name": row[1],
                        "sector": row[2],
                        "reason": row[3],
                        "added_at": row[4]
                    })
                return interests
        except Exception as e:
            logger.error(f"관심 종목 조회 실패: {e}")
            return []
    
    # === 대화 기록 관리 ===
    
    async def save_message(
        self, 
        user_id: str, 
        session_id: str, 
        message_type: str, 
        content: str,
        entities: List[str] = None,
        intent: str = None
    ) -> bool:
        """대화 메시지 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversation_history 
                    (user_id, session_id, message_type, content, entities, intent)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    session_id,
                    message_type,
                    content,
                    json.dumps(entities or []),
                    intent
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"메시지 저장 실패: {e}")
            return False
    
    async def get_conversation_history(
        self, 
        user_id: str, 
        session_id: str = None, 
        limit: int = 50
    ) -> List[Dict]:
        """대화 기록 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if session_id:
                    cursor = conn.execute("""
                        SELECT session_id, message_type, content, entities, intent, timestamp
                        FROM conversation_history 
                        WHERE user_id = ? AND session_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (user_id, session_id, limit))
                else:
                    cursor = conn.execute("""
                        SELECT session_id, message_type, content, entities, intent, timestamp
                        FROM conversation_history 
                        WHERE user_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (user_id, limit))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        "session_id": row[0],
                        "message_type": row[1],
                        "content": row[2],
                        "entities": json.loads(row[3] or "[]"),
                        "intent": row[4],
                        "timestamp": row[5]
                    })
                return history
        except Exception as e:
            logger.error(f"대화 기록 조회 실패: {e}")
            return []
    
    # === 컨텍스트 생성 ===
    
    async def get_user_context(self, user_id: str, session_id: str = None) -> Dict:
        """종합 사용자 컨텍스트 생성"""
        try:
            profile = await self.get_user_profile(user_id)
            holdings = await self.get_user_holdings(user_id)
            interests = await self.get_user_interests(user_id)
            
            # 최근 대화 기록 (지난 24시간)
            recent_conversations = await self.get_conversation_history(
                user_id, session_id, limit=20
            )
            
            # 대화에서 자주 언급된 엔티티들
            entity_counts = {}
            for conv in recent_conversations:
                for entity in conv.get("entities", []):
                    entity_counts[entity] = entity_counts.get(entity, 0) + 1
            
            frequent_entities = sorted(
                entity_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            context = {
                "user_profile": profile or {},
                "holdings": holdings,
                "interests": interests,
                "recent_conversations": recent_conversations[:5],  # 최근 5개
                "frequent_entities": frequent_entities,
                "context_summary": self._generate_context_summary(
                    profile, holdings, interests, frequent_entities
                )
            }
            
            return context
            
        except Exception as e:
            logger.error(f"사용자 컨텍스트 생성 실패: {e}")
            return {}
    
    def _generate_context_summary(
        self, 
        profile: Dict, 
        holdings: List[Dict], 
        interests: List[Dict],
        frequent_entities: List[tuple]
    ) -> str:
        """컨텍스트 요약 생성"""
        summary_parts = []
        
        if profile:
            summary_parts.append(
                f"투자 경험: {profile.get('investment_experience', '미정')}, "
                f"위험 성향: {profile.get('risk_tolerance', '미정')}"
            )
        
        if holdings:
            holding_names = [h["stock_name"] for h in holdings[:3]]
            summary_parts.append(f"보유 주식: {', '.join(holding_names)}")
        
        if interests:
            interest_names = [i["stock_name"] for i in interests[:3]]
            summary_parts.append(f"관심 종목: {', '.join(interest_names)}")
        
        if frequent_entities:
            entity_names = [e[0] for e in frequent_entities[:3]]
            summary_parts.append(f"최근 관심사: {', '.join(entity_names)}")
        
        return " | ".join(summary_parts) if summary_parts else "신규 사용자"
    
    # === 선호도 관리 ===
    
    async def update_preference(self, user_id: str, key: str, value: str) -> bool:
        """사용자 선호도 업데이트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_preferences 
                    (user_id, preference_key, preference_value, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, key, value, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"선호도 업데이트 실패: {e}")
            return False
    
    async def get_preferences(self, user_id: str) -> Dict[str, str]:
        """사용자 선호도 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT preference_key, preference_value
                    FROM user_preferences WHERE user_id = ?
                """, (user_id,))
                
                preferences = {}
                for row in cursor.fetchall():
                    preferences[row[0]] = row[1]
                return preferences
        except Exception as e:
            logger.error(f"선호도 조회 실패: {e}")
            return {}
